# Scout Agent

`agent/` 目录提供项目级智能体入口，负责把自然语言请求转换成本地 skills 调度。

当前支持：

- `scout_navigation_manager`：命名地点导航
- `scout_move_control`：前进、后退、转向、停止

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
python agent/scout_main_agent.py --text "带我去前台"
python agent/scout_main_agent.py --text "前进1秒然后左转1秒" --dry-run
python agent/scout_main_agent.py --list-skills
```

## 调试

推荐顺序：

```bash
python agent/chat_agent.py --show-capabilities
python agent/chat_agent.py --dry-run
python agent/scout_main_agent.py --text "去实验台" --dry-run
python test/test_chat_agent_static.py
python test/test_scout_main_agent_static.py
```

如果 agent 已启动但动作执行失败，通常是对应 skill 服务没有启动；如果是 dry-run，则主要关注调度日志中的 `LLM输出 / 参数校验 / 执行命令 / 确认策略` 四段。
