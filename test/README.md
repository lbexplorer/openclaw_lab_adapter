# Test

当前目录用于放置 `openclaw_lab_adapter` 的本地测试脚本。

## scout_navigation_manager 静态测试

在项目根目录执行：

```bash
python test/test_scout_navigation_static.py
```

这个脚本会自动检查：

- `skills/scout_navigation_manager/scripts/` 下脚本是否存在
- `navigation_position.yaml` 是否存在、结构是否正确
- 每个地点是否包含 `x / y / yaw`
- `aliases` 是否是字符串列表
- 自然语言短句是否能解析到预期标准地点名

推荐从 `openclaw_lab_adapter` 根目录运行，这样输出路径最直观。

## scout_main_agent 静态测试

在项目根目录执行：

```bash
python test/test_scout_main_agent_static.py
```

这个脚本会自动检查：

- `agent/` 目录是否完整
- `agent_config.yaml` 是否存在且结构正确
- Kimi/OpenAI 兼容工具定义是否能正确生成
- 工具参数校验是否能接受合法 skill 调用
- 非法地点是否会被正确拒绝
