#!/usr/bin/env python3
"""Confirm that an existing tracking handoff has entered the vehicle pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from skills import skill_protocol


SKILL_NAME = "trigger_existing_tracking_handoff"
SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = SKILL_DIR / "config" / "handoff_config.yaml"


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_default_config(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    raw = load_yaml(path)
    return dict(raw.get("default_handoff") or {})


def parse_bool(value: Any, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on", "是", "确认"}:
        return True
    if text in {"0", "false", "no", "n", "off", "否", "不"}:
        return False
    raise ValueError("invalid bool value: %s" % value)


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


def import_ros_dependencies():
    try:
        import rosgraph  # type: ignore
        import rospy  # type: ignore
        from geometry_msgs.msg import Pose  # type: ignore
    except ImportError as exc:
        raise RuntimeError("ROS Python dependencies for tracking handoff are not available") from exc
    return rosgraph, rospy, Pose


def normalize_topic(topic: str) -> str:
    value = (topic or "/track_pose").strip()
    if not value:
        raise ValueError("topic is empty")
    return value if value.startswith("/") else "/" + value


def get_topic_connections(rosgraph: Any, topic: str) -> dict[str, list[str]]:
    master = rosgraph.Master("/trigger_existing_tracking_handoff")
    publishers, subscribers, _services = master.getSystemState()
    normalized = normalize_topic(topic)
    return {
        "publishers": list(dict(publishers).get(normalized, [])),
        "subscribers": list(dict(subscribers).get(normalized, [])),
    }


def base_data(topic: str, cfg: dict[str, Any], connections: dict[str, list[str]] | None = None) -> dict[str, Any]:
    connections = connections or {"publishers": [], "subscribers": []}
    return {
        "handoff_triggered": False,
        "target_pose": None,
        "source_topic": topic,
        "bridge_subscriber_seen": bool(connections.get("subscribers")),
        "ros_publishers": list(connections.get("publishers") or []),
        "ros_subscribers": list(connections.get("subscribers") or []),
        "handoff_mode": str(cfg.get("handoff_mode", "existing_vehicle_pipeline")),
        "dds_topic": str(cfg.get("dds_topic", "PoseMsgTopic")),
    }


def check_handoff(args: argparse.Namespace) -> dict[str, Any]:
    cfg = load_default_config()
    try:
        topic = normalize_topic(args.topic or str(cfg.get("topic", "/track_pose")))
        timeout_seconds = parse_float(args.timeout_seconds, float(cfg.get("timeout_seconds", 3)), "timeout_seconds")
        require_subscriber = parse_bool(args.require_subscriber, bool(cfg.get("require_subscriber", False)))
    except ValueError as exc:
        return result(
            skill_protocol.SkillStatus.INVALID_INPUT,
            str(exc),
            {"handoff_triggered": False},
            error_code="HANDOFF_INVALID_INPUT",
            error_message=str(exc),
        )

    try:
        rosgraph_module, rospy, pose_type = import_ros_dependencies()
    except RuntimeError as exc:
        return result(
            skill_protocol.SkillStatus.UNAVAILABLE,
            "协同交接 ROS 依赖不可用：%s" % exc,
            {"handoff_triggered": False, "source_topic": topic},
            error_code="HANDOFF_ROS_UNAVAILABLE",
            error_message=str(exc),
        )

    if not rospy.core.is_initialized():
        rospy.init_node("trigger_existing_tracking_handoff", anonymous=True, disable_signals=True)

    try:
        connections = get_topic_connections(rosgraph_module, topic)
    except Exception as exc:
        return result(
            skill_protocol.SkillStatus.UNAVAILABLE,
            "无法读取 ROS master topic 状态：%s" % exc,
            {"handoff_triggered": False, "source_topic": topic},
            error_code="HANDOFF_MASTER_UNAVAILABLE",
            error_message=str(exc),
        )

    data = base_data(topic, cfg, connections)

    if args.status:
        data["handoff_triggered"] = bool(data["bridge_subscriber_seen"] or data["ros_publishers"])
        return result(skill_protocol.SkillStatus.SUCCESS, "已读取现有协同交接 topic 状态。", data)

    if require_subscriber and not data["bridge_subscriber_seen"]:
        return result(
            skill_protocol.SkillStatus.FAILED,
            "未观察到 /track_pose subscriber，无法确认现有协同链路已接入。",
            data,
            error_code="HANDOFF_SUBSCRIBER_NOT_FOUND",
            error_message="no subscriber for %s" % topic,
        )

    try:
        msg = rospy.wait_for_message(topic, pose_type, timeout=timeout_seconds)
    except Exception as exc:
        return result(
            skill_protocol.SkillStatus.TIMEOUT,
            "等待协同目标 pose 超时。",
            data,
            error_code="HANDOFF_WAIT_TIMEOUT",
            error_message=str(exc) or "timeout",
            trace={"topic": topic, "timeout_seconds": timeout_seconds},
        )

    data["target_pose"] = pose_to_dict(msg)
    data["handoff_triggered"] = True
    return result(
        skill_protocol.SkillStatus.SUCCESS,
        "已确认人员目标进入现有大车到小车协同交接链路。",
        data,
        trace={"topic": topic, "timeout_seconds": timeout_seconds, "require_subscriber": require_subscriber},
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Confirm existing tracking handoff through /track_pose")
    parser.add_argument("--check", action="store_true", help="Wait for one existing tracking target pose")
    parser.add_argument("--status", action="store_true", help="Read current ROS topic connection state")
    parser.add_argument("--topic", default="", help="Override track pose topic, default /track_pose")
    parser.add_argument("--timeout-seconds", default="", help="Wait timeout for one pose message")
    parser.add_argument("--require-subscriber", default="", help="Require at least one ROS subscriber")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.check and not args.status:
        args.check = True
    payload = check_handoff(args)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") in {skill_protocol.SkillStatus.SUCCESS, skill_protocol.SkillStatus.TIMEOUT} else 1


if __name__ == "__main__":
    raise SystemExit(main())
