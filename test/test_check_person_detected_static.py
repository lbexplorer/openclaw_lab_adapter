#!/usr/bin/env python3
"""Static checks for check_person_detected skill."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT_DIR / "skills" / "check_person_detected" / "scripts" / "check_person_detected.py"
CONFIG_PATH = ROOT_DIR / "skills" / "check_person_detected" / "config" / "detection_config.yaml"
SKILL_DOC_PATH = ROOT_DIR / "skills" / "check_person_detected" / "SKILL.md"


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


class FakeStamp:
    def __init__(self, value: float):
        self.value = value

    def to_sec(self) -> float:
        return self.value


class FakeTarget:
    frame_id = "person"
    scores = 0.9
    ptx = 10
    pty = 20
    distw = 30
    disth = 40
    centerx = 25
    centery = 40
    imgh = 480
    imgw = 640


class FakeTargetArray:
    timestamp = FakeStamp(100.0)
    data = [FakeTarget()]


def check_files() -> None:
    for path in [SCRIPT_PATH, CONFIG_PATH, SKILL_DOC_PATH]:
        if not path.exists():
            fail(f"缺少文件: {path}")
        print(f"[OK] {path}")


def check_config(module) -> None:
    cfg = module.load_default_config()
    if cfg.get("source") != "track_pose":
        fail("默认检测源应为 track_pose")
    if cfg.get("track_pose_topic") != "/track_pose":
        fail("默认 track pose topic 应为 /track_pose")
    if cfg.get("detect_msg_topic") != "/DetectMsg":
        fail("默认 DetectMsg topic 应为 /DetectMsg")
    print("[OK] 默认配置通过")


def check_parsing(module) -> None:
    for source in ["track_pose", "detect_msg", "auto"]:
        if module.parse_source(source) != source:
            fail(f"source 解析失败: {source}")
    try:
        module.parse_source("camera")
    except ValueError:
        print("[OK] 非法 source 被拒绝")
    else:
        fail("非法 source 未被拒绝")
    if module.parse_float("", 3.0, "timeout") != 3.0:
        fail("空 float 参数未使用默认值")
    print("[OK] 参数解析通过")


def check_detect_payload(module) -> None:
    payload = module.build_detect_msg_payload(FakeTargetArray(), "/DetectMsg", 0.5)
    if payload.get("person_detected") is not True:
        fail("person target 未识别")
    if payload.get("detections", [{}])[0].get("confidence") != 0.9:
        fail("confidence 解析失败")
    if payload.get("message_age_seconds") is None:
        fail("message age 未解析")
    print("[OK] DetectMsg 解析通过")


def check_invalid_input_result(module) -> None:
    args = argparse.Namespace(
        check=True,
        status=False,
        source="bad_source",
        topic="",
        timeout_seconds="",
        max_age_seconds="",
        confidence_threshold="",
    )
    payload = module.check_person_detected(args)
    if payload.get("status") != module.skill_protocol.SkillStatus.INVALID_INPUT:
        fail("非法 source 应返回 invalid_input")
    for key in ["skill", "status", "execution_mode", "message", "data", "error", "trace"]:
        if key not in payload:
            fail(f"SkillResult 缺少字段: {key}")
    print("[OK] 非法输入协议通过")


def check_source_contract() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    for text in ["rospy.wait_for_message", "geometry_msgs.msg", "msgs.msg", "/track_pose", "/DetectMsg"]:
        if text not in source:
            fail(f"实现中缺少关键链路: {text}")
    print("[OK] ROS topic 读取链路存在")


def main() -> None:
    check_files()
    module = load_module(SCRIPT_PATH, "check_person_detected_module")
    check_config(module)
    check_parsing(module)
    check_detect_payload(module)
    check_invalid_input_result(module)
    check_source_contract()
    print("[OK] check_person_detected 静态测试通过")


if __name__ == "__main__":
    main()
