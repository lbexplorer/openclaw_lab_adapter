#!/usr/bin/env python3
"""Shared skill protocol for openclaw_lab_adapter agents.

The protocol is intentionally small: existing ROS-facing scripts can keep their
current CLI/service shape, while agents consume a stable SkillResult dictionary.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


class SkillStatus:
    SUCCESS = "success"
    FAILED = "failed"
    RUNNING = "running"
    ACCEPTED = "accepted"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    INVALID_INPUT = "invalid_input"


class ExecutionMode:
    SYNC = "sync"
    ASYNC = "async"


TERMINAL_STATUSES = {
    SkillStatus.SUCCESS,
    SkillStatus.FAILED,
    SkillStatus.TIMEOUT,
    SkillStatus.UNAVAILABLE,
    SkillStatus.INVALID_INPUT,
}


@dataclass
class SkillError:
    code: str
    message: str


@dataclass
class SkillResult:
    skill: str
    status: str
    execution_mode: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    error: SkillError | None = None
    trace: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.error is None:
            payload["error"] = None
        return payload


def make_result(
    skill: str,
    status: str,
    execution_mode: str,
    message: str,
    data: dict[str, Any] | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    error = None
    if error_code or error_message:
        error = SkillError(code=error_code or "SKILL_ERROR", message=error_message or message)
    return SkillResult(
        skill=skill,
        status=status,
        execution_mode=execution_mode,
        message=message,
        data=data or {},
        error=error,
        trace=trace or {},
    ).to_dict()


def is_success(result: dict[str, Any]) -> bool:
    return result.get("status") == SkillStatus.SUCCESS


def is_non_terminal_progress(result: dict[str, Any]) -> bool:
    return result.get("status") in {SkillStatus.ACCEPTED, SkillStatus.RUNNING}


def status_from_navigation_status(raw_status: str) -> tuple[str, str]:
    status = (raw_status or "").strip()
    lowered = status.lower()
    if not status:
        return SkillStatus.UNAVAILABLE, "导航状态为空，无法确认导航服务状态。"
    if lowered == "finish":
        return SkillStatus.SUCCESS, "导航任务已完成。"
    if lowered.startswith("cancelled"):
        return SkillStatus.SUCCESS, "导航任务已取消。"
    if lowered.startswith("moving to "):
        return SkillStatus.RUNNING, "导航任务正在执行。"
    if lowered == "ready":
        return SkillStatus.SUCCESS, "导航服务空闲，可接收任务。"
    if lowered.startswith("failed") or lowered.startswith("error"):
        return SkillStatus.FAILED, "导航任务失败。"
    return SkillStatus.RUNNING, "导航状态已返回，但仍需继续确认。"


def status_from_move_status(raw_status: str) -> tuple[str, str]:
    status = (raw_status or "").strip()
    lowered = status.lower()
    if not status:
        return SkillStatus.UNAVAILABLE, "底盘状态为空，无法确认运动服务状态。"
    if lowered == "stop":
        return SkillStatus.SUCCESS, "底盘当前空闲。"
    if lowered == "moving":
        return SkillStatus.RUNNING, "底盘动作正在执行。"
    if lowered.startswith("failed") or lowered.startswith("error"):
        return SkillStatus.FAILED, "底盘动作执行失败。"
    return SkillStatus.RUNNING, "底盘状态已返回，但仍需继续确认。"


def classify_process_failure(returncode: int, stdout: str, stderr: str) -> tuple[str, str, str]:
    detail = (stderr or stdout or "skill process failed").strip()
    lowered = detail.lower()
    if returncode == 2 or "unknown waypoint" in lowered or "invalid" in lowered:
        return SkillStatus.INVALID_INPUT, "INVALID_INPUT", detail
    service_wait_markers = (
        "ros1 python dependencies not available",
        "wait_for_service",
        "timeout exceeded while waiting for service",
        "service not available",
        "unable to communicate with master",
    )
    if any(marker in lowered for marker in service_wait_markers):
        return SkillStatus.UNAVAILABLE, "SKILL_UNAVAILABLE", detail
    return SkillStatus.FAILED, "SKILL_FAILED", detail
