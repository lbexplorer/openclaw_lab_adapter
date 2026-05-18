#!/usr/bin/env python3
"""Static checks for patrol_fixed_points skill."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT_DIR / "skills" / "patrol_fixed_points" / "scripts" / "patrol.py"
CONFIG_PATH = ROOT_DIR / "skills" / "patrol_fixed_points" / "config" / "patrol_points.yaml"


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(1)


def load_module(module_path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, str(module_path))
    if spec is None or spec.loader is None:
        fail(f"无法加载模块: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def check_files() -> None:
    for path in [SCRIPT_PATH, CONFIG_PATH]:
        if not path.exists():
            fail(f"缺少文件: {path}")
        print(f"[OK] {path}")


def check_default_config(module) -> None:
    cfg = module.load_default_config()
    expected = ["原点", "巡逻点2", "巡逻点3", "巡逻点4", "原点"]
    if cfg.get("patrol_points") != expected:
        fail(f"默认巡逻点错误: {cfg.get('patrol_points')}")
    if int(cfg.get("waypoint_timeout_seconds", 0)) != 120:
        fail("单点默认等待超时应为 120 秒")
    if cfg.get("detection_source") != "track_pose" or cfg.get("detection_topic") != "/track_pose":
        fail("stop_on_detection 默认应读取 /track_pose")
    print("[OK] 默认巡逻配置通过")


def check_parsing_and_validation(module) -> None:
    points = module.parse_patrol_points("", ["原点", "巡逻点2"])
    if points != ["原点", "巡逻点2"]:
        fail("空 patrol_points 未使用默认路线")
    points = module.parse_patrol_points("原点，巡逻点2, 巡逻点3", [])
    if points != ["原点", "巡逻点2", "巡逻点3"]:
        fail("巡逻点字符串解析失败")
    if module.parse_bool("false", True) is not False or module.parse_bool("true", False) is not True:
        fail("bool 参数解析失败")
    module.validate_points(["原点", "巡逻点2", "巡逻点3", "巡逻点4"])
    try:
        module.validate_points(["火星基地"])
    except ValueError:
        print("[OK] 非法巡逻点被拒绝")
    else:
        fail("非法巡逻点未被拒绝")
    print("[OK] 参数解析与校验通过")


def check_status_result(module) -> None:
    module.reset_state_result()
    payload = module.status_result()
    for key in ["skill", "status", "execution_mode", "message", "data", "error", "trace"]:
        if key not in payload:
            fail(f"SkillResult 缺少字段: {key}")
    if payload["skill"] != "patrol_fixed_points":
        fail("status_result skill 名称错误")
    print("[OK] 状态查询协议通过")


def check_stop_support(module) -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    if "--stop" not in source:
        fail("巡逻 skill 缺少 --stop 参数")
    if "cancel_navigation" not in source:
        fail("巡逻 stop 应调用导航 cancel")
    if "stop_requested" not in source:
        fail("巡逻 stop 应记录 stop_requested")
    stopped = module.stopped_result("巡逻点2", ["原点"], "测试停止")
    if stopped.get("status") != module.skill_protocol.SkillStatus.SUCCESS:
        fail("巡逻停止应返回 success")
    if stopped.get("data", {}).get("patrol_status") != "stopped":
        fail("巡逻停止状态应为 stopped")
    if stopped.get("data", {}).get("stop_requested") is not True:
        fail("巡逻停止应记录 stop_requested=true")
    module.reset_state_result()
    print("[OK] 巡逻停止支持通过")


def check_detection_stop_support(module) -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    for text in ["CHECK_PERSON_PATH", "check_detection_once", "detected_person_result", "cancel_navigation()"]:
        if text not in source:
            fail(f"stop_on_detection 缺少检测停止链路: {text}")
    detection_payload = {
        "data": {
            "target_pose": {"position": {"x": 1.0, "y": 2.0, "z": 0.0}},
            "source_topic": "/track_pose",
        }
    }
    cancel_trace = {"stdout": "cancelled=true message=ok", "stderr": ""}
    payload = module.detected_person_result("巡逻点2", ["原点"], detection_payload, cancel_trace)
    data = payload.get("data", {})
    if payload.get("status") != module.skill_protocol.SkillStatus.SUCCESS:
        fail("检测到人员后应返回 success")
    if data.get("patrol_status") != "detected_person":
        fail("检测到人员后 patrol_status 应为 detected_person")
    if data.get("person_detected") is not True:
        fail("检测到人员结果缺少 person_detected=true")
    if data.get("target_pose") is None or data.get("source_topic") != "/track_pose":
        fail("检测到人员结果未保留 target_pose/source_topic")
    module.reset_state_result()
    print("[OK] 检测触发停止支持通过")


def check_invalid_run(module) -> None:
    args = argparse.Namespace(
        patrol_points="火星基地",
        loop="false",
        stop_on_detection="false",
        waypoint_timeout_seconds=120,
        status_poll_seconds=1,
    )
    payload = module.run_patrol(args)
    if payload.get("status") != module.skill_protocol.SkillStatus.INVALID_INPUT:
        fail("非法巡逻路线应返回 invalid_input")
    if payload.get("data", {}).get("patrol_status") != "error":
        fail("非法巡逻路线应记录 error 状态")
    print("[OK] 非法运行输入协议通过")
    module.reset_state_result()


def main() -> None:
    check_files()
    module = load_module(SCRIPT_PATH, "patrol_fixed_points_module")
    check_default_config(module)
    check_parsing_and_validation(module)
    check_status_result(module)
    check_stop_support(module)
    check_detection_stop_support(module)
    check_invalid_run(module)
    print("[OK] patrol_fixed_points 静态测试通过")


if __name__ == "__main__":
    main()
