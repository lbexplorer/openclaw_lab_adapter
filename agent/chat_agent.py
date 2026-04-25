#!/usr/bin/env python3
"""LLM-driven multi-turn chat agent for Scout skill orchestration."""

from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

AGENT_DIR = Path(__file__).resolve().parent
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

import scout_main_agent as core


CHAT_HISTORY_LIMIT = 6
EXIT_WORDS = {"退出", "exit", "quit", "q"}
CONFIRM_WORDS = {"确认", "是", "好的", "好", "yes", "y", "ok", "开始执行", "执行"}
CANCEL_WORDS = {"取消", "不用了", "否", "no", "n", "算了"}
CAPABILITY_PATTERNS = ("你会什么", "你能做什么", "能做什么", "help", "帮助", "skills", "能力")
LAST_ACTION_PATTERNS = ("刚才执行了什么", "刚刚执行了什么", "上一条命令", "上一个任务", "刚才做了什么")
STATUS_PATTERNS = ("当前状态", "现在状态", "你在做什么", "正在做什么", "状态")
LIST_WAYPOINT_PATTERNS = (
    "列出能够到达的地点",
    "列出可到达地点",
    "有哪些可到达地点",
    "可到达地点",
    "有哪些地点",
    "可用地点",
    "有哪些导航点",
    "列出地点",
)


@dataclass
class RobotState:
    mode: str = "idle"
    last_target: str | None = None
    last_action: str | None = None
    last_skill: str | None = None
    last_user_text: str | None = None


@dataclass
class PlannedSkillCall:
    skill_name: str
    arguments: dict[str, Any]
    summary: str
    raw_arguments: dict[str, Any] | None = None


@dataclass
class PendingIntent:
    actions: list[PlannedSkillCall]
    preview_reply: str
    summary: str
    debug_lines: list[str] = field(default_factory=list)


@dataclass
class ChatSession:
    history: list[dict[str, str]] = field(default_factory=list)
    robot_state: RobotState = field(default_factory=RobotState)
    pending_intent: PendingIntent | None = None

    def append(self, role: str, content: str, history_limit: int = CHAT_HISTORY_LIMIT) -> None:
        self.history.append({"role": role, "content": content})
        max_messages = max(history_limit * 2, 2)
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", (text or "")).strip().lower()


def build_startup_banner(skill_catalog: dict[str, dict[str, Any]]) -> str:
    return "\n".join(
        [
            "Scout Chat Agent 已启动，当前进入 LLM skills 调度会话。",
            core.format_capability_overview(skill_catalog),
            "你可以直接输入“带我去前台”“前进1秒”“停止”或“你能做什么”。",
            "输入 退出 / exit 可结束会话。",
        ]
    )


def summarize_robot_state(state: RobotState) -> str:
    if state.mode == "navigating" and state.last_target:
        return f"当前记录状态: navigating, last_target={state.last_target}, last_skill={state.last_skill}"
    if state.mode == "moving" and state.last_action:
        return f"当前记录状态: moving, last_action={state.last_action}, last_skill={state.last_skill}"
    if state.last_skill:
        return f"当前记录状态: {state.mode}, last_skill={state.last_skill}"
    return "当前记录状态: idle"


def build_status_reply(state: RobotState) -> str:
    if state.mode == "navigating" and state.last_target:
        return f"我当前记录的状态是正在前往{state.last_target}。"
    if state.mode == "moving" and state.last_action:
        return f"我当前记录的状态是正在执行动作：{state.last_action}。"
    return "我当前记录的状态是空闲。"


def build_last_action_reply(state: RobotState) -> str:
    if state.last_skill == "scout_navigation_manager" and state.last_target:
        return f"我上一条执行的导航任务是前往{state.last_target}。"
    if state.last_skill == "scout_move_control" and state.last_action:
        return f"我上一条执行的底盘动作是：{state.last_action}。"
    return "我这次会话里还没有执行过动作。"


