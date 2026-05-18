# Scout 桥接调试快速开始

本文是 `docs/debug/` 下的现场调试主入口，合并原 `skills调试.md` 中重复的启动、skill 测试和最小闭环命令。

默认约定：

- 车端 adapter 项目目录用 `$ADAPTER_WS` 表示，常见值为 `/ssd1/workspace/openclaw_lab_adapter`。
- Sailors 工作空间用 `$SAILORS_WS` 表示，常见值为 `/ssd1/workspace/sailors_onboard`。
- 仓库内文件统一使用相对路径，例如 `skills/scout_navigation_manager/config/navigation_position.yaml`。
- Windows 本机路径不要写入文档或命令；需要同步到车端时，在仓库根目录执行 `scp -r . user@host:/target/openclaw_lab_adapter/`。

基础环境：

```bash
export ADAPTER_WS=/ssd1/workspace/openclaw_lab_adapter
export SAILORS_WS=/ssd1/workspace/sailors_onboard

cd "$ADAPTER_WS"
source /opt/ros/noetic/setup.bash
source "$SAILORS_WS/build/devel/setup.bash"
```

## 1. 小车启动

终端 1：启动底盘、传感器和基础驱动。

```bash
cd "$ADAPTER_WS"
source /opt/ros/noetic/setup.bash
source "$SAILORS_WS/build/devel/setup.bash"
bash 1startup.bash
```

基础检查：

```bash
rostopic list | grep -E "/scan|/imu|/odom|/cmd_vel"
```

终端 2：启动地图、定位和导航。

```bash
cd "$ADAPTER_WS"
source /opt/ros/noetic/setup.bash
source "$SAILORS_WS/build/devel/setup.bash"
bash 2nav.bash
```

导航检查：

```bash
rosnode list | grep -E "map_server|amcl|move_base"
rostopic list | grep move_base
```

## 2. 桥接启动

如果已经手动启动并确认 `1startup.bash`、`2nav.bash`，可以用 Terminator 一次打开两个 adapter skill 窗口：

```bash
cd "$ADAPTER_WS"
bash scripts/launch_skills_terminator.sh
```

这个脚本只启动 `navigation_manager_server.py` 和 `move_control_server.py`，不会启动底层驱动、地图、定位或导航服务。底层服务仍需要按第 1 节先完成现场安全确认。

终端 3：启动命名地点导航 skill。

```bash
cd "$ADAPTER_WS"
source /opt/ros/noetic/setup.bash
source "$SAILORS_WS/build/devel/setup.bash"
python3 skills/scout_navigation_manager/scripts/navigation_manager_server.py \
  --waypoints skills/scout_navigation_manager/config/navigation_position.yaml
```

终端 4：启动底盘动作 skill。

```bash
cd "$ADAPTER_WS"
source /opt/ros/noetic/setup.bash
source "$SAILORS_WS/build/devel/setup.bash"
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
python3 skills/scout_navigation_manager/scripts/navigate.py --go "巡逻点三"
python3 skills/scout_navigation_manager/scripts/navigate.py --go "工位2"
python3 skills/scout_navigation_manager/scripts/navigate.py --cancel
python3 skills/scout_navigation_manager/scripts/navigate.py --go "去火星基地"
python3 skills/scout_navigation_manager/scripts/navigate.py --go "巡逻点四"
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
  --patrol-points "巡逻点4,原点"
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

## 5. 人员检测结果读取调试

`check_person_detected` 只读取已有 ROS topic，不启动检测模型。执行前需要先启动 Sailors 感知节点，或启动 toy_utils 检测链路。

启动 Sailors 感知节点：

```bash
bash 3sensing_node.bash
```

确认检测相关 topic：

```bash
rostopic list | grep -E "track|detect|object|camera"
rostopic echo /track_pose
```

默认读取 `/track_pose`：

```bash
python3 skills/check_person_detected/scripts/check_person_detected.py --check
python3 skills/check_person_detected/scripts/check_person_detected.py --status
```

读取 toy_utils `/DetectMsg`：

```bash
python3 skills/check_person_detected/scripts/check_person_detected.py --check --source detect_msg
```

自定义 topic 和等待时间：

```bash
python3 skills/check_person_detected/scripts/check_person_detected.py --check \
  --source track_pose \
  --topic /track_pose \
  --timeout-seconds 3
