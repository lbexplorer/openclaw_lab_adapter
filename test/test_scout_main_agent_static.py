#!/usr/bin/env python3
"""Static checks for the project-level main agent."""

from __future__ import annotations

import importlib.util
import sys
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
    if "confirmation_policy" not in agent_cfg:
        fail("agent.confirmation_policy 缺失")
    timeout_cfg = agent_cfg.get("skill_timeouts")
    if not isinstance(timeout_cfg, dict):
        fail("agent.skill_timeouts 缺失")
    if int(timeout_cfg.get("default_status_seconds", 0)) <= 0:
        fail("agent.skill_timeouts.default_status_seconds 非法")
    patrol_timeout = ((timeout_cfg.get("patrol_fixed_points") or {}).get("execute_seconds"))
    if int(patrol_timeout or 0) < 120:
        fail("patrol_fixed_points.execute_seconds 不应短于单点巡逻等待时间")
    detection_timeout = ((timeout_cfg.get("check_person_detected") or {}).get("execute_seconds"))
    if int(detection_timeout or 0) <= 0:
        fail("check_person_detected.execute_seconds 非法")
    print(f"[OK] max_actions = {agent_cfg.get('max_actions')}")

    for name, payload in skills_cfg.items():
        if not isinstance(payload, dict):
            fail(f"{name} 配置不是字典")
        if not payload.get("description"):
            fail(f"{name} 缺少 description")
        if not isinstance(payload.get("arguments"), dict):
            fail(f"{name} 缺少 arguments 映射")
        if not payload.get("examples"):
            fail(f"{name} 缺少 examples")
        if not payload.get("capabilities"):
            fail(f"{name} 缺少 capabilities")
        print(f"[OK] {name}")


def check_catalog_and_validation(module) -> None:
    config = module.load_agent_config(CONFIG_PATH)
    skill_catalog = module.build_skill_catalog(config, module.load_waypoint_names())

    overview = module.format_capability_overview(skill_catalog)
    if "当前已启用 skills" not in overview:
        fail("能力总览生成失败")
    if "导航地点" not in overview and "导航点" not in overview:
        fail("导航地点未写入能力总览")

    tools = module.build_tools(skill_catalog)
    if not isinstance(tools, list) or len(tools) < 2:
        fail("工具定义生成失败")
    print("[OK] 工具定义生成通过")

    nav_target = "工位2"
    nav_args = module.validate_tool_call(
        "scout_navigation_manager", {"target": nav_target}, skill_catalog
    )
    if nav_args["target"] != nav_target:
        fail("合法导航工具参数验证失败")

    move_args = module.validate_tool_call(
        "scout_move_control", {"command": "forward 1"}, skill_catalog
    )
    if move_args["command"] != "forward 1":
        fail("合法移动工具参数验证失败")

    chained_args = module.validate_tool_call(
        "scout_move_control", {"command": "forward 1, left 1"}, skill_catalog
    )
    if chained_args["command"] != "forward 1, left 1":
        fail("连续移动动作参数验证失败")

    patrol_args = module.validate_tool_call(
        "patrol_fixed_points",
        {"action": "run", "patrol_points": "default", "loop": "false", "stop_on_detection": "false"},
        skill_catalog,
    )
    if patrol_args["action"] != "run" or patrol_args["patrol_points"] != "" or patrol_args["loop"] != "false":
        fail("巡逻工具参数默认值验证失败")
    patrol_stop_args = module.validate_tool_call(
        "patrol_fixed_points",
        {"action": "stop", "patrol_points": "", "loop": "false", "stop_on_detection": "false"},
        skill_catalog,
    )
    if patrol_stop_args["action"] != "stop":
        fail("巡逻停止工具参数验证失败")
    stop_command, _, _ = module.build_execution_command("patrol_fixed_points", patrol_stop_args)
    if "--stop" not in stop_command:
        fail("巡逻停止 action 应映射为 patrol.py --stop")
    detection_args = module.validate_tool_call(
        "check_person_detected",
        {"source": "track_pose", "topic": "", "timeout_seconds": "3", "confidence_threshold": "0.5"},
        skill_catalog,
    )
    if detection_args["source"] != "track_pose":
        fail("人员检测工具参数验证失败")
    detection_command, _, _ = module.build_execution_command("check_person_detected", detection_args)
    if "--check" not in detection_command or "--source" not in detection_command:
        fail("人员检测执行命令应调用 check_person_detected.py --check")
    print("[OK] 合法工具参数验证通过")

    try:
        module.validate_tool_call(
            "scout_navigation_manager", {"target": "火星基地"}, skill_catalog
        )
    except ValueError:
        print("[OK] 非法地点被正确拒绝")
    else:
        fail("非法地点未被拒绝")

    try:
        module.validate_tool_call(
            "scout_move_control", {"command": "jump 1"}, skill_catalog
        )
    except ValueError:
        print("[OK] 非法动作被正确拒绝")
    else:
        fail("非法动作未被拒绝")


