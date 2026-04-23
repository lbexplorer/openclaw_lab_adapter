#!/usr/bin/env python3
"""Static checks for the project-level main agent."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml


ROOT_DIR = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT_DIR / "agent"
CONFIG_PATH = AGENT_DIR / "config" / "agent_config.yaml"
SCRIPT_PATH = AGENT_DIR / "scout_main_agent.py"


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(1)


def load_module(module_path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, str(module_path))
    if spec is None or spec.loader is None:
        fail(f"无法加载模块: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_yaml(path: Path) -> dict:
    if not path.exists():
        fail(f"配置文件不存在: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def check_files() -> None:
    for path in [AGENT_DIR, CONFIG_PATH, SCRIPT_PATH]:
        if not path.exists():
            fail(f"缺少文件或目录: {path}")
        print(f"[OK] {path}")


def check_config_structure(config: dict) -> None:
    llm_cfg = config.get("llm")
    agent_cfg = config.get("agent")
    skills_cfg = config.get("skills")
    if not isinstance(llm_cfg, dict):
        fail("llm 配置缺失")
    if not isinstance(agent_cfg, dict):
        fail("agent 配置缺失")
    if not isinstance(skills_cfg, dict) or not skills_cfg:
        fail("skills 配置为空")

    if not llm_cfg.get("default_base_url"):
        fail("缺少 llm.default_base_url")
    if not llm_cfg.get("default_model"):
        fail("缺少 llm.default_model")
    if int(agent_cfg.get("max_actions", 0)) <= 0:
        fail("agent.max_actions 非法")
    print(f"[OK] max_actions = {agent_cfg.get('max_actions')}")

    for name, payload in skills_cfg.items():
        if not isinstance(payload, dict):
            fail(f"{name} 配置不是字典")
        if not payload.get("description"):
            fail(f"{name} 缺少 description")
        if not isinstance(payload.get("arguments"), dict):
            fail(f"{name} 缺少 arguments 映射")
        print(f"[OK] {name}")


def check_tool_validation(module) -> None:
    config = module.load_agent_config(CONFIG_PATH)
    skill_catalog = module.build_skill_catalog(config, module.load_waypoint_names())

    tools = module.build_tools(skill_catalog)
    if not isinstance(tools, list) or len(tools) < 2:
        fail("工具定义生成失败")
    print("[OK] 工具定义生成通过")

    nav_args = module.validate_tool_call(
        "scout_navigation_manager", {"target": "接待区"}, skill_catalog
    )
    if nav_args["target"] != "接待区":
        fail("合法导航工具参数验证失败")

    move_args = module.validate_tool_call(
        "scout_move_control", {"command": "forward 1"}, skill_catalog
    )
    if move_args["command"] != "forward 1":
        fail("合法移动工具参数验证失败")
    print("[OK] 合法工具参数验证通过")

    try:
        module.validate_tool_call(
            "scout_navigation_manager", {"target": "火星基地"}, skill_catalog
        )
    except ValueError:
        print("[OK] 非法地点被正确拒绝")
    else:
        fail("非法地点未被拒绝")


def check_message_normalization(module) -> None:
    raw_message = {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"id": "call_1", "function": {"name": "demo", "arguments": "{}"}}],
    }
    normalized = module.normalize_message(raw_message)
    if normalized.get("role") != "assistant" or "tool_calls" not in normalized:
        fail("normalize_message 处理失败")
    print("[OK] 消息归一化通过")


def main() -> None:
    check_files()
    config = load_yaml(CONFIG_PATH)
    check_config_structure(config)
    module = load_module(SCRIPT_PATH, "llm_agent_module")
    check_message_normalization(module)
    check_tool_validation(module)
    print("[OK] scout_main_agent 静态测试通过")


if __name__ == "__main__":
    main()
