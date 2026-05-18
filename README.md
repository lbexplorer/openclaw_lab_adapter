# OpenClaw Lab Adapter

`openclaw_lab_adapter` 是实验室 Scout 无人车协同 Demo 的适配项目，用于把现有车端能力封装为可由 agent 调度的 skills。


## Demo 主线

当前主线固定为：

```text
大车固定点巡逻
-> 持续人员检测
-> 检测到静态人员
-> 发送协同指令
-> 小车接收指令
-> 小车前往目标位置
-> 小车执行静态人员跟踪
```

## 当前能力

- `scout_navigation_manager`：命名地点导航，默认对接 ROS1 `move_base`。
- `scout_move_control`：底盘动作封装，默认对接 ROS1 `/cmd_vel`。
- `patrol_fixed_points`：固定点巡逻，复用导航 skill。
- `check_person_detected`：读取已有人员检测 topic，不启动检测模型。
- `trigger_existing_tracking_handoff`：确认目标进入现有协同交接链路。
- `agent/chat_agent.py`：交互式 LLM 调度入口。
- `agent/scout_main_agent.py`：单次自然语言任务调度入口。

## 快速启动

使用 skills 前，必须先在无人车上启动并确认底层车端服务：

- `1startup.sh`
- `2nav.bash`

推荐启动 adapter skills：

```bash
cd /ssd1/workspace/openclaw_lab_adapter
bash scripts/launch_skills_terminator.sh
```

推荐启动 LLM agent：

```bash
cd /ssd1/workspace/openclaw_lab_adapter
bash scripts/launch_agent_terminator.sh
```

完整启动步骤见：

- [Scout Navigation and LLM Skills Startup Guide](docs/debug/scout_navigation_llm_startup_guide.md)
- [Scout 桥接快速开始](demo_0.4_skills.md)

## 目录

```text
agent/          # LLM agent 入口和配置
skills/         # 本项目封装的 adapter skills
scripts/        # Terminator 启动脚本
docs/debug/     # 启动、调试和现场验证文档
docs/interfaces/# 真实接口确认记录
docs/design/    # 设计和协议说明
test/           # 静态测试
```

## 重要边界

- 真实 ROS / DDS / 导航 / 跟踪接口以 `sailors_onboard-main` 为准。
- 本仓库默认只做 adapter、agent、文档和测试。
- 不直接修改真实运动控制接口，除非任务明确要求并完成风险确认。
- 涉及 `/cmd_vel` 或导航目标下发前，必须确认现场安全。

## 进度记录

项目进展统一记录在：

- [docs/log/DEVELOPMENT_LOG.md](docs/log/DEVELOPMENT_LOG.md)