def check_skill_protocol(module) -> None:
    result = module.normalize_process_result(
        skill_name="scout_navigation_manager",
        operation="execute",
        arguments={"target": "工位2"},
        command=["python", "navigate.py", "--go", "工位2"],
        returncode=0,
        stdout="success=True resolved=工位2 message=true",
        stderr="",
    )
    if result.get("status") != module.skill_protocol.SkillStatus.ACCEPTED:
        fail("导航下发成功应归一化为 accepted，而不是 success")
    if result.get("execution_mode") != module.skill_protocol.ExecutionMode.ASYNC:
        fail("导航执行模式应为 async")
    for key in ["skill", "status", "execution_mode", "message", "data", "error", "trace"]:
        if key not in result:
            fail(f"SkillResult 缺少字段: {key}")

    failed = module.normalize_process_result(
        skill_name="scout_navigation_manager",
        operation="execute",
        arguments={"target": "火星基地"},
        command=["python", "navigate.py", "--go", "火星基地"],
        returncode=2,
        stdout="unknown waypoint: 火星基地",
        stderr="",
    )
    if failed.get("status") != module.skill_protocol.SkillStatus.INVALID_INPUT:
        fail("非法导航目标应归一化为 invalid_input")

    status_result = module.normalize_process_result(
        skill_name="scout_navigation_manager",
        operation="status",
        arguments={"query": "status"},
        command=["python", "navigate.py", "--status"],
        returncode=0,
        stdout="moving to 工位2",
        stderr="",
    )
    if status_result.get("status") != module.skill_protocol.SkillStatus.RUNNING:
        fail("moving to 状态应归一化为 running")

    patrol_stdout = module.skill_protocol.make_result(
        skill="patrol_fixed_points",
        status=module.skill_protocol.SkillStatus.SUCCESS,
        execution_mode=module.skill_protocol.ExecutionMode.SYNC,
        message="固定点巡逻已完成。",
        data={"patrol_status": "finished", "completed_waypoints": ["原点"]},
    )
    parsed_patrol = module.normalize_process_result(
        skill_name="patrol_fixed_points",
        operation="execute",
        arguments={"action": "run", "patrol_points": "", "loop": "false", "stop_on_detection": "false"},
        command=["python", "patrol.py", "--run"],
        returncode=0,
        stdout=__import__("json").dumps(patrol_stdout, ensure_ascii=False),
        stderr="",
    )
    if parsed_patrol.get("skill") != "patrol_fixed_points" or parsed_patrol.get("status") != module.skill_protocol.SkillStatus.SUCCESS:
        fail("巡逻 SkillResult JSON 未被 agent 正确解析")
    detection_stdout = module.skill_protocol.make_result(
        skill="check_person_detected",
        status=module.skill_protocol.SkillStatus.SUCCESS,
        execution_mode=module.skill_protocol.ExecutionMode.SYNC,
        message="已检测到人员。",
        data={"person_detected": True, "source_topic": "/track_pose"},
    )
    parsed_detection = module.normalize_process_result(
        skill_name="check_person_detected",
        operation="execute",
        arguments={"source": "track_pose", "topic": "", "timeout_seconds": "3", "confidence_threshold": "0.5"},
        command=["python", "check_person_detected.py", "--check"],
        returncode=0,
        stdout=__import__("json").dumps(detection_stdout, ensure_ascii=False),
        stderr="",
    )
    if parsed_detection.get("skill") != "check_person_detected" or parsed_detection.get("data", {}).get("person_detected") is not True:
        fail("人员检测 SkillResult JSON 未被 agent 正确解析")
    print("[OK] SkillResult 协议归一化通过")


def check_timeout_and_progress(module) -> None:
    config = module.load_agent_config(CONFIG_PATH)
    if int(module.get_skill_timeout(config, "patrol_fixed_points", "execute")) != 600:
        fail("巡逻 skill agent 总超时应为 600 秒")
    if int(module.get_skill_timeout(config, "scout_navigation_manager", "status")) != 15:
        fail("导航状态查询超时应为 15 秒")

    command = [sys.executable, "-c", "import time; time.sleep(2)"]
    result = module.run_skill_command(
        skill_name="patrol_fixed_points",
        command=command,
        script_path=SCRIPT_PATH,
        script_rel_path=SCRIPT_PATH,
        arguments={"patrol_points": ""},
        operation="execute",
        timeout_seconds=0.1,
    )
    if result.get("status") != module.skill_protocol.SkillStatus.TIMEOUT:
        fail("skill 子进程超时应返回 timeout")
    if (result.get("error") or {}).get("code") != "SKILL_PROCESS_TIMEOUT":
        fail("skill 子进程超时应记录 SKILL_PROCESS_TIMEOUT")
    if "timeout_seconds" not in result.get("trace", {}):
        fail("skill 子进程超时 trace 应记录 timeout_seconds")

    step = module.build_step_record(
        index=1,
        skill_name="patrol_fixed_points",
        arguments={"action": "run", "patrol_points": ""},
        operation="execute",
        timeout_seconds=600,
    )
    if step.get("status") != module.skill_protocol.SkillStatus.RUNNING:
        fail("步骤初始状态应为 running")
    for key in ["index", "skill", "arguments", "summary", "started_at", "timeout_seconds", "result"]:
        if key not in step:
            fail(f"步骤记录缺少字段: {key}")
    print("[OK] 超时与进度记录通过")


def check_confirmation_policy(module) -> None:
    config = module.load_agent_config(CONFIG_PATH)
    skill_catalog = module.build_skill_catalog(config, module.load_waypoint_names())

    if module.should_confirm_action("scout_navigation_manager", {"target": "工位2"}, skill_catalog) is not True:
        fail("导航动作应进入确认流程")
    if module.should_confirm_action("scout_move_control", {"command": "stop 0.5"}, skill_catalog) is not False:
        fail("stop 应可直接执行")
    if module.should_confirm_action("scout_move_control", {"command": "forward 1"}, skill_catalog) is not False:
        fail("简单短动作应可直接执行")
    if module.should_confirm_action("scout_move_control", {"command": "forward 2"}, skill_catalog) is not True:
        fail("长时动作应进入确认流程")
    print("[OK] 确认策略通过")


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
    check_catalog_and_validation(module)
    check_skill_protocol(module)
    check_timeout_and_progress(module)
    check_confirmation_policy(module)
    print("[OK] scout_main_agent 静态测试通过")


if __name__ == "__main__":
    main()
