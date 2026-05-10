#!/usr/bin/env python3
"""Fixed-point patrol skill built on scout_navigation_manager."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import yaml


ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from skills import skill_protocol


SKILL_NAME = "patrol_fixed_points"
SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = SKILL_DIR / "config" / "patrol_points.yaml"
DEFAULT_STATE_PATH = SKILL_DIR / "patrol_state.json"
NAVIGATE_PATH = ROOT_DIR / "skills" / "scout_navigation_manager" / "scripts" / "navigate.py"
CHECK_PERSON_PATH = ROOT_DIR / "skills" / "check_person_detected" / "scripts" / "check_person_detected.py"
WAYPOINT_PATH = ROOT_DIR / "skills" / "scout_navigation_manager" / "config" / "navigation_position.yaml"


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_default_config(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    raw = load_yaml(path)
    return dict(raw.get("default_patrol") or {})


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


def parse_patrol_points(raw_points: Any, default_points: list[str]) -> list[str]:
    if raw_points is None or raw_points == "":
        return list(default_points)
    if isinstance(raw_points, list):
        points = [str(item).strip() for item in raw_points]
    else:
        points = [item.strip() for item in str(raw_points).replace("，", ",").split(",")]
    points = [point for point in points if point]
    if not points:
        raise ValueError("patrol_points is empty")
    return points


def load_waypoint_names(path: Path = WAYPOINT_PATH) -> list[str]:
    raw = load_yaml(path)
    positions = raw.get("navigation_positions") or raw.get("destinations") or {}
    return sorted(positions.keys())


def validate_points(points: list[str]) -> None:
    available = set(load_waypoint_names())
    missing = [point for point in points if point not in available]
    if missing:
        raise ValueError("unknown patrol waypoint(s): %s; available: %s" % (",".join(missing), ",".join(sorted(available))))


def write_state(payload: dict[str, Any]) -> None:
    payload = dict(payload)
    existing_path = resolve_existing_state_path()
    if existing_path is not None and "stop_requested" not in payload:
        try:
            existing = json.loads(existing_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
        if existing.get("stop_requested") is True:
            payload["stop_requested"] = True
    payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    state_path = resolve_state_path()
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        fallback_path = fallback_state_path()
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        fallback_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_state() -> dict[str, Any]:
    state_path = resolve_existing_state_path()
    if state_path is None:
        return {
            "patrol_status": "idle",
            "current_waypoint": "",
            "completed_waypoints": [],
            "failed_waypoint": "",
            "last_navigation_status": "",
            "stop_requested": False,
        }
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "patrol_status": "error",
            "current_waypoint": "",
            "completed_waypoints": [],
            "failed_waypoint": "",
            "last_navigation_status": "state file is invalid",
            "stop_requested": False,
        }


def fallback_state_path() -> Path:
    return Path(tempfile.gettempdir()) / "openclaw_lab_adapter" / "patrol_fixed_points_state.json"


def resolve_state_path() -> Path:
    env_path = os.environ.get("PATROL_FIXED_POINTS_STATE_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_STATE_PATH


def resolve_existing_state_path() -> Path | None:
    primary = resolve_state_path()
    if primary.exists():
        return primary
    fallback = fallback_state_path()
    if fallback.exists():
        return fallback
    return None


def run_navigate_command(args: list[str]) -> dict[str, Any]:
    command = [sys.executable, str(NAVIGATE_PATH.relative_to(ROOT_DIR)), *args]
    completed = subprocess.run(
        command,
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def query_navigation_status() -> dict[str, Any]:
    return run_navigate_command(["--status"])


def dispatch_waypoint(point: str) -> dict[str, Any]:
    return run_navigate_command(["--go", point])


def cancel_navigation() -> dict[str, Any]:
    return run_navigate_command(["--cancel"])


def run_detection_command(args: list[str]) -> dict[str, Any]:
    command = [sys.executable, str(CHECK_PERSON_PATH.relative_to(ROOT_DIR)), *args]
    completed = subprocess.run(
        command,
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def parse_skill_result(stdout: str) -> dict[str, Any] | None:
    text = (stdout or "").strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict) and {"skill", "status", "data"}.issubset(payload.keys()):
        return payload
    return None


def check_detection_once(
    source: str,
    topic: str,
    timeout_seconds: float,
    confidence_threshold: float,
) -> dict[str, Any]:
    args = [
        "--check",
        "--source",
        source,
        "--timeout-seconds",
        str(timeout_seconds),
        "--confidence-threshold",
        str(confidence_threshold),
    ]
    if topic:
        args.extend(["--topic", topic])
    trace = run_detection_command(args)
    payload = parse_skill_result(trace.get("stdout", ""))
    return {
        "trace": trace,
        "result": payload,
        "person_detected": bool((payload or {}).get("data", {}).get("person_detected")),
    }


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


def status_result() -> dict[str, Any]:
    state = read_state()
    status = skill_protocol.SkillStatus.RUNNING
    if state.get("patrol_status") in {"idle", "finished", "stopped"}:
        status = skill_protocol.SkillStatus.SUCCESS
    if state.get("patrol_status") == "error":
        status = skill_protocol.SkillStatus.FAILED
    return result(status, "当前巡逻状态：%s。" % state.get("patrol_status", "unknown"), state)


def reset_state_result() -> dict[str, Any]:
    state = {
        "patrol_status": "idle",
        "current_waypoint": "",
        "completed_waypoints": [],
        "failed_waypoint": "",
        "last_navigation_status": "",
        "stop_requested": False,
    }
    write_state(state)
    return result(skill_protocol.SkillStatus.SUCCESS, "巡逻状态已重置为空闲。", state)


def is_stop_requested() -> bool:
    return bool(read_state().get("stop_requested"))


def stopped_result(
    point: str,
    completed_points: list[str],
    message: str,
    trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = {
        "patrol_status": "stopped",
        "current_waypoint": point,
        "completed_waypoints": completed_points,
        "failed_waypoint": "",
        "last_navigation_status": "cancelled",
        "stop_requested": True,
    }
    write_state(data)
    return result(skill_protocol.SkillStatus.SUCCESS, message, data, trace=trace)


def detected_person_result(
    point: str,
    completed_points: list[str],
    detection_payload: dict[str, Any],
    cancel_trace: dict[str, Any],
) -> dict[str, Any]:
    detection_data = dict((detection_payload.get("data") or {}))
    data = {
        "patrol_status": "detected_person",
        "current_waypoint": point,
        "completed_waypoints": completed_points,
        "failed_waypoint": "",
        "last_navigation_status": cancel_trace.get("stdout") or cancel_trace.get("stderr") or "cancel requested",
        "stop_requested": True,
        "person_detected": True,
        "target_pose": detection_data.get("target_pose"),
        "source_topic": detection_data.get("source_topic", ""),
        "detection": detection_data,
    }
    write_state(data)
    return result(
        skill_protocol.SkillStatus.SUCCESS,
        "巡逻中检测到人员，已停止当前巡逻导航并交由现有协同链路处理。",
        data,
        trace={
            "detection": detection_payload,
            "cancel_navigation": cancel_trace,
        },
    )


def stop_state_result() -> dict[str, Any]:
    state = read_state()
    completed_points = list(state.get("completed_waypoints") or [])
    current_waypoint = str(state.get("current_waypoint") or "")
    data = {
        **state,
        "patrol_status": "stopped",
        "current_waypoint": current_waypoint,
        "completed_waypoints": completed_points,
        "failed_waypoint": "",
        "last_navigation_status": "cancel requested",
        "stop_requested": True,
    }
    write_state(data)
    cancel_trace = cancel_navigation()
    data["last_navigation_status"] = cancel_trace.get("stdout") or cancel_trace.get("stderr") or "cancel requested"
    write_state(data)
    return result(
        skill_protocol.SkillStatus.SUCCESS,
        "巡逻停止请求已发送，并已请求取消当前导航。",
        data,
        trace=cancel_trace,
    )


def wait_until_waypoint_done(
    point: str,
    completed_points: list[str],
    timeout_seconds: float,
    poll_seconds: float,
    stop_on_detection: bool = False,
    detection_source: str = "track_pose",
    detection_topic: str = "/track_pose",
    detection_timeout_seconds: float = 0.2,
    detection_confidence_threshold: float = 0.5,
) -> dict[str, Any] | None:
    deadline = time.time() + timeout_seconds
    last_trace: dict[str, Any] = {}
    while time.time() < deadline:
        if is_stop_requested():
            cancel_trace = cancel_navigation()
            return stopped_result(point, completed_points, "巡逻已按停止请求结束。", trace=cancel_trace)
        time.sleep(min(poll_seconds, max(deadline - time.time(), 0.0)))
        if stop_on_detection:
            detection_check = check_detection_once(
                detection_source,
                detection_topic,
                detection_timeout_seconds,
                detection_confidence_threshold,
            )
            detection_payload = detection_check.get("result") or {}
            detection_status = detection_payload.get("status")
            if detection_check.get("person_detected"):
                cancel_trace = cancel_navigation()
                return detected_person_result(point, completed_points, detection_payload, cancel_trace)
            if detection_status == skill_protocol.SkillStatus.UNAVAILABLE:
                detail = (detection_payload.get("error") or {}).get("message") or detection_payload.get("message", "")
                return result(
                    skill_protocol.SkillStatus.UNAVAILABLE,
                    "巡逻中无法读取人员检测结果：%s" % detail,
                    {
                        "patrol_status": "error",
                        "current_waypoint": point,
                        "completed_waypoints": completed_points,
                        "failed_waypoint": point,
                        "last_navigation_status": "detection unavailable",
                        "person_detected": False,
                    },
                    error_code="PATROL_DETECTION_UNAVAILABLE",
                    error_message=detail,
                    trace=detection_check.get("trace", {}),
                )
        trace = query_navigation_status()
        last_trace = trace
        raw_status = trace.get("stdout", "").strip()
        state_status, _ = skill_protocol.status_from_navigation_status(raw_status)
        write_state(
            {
                "patrol_status": "moving" if raw_status.lower().startswith("moving to ") else "arrived",
                "current_waypoint": point,
                "completed_waypoints": completed_points,
                "failed_waypoint": "",
                "last_navigation_status": raw_status,
            }
        )

        if trace.get("returncode") != 0:
            detail = trace.get("stderr") or trace.get("stdout") or "navigation status query failed"
            return result(
                skill_protocol.SkillStatus.UNAVAILABLE,
                "巡逻中无法查询导航状态：%s" % detail,
                {
                    "patrol_status": "error",
                    "current_waypoint": point,
                    "completed_waypoints": completed_points,
                    "failed_waypoint": point,
                    "last_navigation_status": detail,
                },
                error_code="NAVIGATION_STATUS_UNAVAILABLE",
                error_message=detail,
                trace=trace,
            )
        if raw_status.lower() == "finish":
            return None
        if raw_status.lower() == "ready":
            return result(
                skill_protocol.SkillStatus.FAILED,
                "巡逻点 %s 未到达，导航状态提前回到 ready。" % point,
                {
                    "patrol_status": "error",
                    "current_waypoint": point,
                    "completed_waypoints": completed_points,
                    "failed_waypoint": point,
                    "last_navigation_status": raw_status,
                },
                error_code="PATROL_WAYPOINT_NOT_FINISHED",
                error_message="navigation returned ready before finish",
                trace=trace,
            )
        if state_status in {skill_protocol.SkillStatus.FAILED, skill_protocol.SkillStatus.UNAVAILABLE}:
            return result(
                state_status,
                "巡逻点 %s 导航失败：%s" % (point, raw_status),
                {
                    "patrol_status": "error",
                    "current_waypoint": point,
                    "completed_waypoints": completed_points,
                    "failed_waypoint": point,
                    "last_navigation_status": raw_status,
                },
                error_code="PATROL_NAVIGATION_FAILED",
                error_message=raw_status,
                trace=trace,
            )

    return result(
        skill_protocol.SkillStatus.TIMEOUT,
        "等待巡逻点 %s 到达超过 %.0f 秒。" % (point, timeout_seconds),
        {
            "patrol_status": "error",
            "current_waypoint": point,
            "completed_waypoints": completed_points,
            "failed_waypoint": point,
            "last_navigation_status": last_trace.get("stdout", ""),
        },
        error_code="PATROL_WAYPOINT_TIMEOUT",
        error_message="waypoint timeout",
        trace=last_trace,
    )


def run_patrol(args: argparse.Namespace) -> dict[str, Any]:
    cfg = load_default_config()
    try:
        points = parse_patrol_points(args.patrol_points, list(cfg.get("patrol_points") or []))
        loop = parse_bool(args.loop, bool(cfg.get("loop", False)))
        stop_on_detection = parse_bool(args.stop_on_detection, bool(cfg.get("stop_on_detection", False)))
        timeout_seconds = float(args.waypoint_timeout_seconds or cfg.get("waypoint_timeout_seconds", 120))
        poll_seconds = float(args.status_poll_seconds or cfg.get("status_poll_seconds", 1))
        detection_source = str(cfg.get("detection_source", "track_pose"))
        detection_topic = str(cfg.get("detection_topic", "/track_pose"))
        detection_timeout_seconds = float(cfg.get("detection_timeout_seconds", 0.2))
        detection_confidence_threshold = float(cfg.get("detection_confidence_threshold", 0.5))
        validate_points(points)
    except (ValueError, TypeError) as exc:
        data = {
            "patrol_status": "error",
            "current_waypoint": "",
            "completed_waypoints": [],
            "failed_waypoint": "",
            "last_navigation_status": "",
            "patrol_points": args.patrol_points,
        }
        write_state(data)
        return result(
            skill_protocol.SkillStatus.INVALID_INPUT,
            str(exc),
            data,
            error_code="PATROL_INVALID_INPUT",
            error_message=str(exc),
        )

    if loop:
        return result(
            skill_protocol.SkillStatus.INVALID_INPUT,
            "当前 Demo 阶段暂不执行无限循环巡逻，请将 loop 设为 false。",
            {
                "patrol_status": "error",
                "current_waypoint": "",
                "completed_waypoints": [],
                "failed_waypoint": "",
                "last_navigation_status": "",
                "patrol_points": points,
                "loop": loop,
                "stop_on_detection": stop_on_detection,
            },
            error_code="PATROL_LOOP_UNSUPPORTED",
            error_message="loop patrol is not enabled in current demo stage",
        )

    completed_points: list[str] = []
    write_state(
        {
            "patrol_status": "moving",
                "current_waypoint": points[0],
                "completed_waypoints": completed_points,
                "failed_waypoint": "",
                "last_navigation_status": "",
                "patrol_points": points,
                "loop": loop,
                "stop_on_detection": stop_on_detection,
                "stop_requested": False,
            }
    )

    for point in points:
        if is_stop_requested():
            return stopped_result(point, completed_points, "巡逻已在下发下一个点前停止。")
        write_state(
            {
                "patrol_status": "moving",
                "current_waypoint": point,
                "completed_waypoints": completed_points,
                "failed_waypoint": "",
                "last_navigation_status": "dispatching",
                "patrol_points": points,
                "loop": loop,
                "stop_on_detection": stop_on_detection,
            }
        )
        dispatch_trace = dispatch_waypoint(point)
        if dispatch_trace.get("returncode") != 0:
            detail = dispatch_trace.get("stderr") or dispatch_trace.get("stdout") or "navigation dispatch failed"
            data = {
                "patrol_status": "error",
                "current_waypoint": point,
                "completed_waypoints": completed_points,
                "failed_waypoint": point,
                "last_navigation_status": detail,
                "patrol_points": points,
            }
            write_state(data)
            return result(
                skill_protocol.SkillStatus.UNAVAILABLE,
                "巡逻点 %s 下发失败：%s" % (point, detail),
                data,
                error_code="PATROL_DISPATCH_FAILED",
                error_message=detail,
                trace=dispatch_trace,
            )
        if "success=false" in dispatch_trace.get("stdout", "").lower():
            data = {
                "patrol_status": "error",
                "current_waypoint": point,
                "completed_waypoints": completed_points,
                "failed_waypoint": point,
                "last_navigation_status": dispatch_trace.get("stdout", ""),
                "patrol_points": points,
            }
            write_state(data)
            return result(
                skill_protocol.SkillStatus.FAILED,
                "巡逻点 %s 被导航服务拒绝：%s" % (point, dispatch_trace.get("stdout", "")),
                data,
                error_code="PATROL_GOAL_REJECTED",
                error_message=dispatch_trace.get("stdout", ""),
                trace=dispatch_trace,
            )

        failure = wait_until_waypoint_done(
            point,
            completed_points,
            timeout_seconds,
            poll_seconds,
            stop_on_detection=stop_on_detection,
            detection_source=detection_source,
            detection_topic=detection_topic,
            detection_timeout_seconds=detection_timeout_seconds,
            detection_confidence_threshold=detection_confidence_threshold,
        )
        if failure is not None:
            write_state(failure.get("data", {}))
            return failure

        completed_points.append(point)
        write_state(
            {
                "patrol_status": "arrived",
                "current_waypoint": point,
                "completed_waypoints": completed_points,
                "failed_waypoint": "",
                "last_navigation_status": "finish",
                "patrol_points": points,
                "loop": loop,
                "stop_on_detection": stop_on_detection,
            }
        )

    final_data = {
        "patrol_status": "finished",
        "current_waypoint": points[-1],
        "completed_waypoints": completed_points,
        "failed_waypoint": "",
        "last_navigation_status": "finish",
        "patrol_points": points,
        "loop": loop,
        "stop_on_detection": stop_on_detection,
        "stop_requested": False,
    }
    write_state(final_data)
    return result(skill_protocol.SkillStatus.SUCCESS, "固定点巡逻已完成。", final_data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Patrol fixed points skill")
    parser.add_argument("--run", action="store_true", help="Run one fixed-point patrol pass")
    parser.add_argument("--status", action="store_true", help="Read latest patrol state")
    parser.add_argument("--reset", action="store_true", help="Reset patrol state to idle")
    parser.add_argument("--stop", action="store_true", help="Stop patrol and cancel active navigation")
    parser.add_argument("--patrol-points", default="", help="Comma-separated waypoint names")
    parser.add_argument("--loop", default="", help="Whether to loop patrol, default false")
    parser.add_argument("--stop-on-detection", default="", help="Reserved for detection integration")
    parser.add_argument("--waypoint-timeout-seconds", type=float, default=None)
    parser.add_argument("--status-poll-seconds", type=float, default=None)
    args = parser.parse_args()

    if args.status:
        print(json.dumps(status_result(), ensure_ascii=False))
        return
    if args.reset:
        print(json.dumps(reset_state_result(), ensure_ascii=False))
        return
    if args.stop:
        print(json.dumps(stop_state_result(), ensure_ascii=False))
        return
    if args.run:
        print(json.dumps(run_patrol(args), ensure_ascii=False))
        return
    parser.print_help(sys.stderr)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