```

异常输入测试：

```bash
python3 skills/check_person_detected/scripts/check_person_detected.py --check --source camera
```

返回结果应为统一 `SkillResult` JSON。重点看：

- `status`：`success / timeout / unavailable / invalid_input`
- `data.person_detected`：是否检测到人员
- `data.source`：`track_pose` 或 `detect_msg`
- `data.source_topic`：实际订阅 topic
- `data.target_pose`：`/track_pose` 返回的目标位姿
- `data.detections`：`/DetectMsg` 返回的人员检测框
- `data.confidence_threshold`：人员置信度阈值

## 6. 追踪交接启动调试

追踪交接当前优先复用现场已有能力：大车检测到目标后输出 `/track_pose`，现有桥接链路把目标交给小车，小车按现场既有流程前往目标并执行静态人员跟踪。

`trigger_existing_tracking_handoff` 只读取和确认已有 `/track_pose`，不主动发布 `/track_pose`，不启动 DDS，不远程配置小车，也不直接发布 `/cmd_vel`。

大车侧启动 Sailors 感知与 DDS 发送链路：

```bash
source /opt/ros/noetic/setup.bash
source "$SAILORS_WS/build/devel/setup.bash"

# 启动人员目标位姿来源。现场如果已有 3sensing_node.bash，可优先使用脚本。
bash 3sensing_node.bash

# 启动 /track_pose -> DDS PoseMsgTopic。现场如果已有 4dds_bridge.sh，可优先使用脚本。
bash 4dds_bridge.sh
```

如果没有上述脚本，使用真实节点命令：

```bash
source /opt/ros/noetic/setup.bash
source "$SAILORS_WS/build/devel/setup.bash"
rosrun perception sensing_node
rosrun saw_dds track_converter_sub
```

小车侧启动 DDS 接收链路：

```bash
source /opt/ros/noetic/setup.bash
source "$SAILORS_WS/build/devel/setup.bash"
rosrun saw_dds track_converter_pub
rostopic echo /track_pose
```

如果现场使用 toy_utils 静态跟踪链路，另开终端启动并检查：

```bash
source /opt/ros/noetic/setup.bash
source "$SAILORS_WS/build/devel/setup.bash"
roslaunch perception_toy detection_tracking.launch
roslaunch planner_toy track_planner.launch
rostopic echo /DetectMsg
rostopic echo /TrackMsg
rostopic echo /cmd_vel
```

大车侧确认目标已经进入现有交接链路：

```bash
cd "$ADAPTER_WS"
source /opt/ros/noetic/setup.bash
python3 skills/trigger_existing_tracking_handoff/scripts/trigger_handoff.py --status
python3 skills/trigger_existing_tracking_handoff/scripts/trigger_handoff.py --check \
  --topic /track_pose \
  --timeout-seconds 3
```

只有当大车和桥接 subscriber 在同一个 ROS master 中可见时，才启用 subscriber 强校验：

```bash
python3 skills/trigger_existing_tracking_handoff/scripts/trigger_handoff.py --check \
  --topic /track_pose \
  --timeout-seconds 3 \
  --require-subscriber true