def detect_capability_query(user_text: str, skill_catalog: dict[str, dict[str, Any]]) -> str | None:
    normalized = normalize_text(user_text)
    if any(pattern in normalized for pattern in LIST_WAYPOINT_PATTERNS):
        names = skill_catalog.get("scout_navigation_manager", {}).get("available_waypoints") or []
        return f"当前可到达的命名地点有：{', '.join(names)}。"
    if "scout_move_control" in normalized or any(token in normalized for token in ("前进", "后退", "左转", "右转", "停止", "底盘")):
        payload = skill_catalog.get("scout_move_control")
        if payload:
            return "\n".join(
                [
                    "scout_move_control 可以执行这些操作：",
                    "；".join(payload.get("capabilities") or []),
                    "参数说明：" + "；".join(f"{k}={v}" for k, v in (payload.get("arguments") or {}).items()),
                    "示例：" + "；".join(payload.get("examples") or []),
                ]
            )

    if "scout_navigation_manager" in normalized or any(token in normalized for token in ("导航", "地点", "去哪")):
        payload = skill_catalog.get("scout_navigation_manager")
        if payload:
            return "\n".join(
                [
                    "scout_navigation_manager 可以执行这些操作：",
                    "；".join(payload.get("capabilities") or []),
                    "参数说明：" + "；".join(f"{k}={v}" for k, v in (payload.get("arguments") or {}).items()),
                    "可用地点：" + "、".join(payload.get("available_waypoints") or []),
                    "示例：" + "；".join(payload.get("examples") or []),
                ]
            )
    if any(pattern in normalized for pattern in CAPABILITY_PATTERNS):
        return core.format_capability_overview(skill_catalog)
    return None


def local_fallback_reply(user_text: str, robot_state: RobotState, skill_catalog: dict[str, dict[str, Any]], error_text: str | None = None) -> str:
    normalized = normalize_text(user_text)
    if any(pattern in normalized for pattern in STATUS_PATTERNS):
        return build_status_reply(robot_state)
    if any(pattern in normalized for pattern in LAST_ACTION_PATTERNS):
        return build_last_action_reply(robot_state)

    capability_reply = detect_capability_query(user_text, skill_catalog)
    if capability_reply is not None:
        return capability_reply

    if error_text:
        return f"我这轮没有稳定完成调度，先给你当前能力清单参考。\n{core.format_capability_overview(skill_catalog)}\n附加信息：{error_text}"
    return "我目前支持命名地点导航、基础底盘动作、技能能力查询和最近状态说明。你也可以直接问我“你能做什么”。"


def build_chat_system_prompt(
    skill_catalog: dict[str, dict[str, Any]],
    robot_state: RobotState,
    pending_intent: PendingIntent | None,
    config: dict[str, Any],
) -> str:
    max_actions = int((config.get("agent") or {}).get("max_actions", 3))
    pending_text = pending_intent.summary if pending_intent is not None else "无待确认动作"
    return textwrap.dedent(
        f"""
        你是 openclaw_lab_adapter 的多轮对话主智能体，负责通过 tool calling 调度本地 skills。
        你可以回答能力查询、参数说明、地点列表、最近状态，也可以在需要时调用工具执行动作。
        不要虚构不存在的 skill，也不要虚构地点。
        如果用户是在问能力或说明，就直接回答，不要调用工具。
        如果用户要求执行导航或底盘动作，再决定是否调用工具。
        本轮最多调用 {max_actions} 个工具；如果一个请求不需要工具，就直接回复文本。
        工具参数必须合法：navigation target 必须是标准地点名；move command 必须是英文动作字符串。

        当前技能目录:
        {core.format_skill_catalog_for_prompt(skill_catalog)}

        当前机器人状态:
        {summarize_robot_state(robot_state)}

        当前待确认动作:
        {pending_text}
        """
    ).strip()


def normalize_assistant_message(raw: dict[str, Any]) -> dict[str, Any]:
    message = {"role": raw.get("role", "assistant")}
    if raw.get("content") is not None:
        message["content"] = raw.get("content")
    if raw.get("tool_calls"):
        message["tool_calls"] = raw.get("tool_calls")
    return message


def parse_tool_calls(raw_message: dict[str, Any], skill_catalog: dict[str, dict[str, Any]]) -> list[PlannedSkillCall]:
    planned_actions = []
    for tool_call in raw_message.get("tool_calls") or []:
        tool_name = tool_call.get("function", {}).get("name", "")
        raw_arguments = tool_call.get("function", {}).get("arguments", "{}")
        try:
            parsed_arguments = json.loads(raw_arguments)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid tool call arguments for {tool_name}: {raw_arguments}") from exc
        arguments = core.validate_tool_call(tool_name, parsed_arguments, skill_catalog)
        planned_actions.append(
            PlannedSkillCall(
                skill_name=tool_name,
                arguments=arguments,
                summary=core.summarize_action(tool_name, arguments),
                raw_arguments=parsed_arguments,
            )
        )
    return planned_actions


