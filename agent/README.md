# Scout Main Agent

这里存放 `openclaw_lab_adapter` 的项目级主智能体入口。

职责：

- 接收自然语言输入
- 调用 Kimi / OpenAI 兼容模型
- 选择并调度本项目 `skills/` 下的本地能力

当前主入口：

- `agent/scout_main_agent.py`

当前可调度 skills：

- `scout_navigation_manager`
- `scout_move_control`