```

巡逻中检测到人员后停止当前巡逻，并把目标交给现有追踪链路：

```bash
python3 skills/patrol_fixed_points/scripts/patrol.py --run --stop-on-detection true
python3 skills/trigger_existing_tracking_handoff/scripts/trigger_handoff.py --check --timeout-seconds 3
```

返回结果应为统一 `SkillResult` JSON。重点看：

- `data.handoff_triggered`：是否确认目标已进入现有协同交接链路
- `data.target_pose`：从 `/track_pose` 读取到的人员目标位姿
- `data.source_topic`：实际读取 topic
- `data.bridge_subscriber_seen`：是否在 ROS master 中看到 subscriber
- `data.dds_topic`：当前交接对应的 DDS topic，默认为 `PoseMsgTopic`

注意：`handoff_triggered=true` 只代表大车侧目标已进入现有交接链路，不等价于小车已经到达目标或已经开始发布跟踪 `/cmd_vel`。小车侧真实跟踪状态仍需通过 `/track_pose`、`/TrackMsg`、`/cmd_vel` 和现场既有日志确认。

## 7. LLM 调度

先配置模型密钥，可放在项目根目录 `.env`：

```bash
OPENCLAW_LLM_API_KEY=your_key
OPENCLAW_LLM_BASE_URL=https://api.moonshot.cn/v1
OPENCLAW_LLM_MODEL=kimi-k2.5
```

用 Terminator 启动交互式大模型调度入口：

```bash
bash scripts/launch_agent_terminator.sh
```

查看 agent 能力：

```bash
python3 agent/chat_agent.py
python3 agent/chat_agent.py --show-capabilities
python3 agent/scout_main_agent.py --list-skills
```

dry-run 调度测试，不控制小车：

```bash
python3 agent/scout_main_agent.py --text "去工位2" --dry-run
python3 agent/scout_main_agent.py --text "前进1秒然后停止" --dry-run
python3 agent/scout_main_agent.py --text "开始巡逻" --dry-run
python3 agent/scout_main_agent.py --text "停止巡逻" --dry-run
python3 agent/scout_main_agent.py --text "检查是否检测到人员" --dry-run
python3 agent/scout_main_agent.py --text "触发小车协同跟踪" --dry-run
python3 agent/scout_main_agent.py --text "开始巡逻，检测到人后停止并触发小车协同跟踪" --dry-run
```

真实调度测试，确认现场安全后再执行：

```bash
python3 agent/scout_main_agent.py --text "去工位2"
python3 agent/scout_main_agent.py --text "前进1秒然后停止"
python3 agent/scout_main_agent.py --text "开始巡逻"
python3 agent/scout_main_agent.py --text "停止巡逻"
python3 agent/scout_main_agent.py --text "检查是否检测到人员"
python3 agent/scout_main_agent.py --text "触发小车协同跟踪"
python3 agent/scout_main_agent.py --text "开始巡逻，检测到人后停止并触发小车协同跟踪"
```

## 8. 最小闭环

按顺序确认：

```bash
bash 1startup.bash
bash 2nav.bash
python3 skills/scout_navigation_manager/scripts/navigation_manager_server.py --waypoints skills/scout_navigation_manager/config/navigation_position.yaml
python3 skills/scout_move_control/scripts/move_control_server.py
python3 skills/patrol_fixed_points/scripts/patrol.py --status
python3 skills/patrol_fixed_points/scripts/patrol.py --stop
python3 skills/check_person_detected/scripts/check_person_detected.py --status
python3 skills/trigger_existing_tracking_handoff/scripts/trigger_handoff.py --status
python3 agent/scout_main_agent.py --text "去工位2" --dry-run
python3 agent/scout_main_agent.py --text "前进1秒然后停止" --dry-run
python3 agent/scout_main_agent.py --text "开始巡逻" --dry-run
python3 agent/scout_main_agent.py --text "检查是否检测到人员" --dry-run
python3 agent/scout_main_agent.py --text "触发小车协同跟踪" --dry-run
```

如果 dry-run 正常，再去掉 `--dry-run` 做真实动作测试。

追踪闭环现场命令：

```bash
# 大车侧：先启动 Sailors 感知和 DDS 发送链路，再启动 adapter skill 检查。
bash 3sensing_node.bash
bash 4dds_bridge.sh
python3 skills/check_person_detected/scripts/check_person_detected.py --check --timeout-seconds 3
python3 skills/patrol_fixed_points/scripts/patrol.py --run --stop-on-detection true
python3 skills/trigger_existing_tracking_handoff/scripts/trigger_handoff.py --check --timeout-seconds 3

# 小车侧：确认已有接收和跟踪链路已启动。
rosrun saw_dds track_converter_pub
rostopic echo /track_pose
rostopic echo /cmd_vel
```

## 9. 新增 skill 后的文档同步流程

每完成一个新的 skill，必须同步更新本文，避免现场调试时找不到命令。

如果用户只要求补充启动方式、快速测试或文档同步，只需要先完成最小必填项，不必重新梳理真实接口或补齐所有扩展测试。

最小必填：

1. skill 的启动前置条件，例如依赖哪个 ROS service、topic 或已有 skill。
2. skill 的最小命令行测试方式。
3. `--status` 或等价状态查询命令。
4. 必要的安全提示，例如真实动作命令需确认现场安全后再执行。

建议补充：

1. 正常输入测试命令。
2. 异常输入测试命令。
3. 返回结果中需要重点观察的 `SkillResult` 字段。
4. agent dry-run 调度命令。
5. 真实调度命令，且必须注明确认现场安全后再执行。

建议新增位置：

- 底层或桥接服务：放在“桥接启动”或对应调试章节。
- 单独 skill：新增一个独立调试章节。
- agent 可调用 skill：同步补充到“LLM 调度”和“最小闭环”。
