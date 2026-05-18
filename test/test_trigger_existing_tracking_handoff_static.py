#!/usr/bin/env python3
"""Static checks for trigger_existing_tracking_handoff skill."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT_DIR / "skills" / "trigger_existing_tracking_handoff" / "scripts" / "trigger_handoff.py"
CONFIG_PATH = ROOT_DIR / "skills" / "trigger_existing_tracking_handoff" / "config" / "handoff_config.yaml"
SKILL_DOC_PATH = ROOT_DIR / "skills" / "trigger_existing_tracking_handoff" / "SKILL.md"


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
    for path in [SCRIPT_PATH, CONFIG_PATH, SKILL_DOC_PATH]:
        if not path.exists():
            fail(f"缺少文件: {path}")
        print(f"[OK] {path}")


def check_config(module) -> None:
    cfg = module.load_default_config()
    if cfg.get("topic") != "/track_pose":
        fail("默认 handoff topic 应为 /track_pose")
    if cfg.get("dds_topic") != "PoseMsgTopic":
        fail("默认 DDS topic 应为 PoseMsgTopic")
    if cfg.get("handoff_mode") != "existing_vehicle_pipeline":
        fail("handoff_mode 应说明复用现有链路")
    print("[OK] 默认配置通过")


def check_parsing(module) -> None:
    if module.normalize_topic("track_pose") != "/track_pose":
        fail("topic 归一化失败")
    if module.parse_bool("true") is not True or module.parse_bool("false") is not False:
        fail("bool 参数解析失败")
    try:
        module.parse_float("-1", 3.0, "timeout_seconds")
    except ValueError:
        print("[OK] 非法 timeout 被拒绝")
    else:
        fail("非法 timeout 未被拒绝")
    print("[OK] 参数解析通过")


def check_invalid_input_result(module) -> None:
    args = argparse.Namespace(
        check=True,
        status=False,
        topic="",
        timeout_seconds="-1",
        require_subscriber="",
    )
    payload = module.check_handoff(args)
    if payload.get("status") != module.skill_protocol.SkillStatus.INVALID_INPUT:
        fail("非法 timeout 应返回 invalid_input")
    for key in ["skill", "status", "execution_mode", "message", "data", "error", "trace"]:
        if key not in payload:
            fail(f"SkillResult 缺少字段: {key}")
    print("[OK] 非法输入协议通过")


def check_source_contract() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    for text in ["rospy.wait_for_message", "geometry_msgs.msg", "rosgraph.Master", "/track_pose", "PoseMsgTopic"]:
        if text not in source:
            fail(f"实现中缺少关键链路: {text}")
    forbidden = ["rospy.Publisher", ".publish(", "/cmd_vel"]
    for text in forbidden:
        if text in source:
            fail(f"handoff skill 不应主动发布或控制: {text}")
    print("[OK] ROS topic 读取链路与安全边界通过")


def main() -> None:
    check_files()
    module = load_module(SCRIPT_PATH, "trigger_existing_tracking_handoff_module")
    check_config(module)
    check_parsing(module)
    check_invalid_input_result(module)
    check_source_contract()
    print("[OK] trigger_existing_tracking_handoff 静态测试通过")


if __name__ == "__main__":
    main()
