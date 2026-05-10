# Scout Agent

`agent/` 目录提供项目级智能体入口，负责把自然语言请求转换成本地 skills 调度。

当前支持：

- `scout_navigation_manager`：命名地点导航
- `scout_move_control`：前进、后退、转向、停止
- `patrol_fixed_points`：固定点巡逻，可在检测到人员后停止
- `check_person_detected`：读取已有人员检测 topic
- `trigger_existing_tracking_handoff`：确认目标已进入现有大车到小车协同交接链路

## 入口

### `agent/chat_agent.py`

多轮对话入口，适合日常交互和调度调试。

- 启动后展示当前 skills 能力
- 支持能力问答和动作执行
- `--dry-run` 下会输出调度日志视图



### `agent/scout_main_agent.py`

单轮命令入口，适合快速验证一条自然语言指令。

## 启动

先准备环境变量，可写入项目根目录 `.env`：

```bash
OPENCLAW_LLM_API_KEY=your_key
OPENCLAW_LLM_BASE_URL=https://api.moonshot.cn/v1
OPENCLAW_LLM_MODEL=kimi-k2.5
```

常用命令：

```bash
python agent/chat_agent.py
python agent/chat_agent.py --dry-run
python agent/chat_agent.py --show-capabilities
python agent/scout_main_agent.py --text "去工位2"
python agent/scout_main_agent.py --text "前进1秒然后左转1秒" --dry-run
python agent/scout_main_agent.py --list-skills
```



说明：

- `--dry-run`：只验证调度，不真正执行 skill
- `--show-capabilities`：打印当前技能能力后退出
- `--no-banner`：启动时不打印能力清单
- `--text`：执行单条命令

```bash
python agent/scout_main_agent.py --text "去工位2" --dry-run
```

- dry-run：确认后只模拟执行，不控制小车
- 正常模式：确认后真实执行，高风险需确认，低风险可直接执行

这一步主要确认：

- 模型是否能正确识别技能
- 参数是否合法
- 是否进入了预期的确认流程



## 调试

推荐顺序：

```bash
python3 agent/chat_agent.py --show-capabilities
python3 agent/chat_agent.py --dry-run
python3 agent/scout_main_agent.py --text "去原点" --dry-run
python3 test/test_chat_agent_static.py
python3 test/test_scout_main_agent_static.py
```

如果 agent 已启动但动作执行失败，通常是对应 skill 服务没有启动；如果是 dry-run，则主要关注调度日志中的 `LLM输出 / 参数校验 / 执行命令 / 确认策略` 四段。

调试记录和截图统一维护在 `docs/debug/` 与 `docs/images/`。