def format_debug_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def build_dry_run_debug_lines(
    user_text: str,
    actions: list[PlannedSkillCall],
    skill_catalog: dict[str, dict[str, Any]],
    require_confirmation: bool,
) -> list[str]:
    lines = [
        "[Dry Run 调度日志]",
        "LLM输出:",
        f"- 用户输入: {user_text}",
        f"- action 数量: {len(actions)}",
    ]
    for index, action in enumerate(actions, start=1):
        lines.extend(
            [
                f"- Action {index}: {action.summary}",
                f"  skill: {action.skill_name}",
                f"  raw_arguments: {format_debug_value(action.raw_arguments or {})}",
            ]
        )

    lines.append("参数校验:")
    for index, action in enumerate(actions, start=1):
        lines.extend(
            [
                f"- Action {index}: {action.skill_name}",
                f"  validated_arguments: {format_debug_value(action.arguments)}",
            ]
        )

    lines.append("执行命令:")
    for index, action in enumerate(actions, start=1):
        command, _, _ = core.build_execution_command(action.skill_name, action.arguments)
        lines.extend(
            [
                f"- Action {index}: {action.skill_name}",
                f"  command: {format_debug_value(command)}",
            ]
        )

    lines.append("确认策略:")
    for index, action in enumerate(actions, start=1):
        skill_meta = skill_catalog.get(action.skill_name) or {}
        lines.extend(
            [
                f"- Action {index}: {action.skill_name}",
                f"  risk_level: {skill_meta.get('risk_level', 'unknown')}",
                f"  decision: {'需确认后执行' if require_confirmation else '可直接执行'}",
            ]
        )
    return lines


def append_debug_block(reply: str, debug_lines: list[str], dry_run: bool) -> str:
    if not dry_run or not debug_lines:
        return reply
    block = "\n".join(debug_lines)
    return f"{reply}\n\n{block}" if reply else block


def service_start_hint(skill_name: str) -> str:
    if skill_name == "scout_navigation_manager":
        return "请先启动导航适配服务 navigation_manager_server.py，并确认 move_base 已正常运行。"
    if skill_name == "scout_move_control":
        return "请先启动运动适配服务 move_control_server.py，并确认底盘控制链路已接通。"
    return "请先启动对应的适配服务。"


def is_status_ready(result: dict[str, Any]) -> bool:
    if result.get("status") == "dry_run":
        return True
    if result.get("status") != "ok":
        return False
    if result.get("returncode") not in (None, 0):
        return False
    stdout = (result.get("stdout") or "").strip()
    return bool(stdout)


def update_robot_state_for_action(state: RobotState, action: PlannedSkillCall) -> RobotState:
    updated = RobotState(**vars(state))
    updated.last_skill = action.skill_name
    if action.skill_name == "scout_navigation_manager":
        updated.mode = "navigating"
        updated.last_target = str(action.arguments.get("target", "")).strip() or updated.last_target
    elif action.skill_name == "scout_move_control":
        command = str(action.arguments.get("command", "")).strip()
        segments = core.split_move_command_segments(command)
        if len(segments) == 1 and segments[0]["action"] == "stop":
            updated.mode = "idle"
        else:
            updated.mode = "moving"
        updated.last_action = command
    return updated


def build_pending_intent(actions: list[PlannedSkillCall]) -> PendingIntent:
    summary = "；".join(action.summary for action in actions)
    preview_lines = ["已识别到以下待执行操作："]
    for action in actions:
        preview_lines.append(f"- {action.summary}")
    preview_lines.append("这类操作需要确认。请回复“确认”后执行，或回复“取消”放弃。")
    return PendingIntent(
        actions=actions,
        preview_reply="\n".join(preview_lines),
        summary=summary,
    )


def should_confirm_actions(actions: list[PlannedSkillCall], skill_catalog: dict[str, dict[str, Any]]) -> bool:
    if len(actions) > 1:
        return True
    if not actions:
        return False
    action = actions[0]
    return core.should_confirm_action(action.skill_name, action.arguments, skill_catalog)


def build_execution_fallback_reply(executed_results: list[dict[str, Any]]) -> str:
    if not executed_results:
        return "这轮没有执行任何 skill。"
    result = executed_results[-1]
    if result.get("status") in {"ok", "dry_run"}:
        skill_name = result.get("skill")
        if skill_name == "scout_navigation_manager":
            return f"好的，已处理导航请求，目标是 {result.get('arguments', {}).get('target', '')}。"
        if skill_name == "scout_move_control":
            return f"好的，已处理底盘动作：{result.get('arguments', {}).get('command', '')}。"
    detail = (result.get("stderr") or result.get("stdout") or "执行失败").strip()
    return f"我尝试执行了请求，但没有成功：{detail}"


