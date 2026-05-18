#!/usr/bin/env python3
"""Static checks for scout_navigation_manager configuration and mapping logic."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml


ROOT_DIR = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT_DIR / "skills" / "scout_navigation_manager"
SCRIPT_DIR = SKILL_DIR / "scripts"
CONFIG_PATH = SKILL_DIR / "config" / "navigation_position.yaml"
NAVIGATE_PATH = SCRIPT_DIR / "navigate.py"
SERVER_PATH = SCRIPT_DIR / "navigation_manager_server.py"


def print_section(title: str) -> None:
    print()
    print("=" * 16, title, "=" * 16)


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(1)


def load_yaml_config() -> dict:
    if not CONFIG_PATH.exists():
        fail(f"YAML 配置不存在: {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_module(module_path: Path, module_name: str):
    if not module_path.exists():
        fail(f"脚本不存在: {module_path}")
    spec = importlib.util.spec_from_file_location(module_name, str(module_path))
    if spec is None or spec.loader is None:
        fail(f"无法加载模块: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_files_exist() -> None:
    print_section("路径检查")
    for path in [ROOT_DIR, CONFIG_PATH, NAVIGATE_PATH, SERVER_PATH]:
        if not path.exists():
            fail(f"缺少文件或目录: {path}")
        print(f"[OK] {path}")


def check_yaml_structure(config: dict) -> None:
    print_section("YAML 结构")
    map_id = config.get("map_id")
    frame_id = config.get("frame_id")
    positions = config.get("navigation_positions")

    if not map_id:
        fail("缺少 map_id")
    if not frame_id:
        fail("缺少 frame_id")
    if not isinstance(positions, dict) or not positions:
        fail("navigation_positions 为空或不是字典")

    print(f"[OK] map_id = {map_id}")
    print(f"[OK] frame_id = {frame_id}")
    print(f"[OK] 地点数量 = {len(positions)}")

    for name, pose in positions.items():
        if not isinstance(pose, dict):
            fail(f"{name}: 配置不是字典")
        for key in ["x", "y", "orientation"]:
            if key not in pose:
                fail(f"{name}: 缺少 {key}")
        orientation = pose["orientation"]
        if not isinstance(orientation, dict):
            fail(f"{name}: orientation 不是字典")
        for key in ["x", "y", "z", "w"]:
            if key not in orientation:
                fail(f"{name}: orientation 缺少 {key}")
            if not isinstance(orientation[key], (int, float)):
                fail(f"{name}: orientation.{key} 不是数字")
        aliases = pose.get("aliases", [])
        if aliases is not None and not isinstance(aliases, list):
            fail(f"{name}: aliases 不是列表")
        if isinstance(aliases, list):
            for alias in aliases:
                if not isinstance(alias, str):
                    fail(f"{name}: alias {alias!r} 不是字符串")
        print(
            f"[OK] {name}: x={pose['x']}, y={pose['y']}, "
            f"orientation={orientation}, aliases={len(aliases or [])}"
        )


def check_mapping_logic(navigate_module) -> None:
    print_section("映射逻辑")
    test_cases = {
        "原点": "原点",
        "回到原点": "原点",
        "回家": "原点",
        "带我去巡逻点2": "巡逻点2",
        "去巡逻点三": "巡逻点3",
        "到巡逻点4": "巡逻点4",
        "去工位2": "工位2",
        "带我去工位2": "工位2",
        "去火星基地": None,
    }

    for raw_text, expected in test_cases.items():
        actual = navigate_module.resolve_waypoint_name(str(CONFIG_PATH), raw_text)
        if actual != expected:
            fail(f"{raw_text!r} 解析结果错误: actual={actual!r}, expected={expected!r}")
        print(f"[OK] {raw_text} -> {actual}")


def check_waypoint_listing(navigate_module) -> None:
    print_section("地点列表")
    names = navigate_module.load_waypoint_names(str(CONFIG_PATH))
    if not names:
        fail("load_waypoint_names 返回空列表")
    print("[OK] 可用地点: " + ", ".join(names))


def check_failure_status_preserved() -> None:
    print_section("失败状态")
    source = SERVER_PATH.read_text(encoding="utf-8")
    if "format_navigation_failure_status" not in source:
        fail("缺少导航失败状态格式化函数")
    if 'failed: target=%s state=%s(%s)' not in source:
        fail("导航失败状态未保留 target 和 actionlib state")
    if 'self._set_status("ready")\n        rospy.logwarn("Navigation failed' in source:
        fail("导航失败后不应直接把状态重置为 ready")
    print("[OK] 导航失败状态会保留失败原因")


def check_goal_dispatched_confirmation() -> None:
    print_section("下发确认")
    server_source = SERVER_PATH.read_text(encoding="utf-8")
    client_source = NAVIGATE_PATH.read_text(encoding="utf-8")
    if "/scout_navigation_manager/goal_dispatched" not in server_source:
        fail("服务端缺少 goal_dispatched publisher")
    if "latch=True" not in server_source:
        fail("goal_dispatched publisher 应使用 latch=True，避免客户端错过确认消息")
    if "_publish_goal_dispatched" not in server_source:
        fail("服务端未在目标下发后发布确认消息")
    if "default=10.0" not in client_source:
        fail("navigate.py 下发确认默认等待时间应为 10 秒")
    if "dispatch_confirmed=true" not in client_source:
        fail("navigate.py 缺少 dispatch_confirmed=true 输出")
    if "dispatch_confirmed=false" not in client_source:
        fail("navigate.py 缺少 dispatch_confirmed=false 输出")
    print("[OK] goal_dispatched 下发确认链路通过")


def check_cancel_navigation_support() -> None:
    print_section("取消导航")
    server_source = SERVER_PATH.read_text(encoding="utf-8")
    client_source = NAVIGATE_PATH.read_text(encoding="utf-8")
    if "/scout_navigation_manager/cancel_navigation" not in server_source:
        fail("服务端缺少 cancel_navigation 服务")
    if "cancel_goal()" not in server_source:
        fail("服务端取消导航时应调用 move_base cancel_goal()")
    if "navigation cancellation is still in progress" not in server_source:
        fail("取消回调完成前应拒绝新的导航目标，避免状态竞争")
    if "--cancel" not in client_source:
        fail("navigate.py 缺少 --cancel 参数")
    if "cancel_navigation()" not in client_source:
        fail("navigate.py 缺少 cancel_navigation 调用")
    print("[OK] 取消导航链路通过")


def main() -> None:
    print("项目根目录:", ROOT_DIR)
    check_files_exist()
    config = load_yaml_config()
    check_yaml_structure(config)
    navigate_module = load_module(NAVIGATE_PATH, "navigate_module")
    check_waypoint_listing(navigate_module)
    check_mapping_logic(navigate_module)
    check_failure_status_preserved()
    check_goal_dispatched_confirmation()
    check_cancel_navigation_support()
    print_section("结果")
    print("[OK] scout_navigation_manager 静态测试通过")


if __name__ == "__main__":
    main()
