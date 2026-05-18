# Scout Agent

`agent/` 提供项目级智能体入口，负责把自然语言请求转换为本地 skills 调度。agent 只编排本仓库 adapter skills，不直接改写真实 ROS / DDS / 导航 / 跟踪接口。

## 支持能力

- `scout_navigation_manager`：命名地点导航。
- `scout_move_control`：前进、后退、转向、停止。
- `patrol_fixed_points`：固定点巡逻，可在检测到人员后停止。
- `check_person_detected`：读取已有人员检测 topic。
- `trigger_existing_tracking_handoff`：确认目标已进入现有大车到小车协同交接链路。

## 入口

### `chat_agent.py`

多轮对话入口，适合日常交互和调度调试。

- 启动后展示当前 skills 能力。
- 支持能力问答和动作执行。
- `--dry-run` 下只输出调度日志，不执行真实动作。

### `scout_main_agent.py`

单轮命令入口，适合快速验证一条自然语言指令。

- `--text` 指定自然语言任务。
- `--dry-run` 只验证调度和参数。
- `--list-skills` 输出当前可调度 skill。

## 启动

先准备模型环境变量，可写入项目根目录 `.env`：

```bash
OPENCLAW_LLM_API_KEY=your_key
OPENCLAW_LLM_BASE_URL=https://api.moonshot.cn/v1
OPENCLAW_LLM_MODEL=kimi-k2.5
```

推荐用 Terminator 启动交互入口：

```bash
bash scripts/launch_agent_terminator.sh
```

常用命令：

```bash
python3 agent/chat_agent.py
python3 agent/chat_agent.py --dry-run
python3 agent/chat_agent.py --show-capabilities
python3 agent/scout_main_agent.py --list-skills
python3 agent/scout_main_agent.py --text "去工位2" --dry-run
python3 agent/scout_main_agent.py --text "前进1秒然后左转1秒" --dry-run
python3 agent/scout_main_agent.py --text "开始巡逻，检测到人后停止并触发小车协同跟踪" --dry-run
```

去掉 `--dry-run` 会执行真实 skill。涉及底盘动作、巡逻或导航目标下发前，必须确认现场安全，并确保对应 skill 服务已经启动。

## 调试顺序

推荐从项目根目录执行：

```bash
python3 agent/chat_agent.py --show-capabilities
python3 agent/scout_main_agent.py --list-skills
python3 agent/scout_main_agent.py --text "去原点" --dry-run
python3 test/test_chat_agent_static.py
python3 test/test_scout_main_agent_static.py
```

如果 agent 已启动但动作执行失败，通常是对应 skill 服务没有启动。完整现场启动和 skill 测试命令见 [../docs/debug/scout_bridge_quickstart_cn.md](../docs/debug/scout_bridge_quickstart_cn.md)。