def execute_actions_with_guard(
    actions: list[PlannedSkillCall],
    previous_state: RobotState,
    history: list[dict[str, str]],
    user_text: str,
    assistant_message: dict[str, Any],
    config: dict[str, Any],
    skill_catalog: dict[str, dict[str, Any]],
    dry_run: bool,
    debug_lines: list[str] | None = None,
) -> dict[str, Any]:
    working_state = RobotState(**vars(previous_state))
    working_state.last_user_text = user_text
    executed_results: list[dict[str, Any]] = []

    messages: list[dict[str, Any]] = [{"role": "system", "content": build_chat_system_prompt(skill_catalog, previous_state, None, config)}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})
    messages.append(normalize_assistant_message(assistant_message))

    for index, action in enumerate(actions):
        if not dry_run:
            status_result = core.query_skill_status(action.skill_name, dry_run=False)
            if not is_status_ready(status_result):
                return {
                    "assistant_reply": append_debug_block(service_start_hint(action.skill_name), debug_lines or [], dry_run),
                    "updated_state": previous_state,
                    "pending_intent": None,
                    "executed_results": executed_results + [status_result],
                }

        result = core.execute_action(action.skill_name, action.arguments, dry_run=dry_run)
        executed_results.append(result)
        if result.get("status") not in {"ok", "dry_run"}:
            detail = (result.get("stderr") or result.get("stdout") or "执行失败").strip()
            return {
                "assistant_reply": append_debug_block(f"我尝试执行第 {index + 1} 个动作时失败了：{detail}", debug_lines or [], dry_run),
                "updated_state": previous_state,
                "pending_intent": None,
                "executed_results": executed_results,
            }

        working_state = update_robot_state_for_action(working_state, action)
        messages.append(
            {
                "role": "tool",
                "tool_call_id": f"exec_{index}",
                "content": json.dumps(result, ensure_ascii=False),
            }
        )

    try:
        follow_up = core.call_chat_completion(
            {
                "messages": messages,
                "tool_choice": "none",
            },
            config,
        )
        raw_message = follow_up["choices"][0]["message"]
        assistant_reply = (raw_message.get("content") or "").strip()
    except Exception:
        assistant_reply = ""

    return {
        "assistant_reply": append_debug_block(assistant_reply or build_execution_fallback_reply(executed_results), debug_lines or [], dry_run),
        "updated_state": working_state,
        "pending_intent": None,
        "executed_results": executed_results,
    }


def handle_pending_turn(
    user_text: str,
    robot_state: RobotState,
    pending_intent: PendingIntent,
    history: list[dict[str, str]],
    config: dict[str, Any],
    skill_catalog: dict[str, dict[str, Any]],
    dry_run: bool,
) -> dict[str, Any]:
    normalized = normalize_text(user_text)
    if normalized in CONFIRM_WORDS:
        assistant_message = {
            "role": "assistant",
            "content": pending_intent.preview_reply,
            "tool_calls": [
                {
                    "id": f"pending_{index}",
                    "type": "function",
                    "function": {
                        "name": action.skill_name,
                        "arguments": json.dumps(action.arguments, ensure_ascii=False),
                    },
                }
                for index, action in enumerate(pending_intent.actions)
            ],
        }
        return execute_actions_with_guard(
            pending_intent.actions,
            robot_state,
            history,
            user_text,
            assistant_message,
            config,
            skill_catalog,
            dry_run=dry_run,
            debug_lines=pending_intent.debug_lines,
        )
    if normalized in CANCEL_WORDS:
        updated_state = RobotState(**vars(robot_state))
        updated_state.last_user_text = user_text
        return {
            "assistant_reply": f"已取消本次待执行操作：{pending_intent.summary}。",
            "updated_state": updated_state,
            "pending_intent": None,
            "executed_results": [],
        }
    updated_state = RobotState(**vars(robot_state))
    updated_state.last_user_text = user_text
    return {
        "assistant_reply": (
            f"当前有一条待确认操作：{pending_intent.summary}。"
            "如果要执行，请回复“确认”；如果不要执行，请回复“取消”。"
        ),
        "updated_state": updated_state,
        "pending_intent": pending_intent,
        "executed_results": [],
    }


