# Test

`test/` 放置本仓库的本地静态测试脚本，主要验证 agent、skills 配置、命令解析和接口封装的结构正确性。

这些测试不启动真实 ROS 节点，不控制无人车，也不替代现场联调。涉及真实导航、底盘动作、人员检测和协同交接的验证仍以 `docs/debug/scout_bridge_quickstart_cn.md` 中的现场流程为准。

## 一次性运行

在项目根目录执行：

```powershell
Get-ChildItem test -Filter test_*.py | ForEach-Object { python $_.FullName }
```

Linux / ROS 车端环境可使用：

```bash
for f in test/test_*.py; do python3 "$f"; done
```

## 单项测试

### `test_scout_navigation_static.py`

检查 `scout_navigation_manager` 脚本、`navigation_position.yaml` 结构、地点坐标和别名解析。

```bash
python3 test/test_scout_navigation_static.py
```

### `test_scout_main_agent_static.py`

检查 `scout_main_agent.py`、agent 配置、工具定义、参数校验和非法输入拒绝逻辑。

```bash
python3 test/test_scout_main_agent_static.py
```

### `test_chat_agent_static.py`

检查 `chat_agent.py` 的能力展示、中文动作解析、导航短句解析、未知地点和超范围请求处理。

```bash
python3 test/test_chat_agent_static.py
```

### `test_patrol_fixed_points_static.py`

检查固定点巡逻配置、巡逻脚本入口、状态字段和异常输入处理。

```bash
python3 test/test_patrol_fixed_points_static.py
```

### `test_check_person_detected_static.py`

检查人员检测结果读取 skill 的配置、topic 来源、状态字段和异常输入处理。

```bash
python3 test/test_check_person_detected_static.py
```

### `test_trigger_existing_tracking_handoff_static.py`

检查协同交接确认 skill 的配置、DDS / `/track_pose` 边界、状态字段和异常输入处理。

```bash
python3 test/test_trigger_existing_tracking_handoff_static.py
```

## 预期用途

- 提交前快速检查配置和静态逻辑。
- 文档整理或 agent 路由修改后确认入口没有断裂。
- 现场联调前先排除明显的本仓库结构问题。
