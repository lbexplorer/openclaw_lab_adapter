# Scout 桥接快速开始

本文只保留现场调试最常用的启动和测试命令。完整排查细节见 `skills调试.md`。

默认项目目录：

```bash
cd /ssd1/workspace/openclaw_lab_adapter
source /opt/ros/noetic/setup.bash
```

## 1. 小车启动

终端 1：启动底盘、传感器和基础驱动。

```bash
cd /ssd1/workspace/openclaw_lab_adapter
source /opt/ros/noetic/setup.bash
bash 1startup.bash
```

基础检查：

```bash
rostopic list | grep -E "/scan|/imu|/odom|/cmd_vel"
```

终端 2：启动地图、定位和导航。

```bash
cd /ssd1/workspace/openclaw_lab_adapter
source /opt/ros/noetic/setup.bash
bash 2nav.bash
```

导航检查：

```bash
rosnode list | grep -E "map_server|amcl|move_base"
rostopic list | grep move_base
```

## 2. 桥接启动

终端 3：启动命名地点导航 skill。

```bash
cd /ssd1/workspace/openclaw_lab_adapter
source /opt/ros/noetic/setup.bash
python3 skills/scout_navigation_manager/scripts/navigation_manager_server.py \
  --waypoints skills/scout_navigation_manager/config/navigation_position.yaml
```

终端 4：启动底盘动作 skill。

```bash
cd /ssd1/workspace/openclaw_lab_adapter
source /opt/ros/noetic/setup.bash
python3 skills/scout_move_control/scripts/move_control_server.py
```

接口检查：

```bash
rosservice call /scout_navigation_manager/list_positions
rosservice call /scout_navigation_manager/navigation_status
python3 skills/scout_move_control/scripts/move_control_client.py --status
```

## 3. 导航调试

查看当前地点配置：

```bash
python3 - <<'PY'
import yaml
with open("skills/scout_navigation_manager/config/navigation_position.yaml", "r", encoding="utf-8") as f:
    data = yaml.safe_load(f)
print("\n".join(data["navigation_positions"].keys()))
PY
```

客户端脚本测试：

```bash
python3 skills/scout_navigation_manager/scripts/navigate.py --go 原点
python3 skills/scout_navigation_manager/scripts/navigate.py --go "巡逻点二"
python3 skills/scout_navigation_manager/scripts/navigate.py --go "工位2"
python3 skills/scout_navigation_manager/scripts/navigate.py --cancel
python3 skills/scout_navigation_manager/scripts/navigate.py --go "去火星基地"
```

ROS service 测试：

```bash
rosservice call /scout_navigation_manager/set_pose "data: '原点'"
rosservice call /scout_navigation_manager/set_pose "data: '工位2'"
rosservice call /scout_navigation_manager/navigation_status
rosservice call /scout_navigation_manager/cancel_navigation
```

底盘动作测试：

```bash
python3 skills/scout_move_control/scripts/move_control_client.py --cmd "forward 1"
python3 skills/scout_move_control/scripts/move_control_client.py --cmd "left 1"
python3 skills/scout_move_control/scripts/move_control_client.py --cmd "stop 0.5"
python3 skills/scout_move_control/scripts/move_control_client.py --cmd "forward 1, stop 0.5, left 1"
```

## 4. 固定点巡逻调试

`patrol_fixed_points` 复用 `scout_navigation_manager`，执行前必须先启动 `navigation_manager_server.py`，并确认 `move_base` 正常。

默认巡逻路线：

```text
原点 -> 巡逻点2 -> 巡逻点3 -> 巡逻点4 -> 原点
```

查看巡逻状态：

```bash
python3 skills/patrol_fixed_points/scripts/patrol.py --status
```

重置巡逻状态：

```bash
python3 skills/patrol_fixed_points/scripts/patrol.py --reset
```

停止巡逻并取消当前导航：

```bash
python3 skills/patrol_fixed_points/scripts/patrol.py --stop
```

执行默认巡逻：

```bash
python3 skills/patrol_fixed_points/scripts/patrol.py --run
```

执行自定义巡逻点：

```bash
python3 skills/patrol_fixed_points/scripts/patrol.py --run \
  --patrol-points "原点,巡逻点2,巡逻点3,巡逻点4,原点"
```

异常输入测试：

```bash
python3 skills/patrol_fixed_points/scripts/patrol.py --run --patrol-points "火星基地"
```

返回结果应为统一 `SkillResult` JSON。重点看：

- `status`：`success / failed / timeout / unavailable / invalid_input`
- `data.patrol_status`：`idle / moving / arrived / finished / stopped / error`
- `data.current_waypoint`：当前巡逻点
- `data.completed_waypoints`：已完成巡逻点
- `data.failed_waypoint`：失败巡逻点
- `data.last_navigation_status`：最近一次导航状态

## 5. LLM 调度

先配置模型密钥，可放在项目根目录 `.env`：

```bash
OPENCLAW_LLM_API_KEY=your_key
OPENCLAW_LLM_BASE_URL=https://api.moonshot.cn/v1
OPENCLAW_LLM_MODEL=kimi-k2.5
```

查看 agent 能力：

```bash
python3 agent/chat_agent.py --show-capabilities
python3 agent/scout_main_agent.py --list-skills
```

dry-run 调度测试，不控制小车：

```bash
python3 agent/scout_main_agent.py --text "去工位2" --dry-run
python3 agent/scout_main_agent.py --text "前进1秒然后停止" --dry-run
python3 agent/scout_main_agent.py --text "开始巡逻" --dry-run
python3 agent/scout_main_agent.py --text "停止巡逻" --dry-run
```

真实调度测试，确认现场安全后再执行：

```bash
python3 agent/scout_main_agent.py --text "去工位2"
python3 agent/scout_main_agent.py --text "前进1秒然后停止"
python3 agent/scout_main_agent.py --text "开始巡逻"
python3 agent/scout_main_agent.py --text "停止巡逻"
```

## 6. 最小闭环

按顺序确认：

```bash
bash 1startup.bash
bash 2nav.bash
python3 skills/scout_navigation_manager/scripts/navigation_manager_server.py --waypoints skills/scout_navigation_manager/config/navigation_position.yaml
python3 skills/scout_move_control/scripts/move_control_server.py
python3 skills/patrol_fixed_points/scripts/patrol.py --status
python3 skills/patrol_fixed_points/scripts/patrol.py --stop
python3 agent/scout_main_agent.py --text "去工位2" --dry-run
python3 agent/scout_main_agent.py --text "前进1秒然后停止" --dry-run
python3 agent/scout_main_agent.py --text "开始巡逻" --dry-run
```

如果 dry-run 正常，再去掉 `--dry-run` 做真实动作测试。

## 7. 新增 skill 后的文档同步流程

每完成一个新的 skill，必须同步更新本文，避免现场调试时找不到命令。

新增 skill 后至少补充：

1. skill 的启动前置条件，例如依赖哪个 ROS service、topic 或已有 skill。
2. skill 的最小命令行测试方式。
3. `--status` 或等价状态查询命令。
4. 正常输入测试命令。
5. 异常输入测试命令。
6. 返回结果中需要重点观察的 `SkillResult` 字段。
7. agent dry-run 调度命令。
8. 真实调度命令，且必须注明确认现场安全后再执行。

建议新增位置：

- 底层或桥接服务：放在“桥接启动”或对应调试章节。
- 单独 skill：新增一个独立调试章节。
- agent 可调用 skill：同步补充到“LLM 调度”和“最小闭环”。