def handle_chat_turn(
    user_text: str,
    recent_history: list[dict[str, str]],
    robot_state: RobotState,
    pending_intent: PendingIntent | None,
    skill_catalog: dict[str, dict[str, Any]],
    config: dict[str, Any],
    dry_run: bool = False,
) -> dict[str, Any]:
    updated_state = RobotState(**vars(robot_state))
    updated_state.last_user_text = user_text

    if pending_intent is not None:
        return handle_pending_turn(
            user_text,
            updated_state,
            pending_intent,
            recent_history,
            config,
            skill_catalog,
            dry_run=dry_run,
        )

    if not normalize_text(user_text):
        return {
            "assistant_reply": "我还没有收到有效指令，你可以直接告诉我要去哪里、怎么移动，或者问我能做什么。",
            "updated_state": updated_state,
            "pending_intent": None,
            "executed_results": [],
        }

    system_prompt = build_chat_system_prompt(skill_catalog, robot_state, None, config)
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    messages.extend(recent_history)
    messages.append({"role": "user", "content": user_text})
    tools = core.build_tools(skill_catalog)

    try:
        raw = core.call_chat_completion(
            {
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
            },
            config,
        )
        raw_message = raw["choices"][0]["message"]
    except Exception as exc:
        return {
            "assistant_reply": local_fallback_reply(user_text, updated_state, skill_catalog, error_text=str(exc)),
            "updated_state": updated_state,
            "pending_intent": None,
            "executed_results": [],
        }

    tool_calls = raw_message.get("tool_calls") or []
    if not tool_calls:
        assistant_reply = (raw_message.get("content") or "").strip()
        if not assistant_reply:
            assistant_reply = local_fallback_reply(user_text, updated_state, skill_catalog)
        return {
            "assistant_reply": assistant_reply,
            "updated_state": updated_state,
            "pending_intent": None,
            "executed_results": [],
        }

    try:
        planned_actions = parse_tool_calls(raw_message, skill_catalog)
    except Exception as exc:
        return {
            "assistant_reply": local_fallback_reply(user_text, updated_state, skill_catalog, error_text=str(exc)),
            "updated_state": updated_state,
            "pending_intent": None,
            "executed_results": [],
        }

    require_confirmation = should_confirm_actions(planned_actions, skill_catalog)
    debug_lines = build_dry_run_debug_lines(user_text, planned_actions, skill_catalog, require_confirmation)

    if require_confirmation:
        pending = build_pending_intent(planned_actions)
        pending.debug_lines = debug_lines
        return {
            "assistant_reply": append_debug_block(pending.preview_reply, debug_lines, dry_run),
            "updated_state": updated_state,
            "pending_intent": pending,
            "executed_results": [],
        }

    return execute_actions_with_guard(
        planned_actions,
        updated_state,
        recent_history,
        user_text,
        raw_message,
        config,
        skill_catalog,
        dry_run=dry_run,
        debug_lines=debug_lines,
    )


def run_chat_loop(
    dry_run: bool = False,
    history_limit: int = CHAT_HISTORY_LIMIT,
    show_banner: bool = True,
    show_capabilities_only: bool = False,
) -> int:
    core.ensure_stdout_encoding()
    core.load_dotenv()
    config = core.load_agent_config()
    config.setdefault("agent", {})
    config["agent"].setdefault("confirmation_policy", core.get_confirmation_policy(config))
    skill_catalog = core.build_skill_catalog(config, core.load_waypoint_names())
    session = ChatSession()

    banner = build_startup_banner(skill_catalog)
    if show_banner or show_capabilities_only:
        print(banner)
    if show_capabilities_only:
        return 0

    while True:
        try:
            user_text = input("你：").strip()
        except EOFError:
            print("\n助手：会话结束。")
            return 0
        except KeyboardInterrupt:
            print("\n助手：已中断会话。")
            return 130

        if normalize_text(user_text) in EXIT_WORDS:
            print("助手：会话结束。")
            return 0

        result = handle_chat_turn(
            user_text,
            session.history,
            session.robot_state,
            session.pending_intent,
            skill_catalog,
            config,
            dry_run=dry_run,
        )
        session.robot_state = result["updated_state"]
        session.pending_intent = result.get("pending_intent")
        assistant_reply = result["assistant_reply"]
        session.append("user", user_text, history_limit=history_limit)
        session.append("assistant", assistant_reply, history_limit=history_limit)
        print(f"助手：{assistant_reply}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scout chat agent")
    parser.add_argument("--dry-run", action="store_true", help="Plan only, do not execute skills")
    parser.add_argument(
        "--history-limit",
        type=int,
        default=CHAT_HISTORY_LIMIT,
        help="How many recent turns to keep in memory",
    )
    parser.add_argument("--no-banner", action="store_true", help="Do not print startup capability banner")
    parser.add_argument("--show-capabilities", action="store_true", help="Print startup capability banner and exit")
    args = parser.parse_args()
    raise SystemExit(
        run_chat_loop(
            dry_run=args.dry_run,
            history_limit=max(args.history_limit, 1),
            show_banner=not args.no_banner,
            show_capabilities_only=args.show_capabilities,
        )
    )


if __name__ == "__main__":
    main()
