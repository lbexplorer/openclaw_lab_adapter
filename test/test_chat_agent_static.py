#!/usr/bin/env python3
"""Static checks for the LLM-driven Scout chat agent."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT_DIR / "agent"
SCRIPT_PATH = AGENT_DIR / "chat_agent.py"


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
    if not SCRIPT_PATH.exists():
        fail(f"缺少聊天式 agent 脚本: {SCRIPT_PATH}")
    print(f"[OK] {SCRIPT_PATH}")


def make_llm_response(content: str = "", tool_calls: list[dict] | None = None) -> dict:
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls or [],
                }
            }
        ]
    }


def tool_call(call_id: str, name: str, arguments: dict) -> dict:
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(arguments, ensure_ascii=False),
        },
    }


def install_fake_llm(module, responses: list[dict]) -> None:
    queue = list(responses)

    def fake_call_chat_completion(payload, config):
        del payload, config
        if not queue:
            fail("fake LLM 响应队列已耗尽")
        return queue.pop(0)

    module.core.call_chat_completion = fake_call_chat_completion


def install_fake_execution(module) -> None:
    module.core.query_skill_status = lambda skill_name, dry_run=False: {
        "skill": skill_name,
        "status": "dry_run" if dry_run else "ok",
        "returncode": 0,
        "stdout": "ready",
    }
    module.core.execute_action = lambda skill_name, arguments, dry_run=False: {
        "skill": skill_name,
        "status": "dry_run" if dry_run else "ok",
        "arguments": arguments,
        "returncode": 0,
        "stdout": "ok",
    }


def check_startup_banner(module) -> None:
    config = module.core.load_agent_config()
    skill_catalog = module.core.build_skill_catalog(config, module.core.load_waypoint_names())
    banner = module.build_startup_banner(skill_catalog)
    if "当前已启用 skills" not in banner:
        fail("启动 banner 缺少技能标题")
    if "参数说明" not in banner or "示例" not in banner:
        fail("启动 banner 未展示参数或示例")
    if "导航地点" not in banner:
        fail("启动 banner 未展示导航地点")
    print("[OK] 启动展示通过")


def check_capability_queries(module) -> None:
    config = module.core.load_agent_config()
    skill_catalog = module.core.build_skill_catalog(config, module.core.load_waypoint_names())
    state = module.RobotState()

    install_fake_llm(module, [make_llm_response(content="我可以导航和控制底盘。")])
    capability = module.handle_chat_turn("你能做什么", [], state, None, skill_catalog, config, dry_run=True)
    if "导航" not in capability["assistant_reply"]:
        fail("能力查询回复不符合预期")

    install_fake_llm(module, [make_llm_response(content="")])
    move_help = module.handle_chat_turn("scout_move_control 能做什么", [], state, None, skill_catalog, config, dry_run=True)
    if "scout_move_control 可以执行这些操作" not in move_help["assistant_reply"]:
        fail("单 skill 能力查询未走本地回退")

    install_fake_llm(module, [make_llm_response(content="")])
    waypoints = module.handle_chat_turn("有哪些可到达地点", [], state, None, skill_catalog, config, dry_run=True)
    if "当前可到达的命名地点有" not in waypoints["assistant_reply"]:
        fail("地点列表查询回复不正确")
    print("[OK] 能力问答通过")


def check_confirmation_and_execution(module) -> None:
    config = module.core.load_agent_config()
    skill_catalog = module.core.build_skill_catalog(config, module.core.load_waypoint_names())
    install_fake_execution(module)
    state = module.RobotState()

    install_fake_llm(
        module,
        [
            make_llm_response(
                tool_calls=[tool_call("call_nav", "scout_navigation_manager", {"target": "接待区"})]
            )
        ],
    )
    nav = module.handle_chat_turn("带我去前台", [], state, None, skill_catalog, config, dry_run=True)
    if "待执行操作" not in nav["assistant_reply"]:
        fail("导航请求未进入待确认流程")
    if "[Dry Run 调度日志]" not in nav["assistant_reply"] or "LLM输出:" not in nav["assistant_reply"]:
        fail("导航 dry-run 未输出调度信息")
    if "参数校验:" not in nav["assistant_reply"] or "执行命令:" not in nav["assistant_reply"] or "确认策略:" not in nav["assistant_reply"]:
        fail("导航 dry-run 未按四段式展示")
    pending = nav.get("pending_intent")
    if pending is None or pending.actions[0].arguments.get("target") != "接待区":
        fail("导航待确认目标解析失败")

    install_fake_llm(module, [make_llm_response(content="好的，正在前往接待区。")])
    confirmed_nav = module.handle_chat_turn("确认", [], state, pending, skill_catalog, config, dry_run=True)
    if "正在前往接待区" not in confirmed_nav["assistant_reply"]:
        fail("导航确认执行回复不符合预期")
    if "validated_arguments:" not in confirmed_nav["assistant_reply"]:
        fail("导航确认后的 dry-run 未保留调度信息")

    install_fake_llm(
        module,
        [
            make_llm_response(
                tool_calls=[tool_call("call_stop", "scout_move_control", {"command": "stop 0.5"})]
            ),
            make_llm_response(content="已发送停止指令。"),
        ],
    )
    stop_result = module.handle_chat_turn("停止", [], state, None, skill_catalog, config, dry_run=True)
    if stop_result.get("pending_intent") is not None:
        fail("stop 不应进入待确认流程")
    if "停止" not in stop_result["assistant_reply"]:
        fail("stop 直接执行回复不符合预期")
    if "[Dry Run 调度日志]" not in stop_result["assistant_reply"]:
        fail("stop 的 dry-run 未输出调度信息")

    install_fake_llm(
        module,
        [
            make_llm_response(
                tool_calls=[tool_call("call_move", "scout_move_control", {"command": "forward 1"})]
            ),
            make_llm_response(content="已发送底盘动作：forward 1。"),
        ],
    )
    move_result = module.handle_chat_turn("前进1秒", [], state, None, skill_catalog, config, dry_run=True)
    if move_result.get("pending_intent") is not None:
        fail("简单短动作不应进入待确认流程")
    if "forward 1" not in move_result["assistant_reply"]:
        fail("简单短动作直接执行回复不符合预期")
    if "raw_arguments:" not in move_result["assistant_reply"] or "command:" not in move_result["assistant_reply"]:
        fail("简单短动作 dry-run 未展示原始参数或命令")
    if "decision: 可直接执行" not in move_result["assistant_reply"]:
        fail("简单短动作未展示确认策略决策")

    install_fake_llm(
        module,
        [
            make_llm_response(
                tool_calls=[tool_call("call_long", "scout_move_control", {"command": "forward 2"})]
            )
        ],
    )
    long_move = module.handle_chat_turn("前进2秒", [], state, None, skill_catalog, config, dry_run=True)
    pending_long = long_move.get("pending_intent")
    if pending_long is None:
        fail("长时动作应进入待确认流程")

    canceled = module.handle_chat_turn("取消", [], state, pending_long, skill_catalog, config, dry_run=True)
    if "已取消本次待执行操作" not in canceled["assistant_reply"]:
        fail("取消待执行动作失败")
    print("[OK] 确认与执行策略通过")


def check_invalid_tool_call_fallback(module) -> None:
    config = module.core.load_agent_config()
    skill_catalog = module.core.build_skill_catalog(config, module.core.load_waypoint_names())
    state = module.RobotState()

    install_fake_llm(
        module,
        [
            make_llm_response(
                tool_calls=[tool_call("call_bad", "scout_move_control", {"command": "jump 1"})]
            )
        ],
    )
    bad = module.handle_chat_turn("跳一下", [], state, None, skill_catalog, config, dry_run=True)
    if "当前已启用 skills" not in bad["assistant_reply"]:
        fail("非法 tool call 未回退到能力说明")
    print("[OK] 非法 tool call 回退通过")


def main() -> None:
    check_files()
    module = load_module(SCRIPT_PATH, "chat_agent_module")
    check_startup_banner(module)
    check_capability_queries(module)
    check_confirmation_and_execution(module)
    check_invalid_tool_call_fallback(module)
    print("[OK] chat_agent 静态测试通过")


if __name__ == "__main__":
    main()
