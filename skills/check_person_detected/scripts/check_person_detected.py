#!/usr/bin/env python3
"""Read existing person-detection ROS topics and return SkillResult JSON."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import yaml


ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from skills import skill_protocol


SKILL_NAME = "check_person_detected"
SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = SKILL_DIR / "config" / "detection_config.yaml"
VALID_SOURCES = {"track_pose", "detect_msg", "auto"}


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_default_config(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    raw = load_yaml(path)
    return dict(raw.get("default_detection") or {})


def parse_source(source: str | None, default: str = "track_pose") -> str:
    value = (source or default or "track_pose").strip().lower()
    if value not in VALID_SOURCES:
        raise ValueError("unsupported detection source: %s" % value)
    return value


def parse_float(value: Any, default: float, name: str) -> float:
    if value is None or value == "":
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("%s must be a number" % name) from exc
    if parsed < 0:
        raise ValueError("%s must be non-negative" % name)
    return parsed


def result(
    status: str,
    message: str,
    data: dict[str, Any],
    error_code: str | None = None,
    error_message: str | None = None,
    trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return skill_protocol.make_result(
        skill=SKILL_NAME,
        status=status,
        execution_mode=skill_protocol.ExecutionMode.SYNC,
        message=message,
        data=data,
        error_code=error_code,
        error_message=error_message,
        trace=trace or {},
    )


def pose_to_dict(msg: Any) -> dict[str, Any]:
    return {
        "position": {
            "x": float(msg.position.x),
            "y": float(msg.position.y),
            "z": float(msg.position.z),
        },
        "orientation": {
            "x": float(msg.orientation.x),
            "y": float(msg.orientation.y),
            "z": float(msg.orientation.z),
            "w": float(msg.orientation.w),
        },
    }


def target_to_dict(target: Any) -> dict[str, Any]:
    return {
        "class_name": str(getattr(target, "frame_id", "")),
        "confidence": float(getattr(target, "scores", 0.0)),
        "bbox": {
            "x": float(getattr(target, "ptx", 0.0)),
            "y": float(getattr(target, "pty", 0.0)),
            "width": float(getattr(target, "distw", 0.0)),
            "height": float(getattr(target, "disth", 0.0)),
            "center_x": float(getattr(target, "centerx", 0.0)),
            "center_y": float(getattr(target, "centery", 0.0)),
        },
        "image": {
            "height": int(getattr(target, "imgh", 0)),
            "width": int(getattr(target, "imgw", 0)),
        },
    }


def is_person_target(target: Any) -> bool:
    class_name = str(getattr(target, "frame_id", "")).strip().lower()
    return class_name in {"person", "people", "pedestrian", "0x1", "1"}


def message_age_seconds(msg: Any, now_seconds: float | None = None) -> float | None:
    stamp = getattr(msg, "timestamp", None) or getattr(msg, "stamp", None)
    if stamp is None:
        return None
    if hasattr(stamp, "to_sec"):
        stamp_seconds = float(stamp.to_sec())
    elif hasattr(stamp, "secs"):
        stamp_seconds = float(stamp.secs) + float(getattr(stamp, "nsecs", 0)) / 1_000_000_000
    else:
        return None
    now = time.time() if now_seconds is None else now_seconds
    return max(0.0, now - stamp_seconds)


def build_detect_msg_payload(msg: Any, topic: str, confidence_threshold: float) -> dict[str, Any]:
    targets = list(getattr(msg, "data", []) or [])
    detections = [
        target_to_dict(target)
        for target in targets
        if is_person_target(target) and float(getattr(target, "scores", 0.0)) >= confidence_threshold
    ]
    return {
        "person_detected": bool(detections),
        "source": "detect_msg",
        "source_topic": topic,
        "target_pose": None,
        "detections": detections,
        "confidence_threshold": confidence_threshold,
        "message_age_seconds": message_age_seconds(msg),
        "raw_detection_count": len(targets),
    }


def import_ros_dependencies(source: str):
    try:
        import rospy  # type: ignore
    except ImportError as exc:
        raise RuntimeError("ROS Python dependency rospy is not available") from exc

    if source == "track_pose":
        try:
            from geometry_msgs.msg import Pose  # type: ignore
        except ImportError as exc:
            raise RuntimeError("geometry_msgs.msg.Pose is not available") from exc
        return rospy, Pose

    try:
        from msgs.msg import TargetArray  # type: ignore
    except ImportError as exc:
        raise RuntimeError("msgs.msg.TargetArray is not available") from exc
    return rospy, TargetArray


def wait_for_track_pose(topic: str, timeout_seconds: float) -> dict[str, Any]:
    rospy, pose_type = import_ros_dependencies("track_pose")
    if not rospy.core.is_initialized():
        rospy.init_node("check_person_detected", anonymous=True, disable_signals=True)
    msg = rospy.wait_for_message(topic, pose_type, timeout=timeout_seconds)
    return {
        "person_detected": True,
        "source": "track_pose",
        "source_topic": topic,
        "target_pose": pose_to_dict(msg),
        "detections": [],
        "confidence_threshold": None,
        "message_age_seconds": message_age_seconds(msg),
        "raw_detection_count": 1,
    }


def wait_for_detect_msg(topic: str, timeout_seconds: float, confidence_threshold: float) -> dict[str, Any]:
    rospy, target_array_type = import_ros_dependencies("detect_msg")
    if not rospy.core.is_initialized():
        rospy.init_node("check_person_detected", anonymous=True, disable_signals=True)
    msg = rospy.wait_for_message(topic, target_array_type, timeout=timeout_seconds)
    return build_detect_msg_payload(msg, topic, confidence_threshold)


def check_source(
    source: str,
    topic: str,
    timeout_seconds: float,
    confidence_threshold: float,
) -> dict[str, Any]:
    if source == "track_pose":
        return wait_for_track_pose(topic, timeout_seconds)
    if source == "detect_msg":
        return wait_for_detect_msg(topic, timeout_seconds, confidence_threshold)
    raise ValueError("unsupported detection source: %s" % source)


def check_person_detected(args: argparse.Namespace) -> dict[str, Any]:
    cfg = load_default_config()
    try:
        source = parse_source(args.source, str(cfg.get("source", "track_pose")))
        timeout_seconds = parse_float(args.timeout_seconds, float(cfg.get("timeout_seconds", 3)), "timeout_seconds")
        max_age_seconds = parse_float(args.max_age_seconds, float(cfg.get("max_age_seconds", 2)), "max_age_seconds")
        confidence_threshold = parse_float(
            args.confidence_threshold,
            float(cfg.get("confidence_threshold", 0.5)),
            "confidence_threshold",
        )
    except ValueError as exc:
        return result(
            skill_protocol.SkillStatus.INVALID_INPUT,
            str(exc),
            {"person_detected": False},
            error_code="INVALID_DETECTION_ARGUMENT",
            error_message=str(exc),
        )

    track_topic = args.topic or str(cfg.get("track_pose_topic", "/track_pose"))
    detect_topic = args.topic or str(cfg.get("detect_msg_topic", "/DetectMsg"))
    sources = ["track_pose", "detect_msg"] if source == "auto" else [source]
    errors = []

    for item in sources:
        topic = track_topic if item == "track_pose" else detect_topic
        try:
            data = check_source(item, topic, timeout_seconds, confidence_threshold)
        except TimeoutError as exc:
            errors.append({"source": item, "topic": topic, "error": str(exc) or "timeout"})
            continue
        except Exception as exc:
            text = str(exc)
            if "rospy" in text or "not available" in text or "No module named" in text:
                return result(
                    skill_protocol.SkillStatus.UNAVAILABLE,
                    "人员检测 ROS 依赖不可用：%s" % text,
                    {"person_detected": False, "source": item, "source_topic": topic},
                    error_code="DETECTION_ROS_UNAVAILABLE",
                    error_message=text,
                    trace={"source": item, "topic": topic, "timeout_seconds": timeout_seconds},
                )
            errors.append({"source": item, "topic": topic, "error": text})
            continue

        data["max_age_seconds"] = max_age_seconds
        message = "已检测到人员。" if data.get("person_detected") else "检测 topic 正常，但当前未检测到人员。"
        return result(
            skill_protocol.SkillStatus.SUCCESS,
            message,
            data,
            trace={"source": item, "topic": topic, "timeout_seconds": timeout_seconds},
        )

    message = "等待人员检测结果超时。"
    return result(
        skill_protocol.SkillStatus.TIMEOUT,
        message,
        {
            "person_detected": False,
            "source": source,
            "source_topic": track_topic if source == "track_pose" else detect_topic,
            "errors": errors,
            "max_age_seconds": max_age_seconds,
            "confidence_threshold": confidence_threshold,
        },
        error_code="DETECTION_WAIT_TIMEOUT",
        error_message=message,
        trace={"source": source, "timeout_seconds": timeout_seconds, "errors": errors},
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check person detection result from existing ROS topics")
    parser.add_argument("--check", action="store_true", help="Wait for one detection message and return SkillResult")
    parser.add_argument("--status", action="store_true", help="Alias of --check with current defaults")
    parser.add_argument("--source", default="", help="track_pose, detect_msg or auto")
    parser.add_argument("--topic", default="", help="Override source topic")
    parser.add_argument("--timeout-seconds", default="", help="Wait timeout for one ROS message")
    parser.add_argument("--max-age-seconds", default="", help="Maximum expected message age")
    parser.add_argument("--confidence-threshold", default="", help="Confidence threshold for /DetectMsg")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.check and not args.status:
        args.check = True
    payload = check_person_detected(args)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") in {skill_protocol.SkillStatus.SUCCESS, skill_protocol.SkillStatus.TIMEOUT} else 1


if __name__ == "__main__":
    raise SystemExit(main())
