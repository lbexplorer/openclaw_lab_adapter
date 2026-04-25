#!/usr/bin/env python3
"""Project-level main agent that routes natural language to local skills."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any
from urllib import error, request

import yaml


ROOT_DIR = Path(__file__).resolve().parents[1]
AGENT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = AGENT_DIR / "config" / "agent_config.yaml"
ENV_PATH = ROOT_DIR / ".env"
NAVIGATE_REL_PATH = Path("skills") / "scout_navigation_manager" / "scripts" / "navigate.py"
MOVE_CLIENT_REL_PATH = Path("skills") / "scout_move_control" / "scripts" / "move_control_client.py"
NAVIGATE_PATH = ROOT_DIR / NAVIGATE_REL_PATH
MOVE_CLIENT_PATH = ROOT_DIR / MOVE_CLIENT_REL_PATH
NAVIGATION_CONFIG_PATH = ROOT_DIR / "skills" / "scout_navigation_manager" / "config" / "navigation_position.yaml"
MOVE_COMMAND_PATTERN = re.compile(r"^(forward|backward|left|right|stop)\s+(\d+(?:\.\d+)?)$")


def ensure_stdout_encoding() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass


def load_dotenv(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        os.environ.setdefault(key, value)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_agent_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"agent config not found: {path}")
    return load_yaml(path)


def load_module(module_path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, str(module_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_waypoint_names() -> list[str]:
    if NAVIGATE_PATH.exists():
        navigate_module = load_module(NAVIGATE_PATH, "navigate_module_for_main_agent")
        return list(navigate_module.load_waypoint_names(str(NAVIGATION_CONFIG_PATH)))

    raw = load_yaml(NAVIGATION_CONFIG_PATH)
    positions = raw.get("navigation_positions") or raw.get("destinations") or {}
    return sorted(positions.keys())


def get_env_value(primary_name: str | None, fallback_names: list[str] | None = None, default: str = "") -> str:
    names = []
    if primary_name:
        names.append(primary_name)
    names.extend(fallback_names or [])
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return default


def _normalize_lines(values: Any) -> list[str]:
    if isinstance(values, str):
        return [values.strip()] if values.strip() else []
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def build_skill_catalog(config: dict[str, Any], waypoint_names: list[str]) -> dict[str, dict[str, Any]]:
    skills: dict[str, dict[str, Any]] = {}
    agent_cfg = config.get("agent") or {}
    confirmation_policy = dict(agent_cfg.get("confirmation_policy") or {})

    for name, payload in (config.get("skills") or {}).items():
        if not payload.get("enabled", True):
            continue

        skill_payload = {
            "description": str(payload.get("description", "")).strip(),
            "arguments": dict(payload.get("arguments") or {}),
            "examples": _normalize_lines(payload.get("examples")),
            "capabilities": _normalize_lines(payload.get("capabilities")),
            "query_keywords": _normalize_lines(payload.get("query_keywords")),
            "risk_level": str(payload.get("risk_level", "high")).strip().lower() or "high",
            "status_supported": bool(payload.get("status_supported", False)),
            "confirmation_policy": confirmation_policy,
        }
        if name == "scout_navigation_manager":
            skill_payload["available_waypoints"] = waypoint_names
        skills[name] = skill_payload
    return skills


def format_skill_catalog_for_prompt(skill_catalog: dict[str, dict[str, Any]]) -> str:
    lines = []
    for name, payload in skill_catalog.items():
        lines.append(f"- {name}: {payload.get('description', '')}")
        capabilities = payload.get("capabilities") or []
        if capabilities:
            lines.append("  能力: " + "；".join(capabilities))
        arguments = payload.get("arguments") or {}
        if arguments:
            arg_text = "；".join(f"{arg}: {desc}" for arg, desc in arguments.items())
            lines.append(f"  参数: {arg_text}")
        examples = payload.get("examples") or []
        if examples:
            lines.append("  示例: " + "；".join(examples))
        waypoints = payload.get("available_waypoints") or []
        if waypoints:
            lines.append("  可用地点: " + "、".join(waypoints))
        lines.append(f"  风险等级: {payload.get('risk_level', 'high')}")
    return "\n".join(lines)


def format_capability_overview(skill_catalog: dict[str, dict[str, Any]]) -> str:
    lines = ["当前已启用 skills："]
    for name, payload in skill_catalog.items():
        lines.append(f"- {name}: {payload.get('description', '')}")
        capabilities = payload.get("capabilities") or []
        if capabilities:
            lines.append("  可执行操作: " + "；".join(capabilities))
        arguments = payload.get("arguments") or {}
        if arguments:
            lines.append("  参数说明: " + "；".join(f"{arg}={desc}" for arg, desc in arguments.items()))
        examples = payload.get("examples") or []
        if examples:
            lines.append("  示例: " + "；".join(examples))
        waypoints = payload.get("available_waypoints") or []
        if waypoints:
            lines.append("  导航地点: " + "、".join(waypoints))
    return "\n".join(lines)


def list_skills(skill_catalog: dict[str, dict[str, Any]]) -> None:
    print(format_capability_overview(skill_catalog))


def build_system_prompt(skill_catalog: dict[str, dict[str, Any]], max_actions: int) -> str:
    catalog_text = format_skill_catalog_for_prompt(skill_catalog)
    return textwrap.dedent(
        f"""
        你是 openclaw_lab_adapter 的主智能体。你的任务是根据用户自然语言请求决定是否调用本地技能。
        你只能使用下面列出的工具，不能虚构新的工具。
        最多调用 {max_actions} 次工具，按顺序执行。

        当前技能目录:
        {catalog_text}

        规则:
        1. 查询能力、参数说明、地点列表、最近状态时，不要调用工具，直接用中文回答。
        2. 导航类请求优先调用 scout_navigation_manager。
        3. 底盘动作请求调用 scout_move_control。
        4. command 必须是英文动作字符串，支持单条或逗号分隔的动作序列，例如 `forward 1` 或 `forward 1, left 1`。
        5. target 必须是可用地点中的标准地点名。
        6. 如果请求超出已知能力，不要调用工具，直接用中文简短说明当前无法执行。
        """
    ).strip()


def build_messages(system_prompt: str, user_text: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]


def build_tools(skill_catalog: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    tools = []
    for skill_name, payload in skill_catalog.items():
        properties = {}
        required = []
        for arg_name, description in payload.get("arguments", {}).items():
            arg_schema = {"type": "string", "description": description}
            if skill_name == "scout_navigation_manager" and arg_name == "target":
                waypoints = payload.get("available_waypoints") or []
                if waypoints:
                    arg_schema["enum"] = waypoints
            properties[arg_name] = arg_schema
            required.append(arg_name)

        description_parts = [payload.get("description", "")]
        capabilities = payload.get("capabilities") or []
        if capabilities:
            description_parts.append("能力: " + "；".join(capabilities))
        examples = payload.get("examples") or []
        if examples:
            description_parts.append("示例: " + "；".join(examples))

        tools.append(
            {
                "type": "function",
                "function": {
                    "name": skill_name,
                    "description": " ".join(part for part in description_parts if part),
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                        "additionalProperties": False,
                    },
                },
            }
        )
    return tools


def split_move_command_segments(command: str) -> list[dict[str, Any]]:
    segments = []
    for raw_segment in str(command).split(","):
        segment = raw_segment.strip()
        if not segment:
            continue
        match = MOVE_COMMAND_PATTERN.fullmatch(segment)
        if match is None:
            raise ValueError(f"invalid move command segment: {segment}")
        action = match.group(1)
        duration = float(match.group(2))
        if duration <= 0:
            raise ValueError(f"move duration must be positive: {segment}")
        segments.append(
            {
                "raw": segment,
                "action": action,
                "duration": duration,
            }
        )
    if not segments:
        raise ValueError("move command is empty")
    return segments


def validate_tool_call(skill_name: str, arguments: dict[str, Any], skill_catalog: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if skill_name not in skill_catalog:
        raise ValueError(f"unsupported skill: {skill_name}")
    if not isinstance(arguments, dict):
        raise ValueError(f"arguments for {skill_name} must be an object")

    if skill_name == "scout_navigation_manager":
        target = str(arguments.get("target", "")).strip()
        waypoints = skill_catalog[skill_name].get("available_waypoints", [])
        if not target:
            raise ValueError("navigation target is empty")
        if waypoints and target not in waypoints:
            raise ValueError(f"unknown navigation target: {target}")
        return {"target": target}

    if skill_name == "scout_move_control":
        command = str(arguments.get("command", "")).strip()
        split_move_command_segments(command)
        return {"command": command}

    raise ValueError(f"no validator for skill: {skill_name}")


def get_confirmation_policy(config: dict[str, Any]) -> dict[str, Any]:
    policy = dict(((config.get("agent") or {}).get("confirmation_policy")) or {})
    return {
        "simple_move_max_seconds": float(policy.get("simple_move_max_seconds", 1.0)),
        "always_confirm_navigation": bool(policy.get("always_confirm_navigation", True)),
        "always_confirm_multi_step_move": bool(policy.get("always_confirm_multi_step_move", True)),
        "direct_actions": _normalize_lines(policy.get("direct_actions")) or ["stop"],
    }


def should_confirm_action(
    skill_name: str,
    arguments: dict[str, Any],
    skill_catalog: dict[str, dict[str, Any]],
) -> bool:
    payload = skill_catalog.get(skill_name) or {}
    policy = dict(payload.get("confirmation_policy") or {})
    risk_level = str(payload.get("risk_level", "high")).lower()

    if skill_name == "scout_navigation_manager":
        return bool(policy.get("always_confirm_navigation", True))

    if skill_name != "scout_move_control":
        return risk_level != "low"

    direct_actions = set(_normalize_lines(policy.get("direct_actions")) or ["stop"])
    segments = split_move_command_segments(str(arguments.get("command", "")))
    if len(segments) > 1 and bool(policy.get("always_confirm_multi_step_move", True)):
        return True

    if len(segments) != 1:
        return risk_level != "low"

    segment = segments[0]
    if segment["action"] in direct_actions:
        return False

    max_seconds = float(policy.get("simple_move_max_seconds", 1.0))
    if segment["duration"] <= max_seconds and risk_level == "low":
        return False
    return True


def summarize_action(skill_name: str, arguments: dict[str, Any]) -> str:
    if skill_name == "scout_navigation_manager":
        return f"导航到{arguments['target']}"
    if skill_name == "scout_move_control":
        return f"执行底盘动作 {arguments['command']}"
    return f"执行 {skill_name}"


def call_chat_completion(payload: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    llm_cfg = config.get("llm") or {}

    api_key = get_env_value(None, list(llm_cfg.get("api_key_envs") or []))
    if not api_key:
        raise RuntimeError("missing API key, set MOONSHOT_API_KEY, KIMI_API_KEY, OPENCLAW_LLM_API_KEY, or OPENAI_API_KEY")

    base_url = get_env_value(str(llm_cfg.get("base_url_env", "")).strip(), default=str(llm_cfg.get("default_base_url", "")).strip())
    model = get_env_value(str(llm_cfg.get("model_env", "")).strip(), default=str(llm_cfg.get("default_model", "")).strip())
    timeout_seconds = float(llm_cfg.get("timeout_seconds", 30))

    request_payload = {"model": model, **payload}
    endpoint = base_url.rstrip("/") + "/chat/completions"
    body = json.dumps(request_payload).encode("utf-8")
    req = request.Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM request failed: HTTP {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"LLM request failed: {exc}") from exc

    return raw


def execute_action(skill_name: str, arguments: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
    command, script_path, script_rel_path = build_execution_command(skill_name, arguments)
    return run_skill_command(
        skill_name,
        command,
        script_path,
        script_rel_path,
        arguments,
        dry_run=dry_run,
    )


def build_execution_command(skill_name: str, arguments: dict[str, Any]) -> tuple[list[str], Path, Path]:
    if skill_name == "scout_navigation_manager":
        script_path = NAVIGATE_PATH
        script_rel_path = NAVIGATE_REL_PATH
        command = [sys.executable, str(script_rel_path), "--go", arguments["target"]]
    elif skill_name == "scout_move_control":
        script_path = MOVE_CLIENT_PATH
        script_rel_path = MOVE_CLIENT_REL_PATH
        command = [sys.executable, str(script_rel_path), "--cmd", arguments["command"]]
    else:
        raise ValueError(f"unsupported execution skill: {skill_name}")

    return command, script_path, script_rel_path


def run_skill_command(
    skill_name: str,
    command: list[str],
    script_path: Path,
    script_rel_path: Path,
    arguments: dict[str, Any],
    dry_run: bool = False,
) -> dict[str, Any]:
    del script_rel_path
    if not script_path.exists():
        raise FileNotFoundError(f"skill script not found: {script_path}")

    if dry_run:
        return {
            "skill": skill_name,
            "status": "dry_run",
            "command": command,
            "arguments": arguments,
            "cwd": str(ROOT_DIR),
        }

    completed = subprocess.run(
        command,
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
        check=False,
    )
    status = "ok" if completed.returncode == 0 else "error"
    return {
        "skill": skill_name,
        "status": status,
        "arguments": arguments,
        "command": command,
        "cwd": str(ROOT_DIR),
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def query_skill_status(skill_name: str, dry_run: bool = False) -> dict[str, Any]:
    if skill_name == "scout_navigation_manager":
        script_path = NAVIGATE_PATH
        script_rel_path = NAVIGATE_REL_PATH
        command = [sys.executable, str(script_rel_path), "--status"]
    elif skill_name == "scout_move_control":
        script_path = MOVE_CLIENT_PATH
        script_rel_path = MOVE_CLIENT_REL_PATH
        command = [sys.executable, str(script_rel_path), "--status"]
    else:
        raise ValueError(f"unsupported status skill: {skill_name}")

    return run_skill_command(
        skill_name,
        command,
        script_path,
        script_rel_path,
        {"query": "status"},
        dry_run=dry_run,
    )


def normalize_message(raw_message: dict[str, Any]) -> dict[str, Any]:
    message = {
        "role": raw_message.get("role", "assistant"),
    }
    if "content" in raw_message and raw_message["content"] is not None:
        message["content"] = raw_message["content"]
    if raw_message.get("reasoning_content"):
        message["reasoning_content"] = raw_message["reasoning_content"]
    if raw_message.get("tool_calls"):
        message["tool_calls"] = raw_message["tool_calls"]
    return message


def agent_loop(user_text: str, config: dict[str, Any], skill_catalog: dict[str, dict[str, Any]], dry_run: bool) -> dict[str, Any]:
    agent_cfg = config.get("agent") or {}
    max_actions = int(agent_cfg.get("max_actions", 3))
    messages = build_messages(build_system_prompt(skill_catalog, max_actions), user_text)
    tools = build_tools(skill_catalog)
    executed_actions = []

    for _ in range(max_actions + 1):
        raw = call_chat_completion(
            {
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
            },
            config,
        )
        try:
            raw_message = raw["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"unexpected LLM response: {raw}") from exc

        messages.append(normalize_message(raw_message))
        tool_calls = raw_message.get("tool_calls") or []
        if not tool_calls:
            return {
                "reply": (raw_message.get("content") or "").strip(),
                "actions": executed_actions,
            }

        for tool_call in tool_calls:
            tool_name = tool_call.get("function", {}).get("name", "")
            raw_arguments = tool_call.get("function", {}).get("arguments", "{}")
            try:
                parsed_arguments = json.loads(raw_arguments)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid tool call arguments for {tool_name}: {raw_arguments}") from exc

            validated_arguments = validate_tool_call(tool_name, parsed_arguments, skill_catalog)
            result = execute_action(tool_name, validated_arguments, dry_run=dry_run)
            executed_actions.append(result)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", tool_name),
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    raise RuntimeError("agent exceeded max action iterations")


def main() -> None:
    ensure_stdout_encoding()
    load_dotenv()
    parser = argparse.ArgumentParser(description="Scout main agent")
    parser.add_argument("--text", type=str, help='Natural language request, e.g. "带我去前台"')
    parser.add_argument("--dry-run", action="store_true", help="Plan only, do not execute skills")
    parser.add_argument("--list-skills", action="store_true", help="List enabled skills")
    args = parser.parse_args()

    config = load_agent_config()
    config.setdefault("agent", {})
    config["agent"].setdefault("confirmation_policy", get_confirmation_policy(config))
    skill_catalog = build_skill_catalog(config, load_waypoint_names())

    if args.list_skills:
        list_skills(skill_catalog)
        return

    if not args.text:
        parser.print_help(sys.stderr)
        raise SystemExit(1)

    output = agent_loop(args.text, config, skill_catalog, dry_run=args.dry_run)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
