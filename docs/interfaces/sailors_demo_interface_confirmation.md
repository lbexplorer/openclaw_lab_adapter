# Sailors Demo 接口确认文档

本文用于确认当前 Demo 主线所需接口，避免后续封装 skill 时脱离真实无人车代码。

Demo 主线固定为：

```text
大车固定点巡逻
-> 持续人员检测
-> 检测到静态人员
-> 发送协同指令
-> 小车接收指令
-> 小车前往目标位置
-> 小车执行静态人员跟踪
```

当前结论：

- `openclaw_lab_adapter` 已验证可用：命名地点导航、底盘短动作、agent 调用单个 skill。
- `sailors_onboard-main` 已存在可复用真实能力：启动底盘/导航、感知节点、`track_pose` 发布、ROS 与 DDS `PoseMsg` 转换。
- `toy_utils` 中存在 `/DetectMsg -> /TrackMsg -> /cmd_vel` 的静态人员检测跟踪参考链路，但目录中 `planner_toy` 带 `CATKIN_IGNORE`，是否作为现场实际运行链路需要继续确认。
- 下一阶段应优先做接口封装，不应重写底层导航、视觉检测、DDS 或跟踪控制。

## 1. 已验证 Adapter 接口

### 1.1 命名地点导航 skill

接口名称：`scout_navigation_manager`

Adapter 文件：

- `skills/scout_navigation_manager/scripts/navigation_manager_server.py`
- `skills/scout_navigation_manager/scripts/navigate.py`
- `skills/scout_navigation_manager/config/navigation_position.yaml`
- `skills/scout_navigation_manager/SKILL.md`

真实底层能力：

- 对接 ROS1 `move_base` action。
- 输入命名地点或自然语言别名。
- 从 YAML 读取 `x / y / yaw`，转换成 `MoveBaseGoal`。

启动前提：

```bash
cd /ssd1/workspace/openclaw_lab_adapter
source /opt/ros/noetic/setup.bash
bash 1startup.bash
bash 2nav.bash
python3 skills/scout_navigation_manager/scripts/navigation_manager_server.py \
  --waypoints skills/scout_navigation_manager/config/navigation_position.yaml
```

ROS 接口：

| 接口 | 类型 | 方向 | 说明 |
|---|---|---|---|
| `/scout_navigation_manager/set_pose` | `scout_openclaw_msgs/SetString` 或 `std_msgs/String` topic fallback | 输入 | 下发目标地点名或自然语言短句 |
| `/scout_navigation_manager/navigation_status` | `std_srvs/Trigger` | 输出 | 查询导航状态 |
| `/scout_navigation_manager/list_positions` | `std_srvs/Trigger` | 输出 | 列出可用地点 |
| `/scout_navigation_manager/get_navigation_mode` | `std_srvs/Trigger` | 输出 | 返回 `named_waypoints` |

客户端命令：

```bash
python3 skills/scout_navigation_manager/scripts/navigate.py --go 原点
python3 skills/scout_navigation_manager/scripts/navigate.py --go "巡逻点二"
python3 skills/scout_navigation_manager/scripts/navigate.py --go "工位2"
rosservice call /scout_navigation_manager/navigation_status
```

输入：

- `target`：标准地点名，例如 `原点`、`巡逻点2`、`巡逻点3`、`巡逻点4`、`工位2`。
- 支持 aliases，例如 `巡逻点二`、`去工位2`。

输出：

- 服务成功：`success=True`，`message=true`。
- 状态：`ready`、`moving to xxx`、`finish`。

成功判断：

- `navigation_status` 从 `ready` 变为 `moving to xxx`。
- RViz 中目标点位落在可通行区域。
- `move_base` 规划并输出 `/cmd_vel`。
- 到达后状态变为 `finish`。

已知问题：

- debug 记录中出现过导航失败、雷达点云漂移、路径不可达或碰撞风险。适配层只负责下发目标，根因可能在 AMCL、点位、局部规划或底盘链路。
- 当前代码注释/文档提到 `/scout_navigation_manager/goal_dispatched`，客户端也会等待该 topic，但服务端当前未实际发布该 topic。这个接口需要后续修正或从文档中移除。
- 当前服务端用 `yaw` 计算四元数，debug 文档建议后续考虑直接保存/下发完整 orientation，减少二次转换误差。

### 1.2 底盘短动作 skill

接口名称：`scout_move_control`

Adapter 文件：

- `skills/scout_move_control/scripts/move_control_server.py`
- `skills/scout_move_control/scripts/move_control_client.py`
- `skills/scout_move_control/SKILL.md`

真实底层能力：

- 对接 ROS1 `/cmd_vel`。
- 将字符串命令转换为 `geometry_msgs/Twist`。

启动前提：

```bash
cd /ssd1/workspace/openclaw_lab_adapter
source /opt/ros/noetic/setup.bash
python3 skills/scout_move_control/scripts/move_control_server.py
```

ROS 接口：

| 接口 | 类型 | 方向 | 说明 |
|---|---|---|---|
| `/scout_move_control/chassis_command` | `std_msgs/String` | 输入 | 接收动作字符串 |
| `/scout_move_control/move_status` | `std_srvs/Trigger` | 输出 | 查询 `stop` 或 `moving` |
| `/cmd_vel` | `geometry_msgs/Twist` | 输出到底盘 | 实际速度控制 |

命令格式：

```text
forward 1
backward 1
left 1
right 1
stop 0.5
forward 1, stop 0.5, left 1
```

默认参数：

- 线速度：`0.20 m/s`
- 角速度：`0.60 rad/s`
- 发布频率：`20 Hz`

成功判断：

- `move_status` 初始为 `stop`。
- 下发动作后短暂变为 `moving`。
- `/cmd_vel` 有对应速度输出。
- 动作结束后自动发布停止并回到 `stop`。

已知边界：

- 运动中会拒绝新的运动命令。
- 该 skill 适合短距离调试和安全停止，不适合作为巡逻或跟踪的主要路径规划接口。

### 1.3 Agent 接口

接口名称：

- `scout_main_agent`
- `chat_agent`

Adapter 文件：

- `agent/scout_main_agent.py`
- `agent/chat_agent.py`
- `agent/config/agent_config.yaml`

当前能力：

- 读取 Kimi/OpenAI 兼容 API 配置。
- 将自然语言映射到已启用 skills。
- 当前已启用 `scout_navigation_manager` 和 `scout_move_control`。
- `chat_agent` 支持多轮对话、dry-run、确认/取消、能力查询。

启动命令：

```bash
python3 agent/chat_agent.py --show-capabilities
python3 agent/chat_agent.py --dry-run
python3 agent/scout_main_agent.py --text "去工位2" --dry-run
python3 agent/scout_main_agent.py --text "前进1秒然后停止" --dry-run
```

真实执行前提：

- `.env` 或环境变量中配置 API key。
- 对应 skill 服务已启动。
- 导航/底盘真实 ROS 链路已启动并经过安全确认。

成功判断：

- 能列出当前 skills。
- 能把 `去工位2` 解析为 `scout_navigation_manager(target=工位2)`。
- 能把 `前进1秒` 解析为 `scout_move_control(command=forward 1)`。
- 高风险导航进入确认流程。
- 简单短动作和停止可按配置直接执行。

当前限制：

- Agent 只能调用单个或少量局部 skill。
- 尚未具备 Demo 主流程编排能力。
- 尚未接入巡逻、人员检测、DDS 下发、小车接收、静态人员跟踪。

## 2. Sailors 真实启动接口

真实代码来源：

- `sailors_onboard-main/sailors_onboard-main/sh/quick_start/1startup.sh`
- `sailors_onboard-main/sailors_onboard-main/sh/quick_start/2nav.bash`
- `sailors_onboard-main/sailors_onboard-main/sh/quick_start/3sensing_node.bash`
- `sailors_onboard-main/sailors_onboard-main/sh/quick_start/4dds_bridge.sh`

### 2.1 底盘、传感器和驱动启动

命令：

```bash
source /opt/ros/noetic/setup.bash
source /ssd1/workspace/sailors_onboard/build/devel/setup.bash
systemctl restart ptp4l.service
systemctl restart phc2sys.service
roslaunch scout_launch startup.launch
```

输出检查：

```bash
rostopic list | grep -E "/scan|/imu|/odom|/cmd_vel"
```

成功判断：

- `/scan`、`/imu`、`/odom`、`/cmd_vel` 存在。
- 串口、雷达、IMU、里程计不持续报硬错误。

### 2.2 地图、定位和导航启动

命令：

```bash
source /opt/ros/noetic/setup.bash
source /ssd1/workspace/sailors_onboard/build/devel/setup.bash
roslaunch scout_launch nav.launch
```

输出检查：

```bash
rosnode list | grep -E "map_server|amcl|move_base"
rostopic list | grep move_base
```

成功判断：

- `/map_server`、`/amcl`、`/move_base` 在线。
- `/move_base/goal`、`/move_base/status`、`/move_base/result`、`/move_base/feedback` 存在。
- RViz 中定位稳定。

### 2.3 感知节点启动

命令：

```bash
source /opt/ros/noetic/setup.bash
source /ssd1/workspace/sailors_onboard/build/devel/setup.bash
rosparam load /ssd1/workspace/sailors_onboard/calibration.yaml
export SAW_CONFIG_DIR=/ssd1/workspace/sailors_onboard/ros1_ws/sailors/onboard
export SAW_DATA_DIR=/ssd1/workspace/sailors_onboard/ros1_ws/sailors/onboard
rosrun perception sensing_node
```

真实代码依据：

- `perception/sensing/sensing_main.cpp`
- `perception/sensing/sensing_node.cpp`
- `perception/sensing/camera/camera_object_detection_nodelet.cpp`
- `perception/sensing/common/publish_channel.hpp`

主要行为：

- 订阅相机、深度、位姿、雷达障碍物相关 channel。
- 运行相机目标检测。
- 计算目标全局 `geometry_msgs/Pose`。
- 发布 track pose 到 `saw_comm::topic::kTrackPose`。
- 发布检测对象、2D bbox、障碍物、检测图像等 topic。

待确认项：

- `saw_comm::topic::kTrackPose` 在现场实际展开后的 ROS topic 名称。代码日志会打印：

```text
We publish track pose to: <topic>
```

- `saw_comm::topic::kCameraObjectList`、`kCameraObject2dList`、`kDetectImg` 的实际 topic 名称。
- 大车端最终要监听 `track_pose` 还是检测对象列表作为“人员检测触发事件”。

## 3. Demo 主线接口确认

### 3.1 大车固定点巡逻

当前状态：部分具备。

可复用接口：

- Adapter：`scout_navigation_manager`
- 底层：ROS1 `move_base`
- 点位：`navigation_position.yaml`

建议封装 skill：

- `patrol_fixed_points`

输入建议：

| 参数 | 类型 | 说明 |
|---|---|---|
| `patrol_points` | list[string] | 巡逻点名称，例如 `巡逻点2, 巡逻点3, 巡逻点4, 工位2` |
| `loop` | bool | 是否循环巡逻 |
| `stop_on_detection` | bool | 检测到人员后是否停止巡逻 |

输出建议：

| 字段 | 说明 |
|---|---|
| `patrol_status` | `idle / moving / arrived / finished / error` |
| `current_waypoint` | 当前目标点 |
| `last_navigation_status` | 来自 `scout_navigation_manager/navigation_status` |

成功判断：

- 能按顺序调用 `scout_navigation_manager`。
- 到达一个点后再下发下一个点。
- 不在 `moving to xxx` 时并发发送新目标。

缺失能力：

- 当前没有巡逻队列、循环、到点等待、检测触发停止逻辑。

### 3.2 持续人员检测

当前状态：Sailors 有真实能力，Adapter 未封装。

真实候选链路 A：Sailors `perception sensing_node`

- 启动：`sh/quick_start/3sensing_node.bash`
- 输出：`saw_comm::topic::kTrackPose`、`kCameraObjectList`、`kCameraObject2dList`
- 数据类型：
  - `TrackPosePublishChannelDataType = geometry_msgs::Pose`
  - `CameraDetectPublishChannelDataType = saw::SensorObjects`
  - `Camera2dDetectPublishChannelDataType = saw::CameraObjectBox2dList`

真实候选链路 B：`toy_utils/perception_toy`

- 检测脚本：`camera_object_detection_main.py`
- 输入：`/camera/color/image_raw`
- 输出：`DetectMsg`
- 消息类型：`msgs/TargetArray`
- 默认过滤：`filter_classes=[1]`，注释说明 `person : 1`

`msgs/TargetArray`：

```text
msgs/Target[] data
time timestamp
```

`msgs/Target`：

```text
string frame_id
time stamp
int32 imgh
int32 imgw
float32 scores
float32 centerx
float32 centery
float32 ptx
float32 pty
float32 distw
float32 disth
```

建议封装 skill：

- `start_person_detection`
- `check_person_detected`

输入建议：

| 参数 | 类型 | 说明 |
|---|---|---|
| `source_topic` | string | 首选现场确认后的检测 topic |
| `target_class` | string/int | 当前固定为 person |
| `confidence_threshold` | float | 默认可先取 0.5 |
| `cooldown_seconds` | float | 防止重复触发 |

输出建议：

| 字段 | 说明 |
|---|---|
| `person_detected` | 是否检测到人员 |
| `confidence` | 置信度 |
| `bbox` | 2D bbox |
| `target_pose` | 如果使用 sensing_node，则可输出全局 pose |
| `timestamp` | 检测时间 |

待确认项：

- Demo 采用 `sensing_node` 的全局 `track_pose`，还是 `toy_utils` 的 `/DetectMsg`。
- 如果使用 `/DetectMsg`，还需要确认如何从 2D bbox 转换为小车可执行目标位置。
- 如果使用 `sensing_node` 的 `track_pose`，需要确认 topic 名称和坐标系。

### 3.3 检测触发与协同指令发送

当前状态：Sailors 有 DDS 桥接参考，Adapter 未封装。

真实代码来源：

- `saw_dds/src/TrackConverterROSSub.cpp`
- `saw_dds/dds_idl/PoseMsg.idl`
- `saw_dds/CMakeLists.txt`

启动命令：

```bash
source /opt/ros/noetic/setup.bash
source /ssd1/workspace/sailors_onboard/build/devel/setup.bash
rosrun saw_dds track_converter_sub
```

ROS 输入：

| 接口 | 类型 | 方向 |
|---|---|---|
| `/track_pose` | `geometry_msgs/Pose` | ROS -> DDS 输入 |

DDS 输出：

| Topic | Type |
|---|---|
| `PoseMsgTopic` | `PoseMsg` |

`PoseMsg.idl`：

```text
struct PoseMsg
{
    unsigned long index;
    sequence<double> position;
    sequence<double> orientation;
};
```

建议封装 skill：

- `publish_tracking_command`

输入建议：

| 参数 | 类型 | 说明 |
|---|---|---|
| `target_pose` | geometry pose/json | 人员目标或接近点 |
| `source_event_id` | string | 检测事件 ID |
| `publish_once` | bool | 当前 Demo 建议只发一次，避免重复触发 |

输出建议：

| 字段 | 说明 |
|---|---|
| `dispatch_success` | 是否成功发布 |
| `ros_topic` | `/track_pose` |
| `dds_topic` | `PoseMsgTopic` |
| `message_id` | 本次事件 ID |

成功判断：

- `/track_pose` 有 `geometry_msgs/Pose` 消息。
- `track_converter_sub` 日志出现 DDS publisher matched 或发送日志。
- 小车侧 DDS subscriber 能收到 `PoseMsgTopic`。

待确认项：

- 大车 `sensing_node` 是否已经直接发布到 `/track_pose`，如果是，adapter 是否只负责监听并限流转发。
- `track_converter_sub` 当前只有 matched 后才发送，需要现场确认 DDS 对端先启动。
- `orientation.z` 在 `camera_object_detection_nodelet.cpp` 中被写成角度值，`orientation.w=1.0`，不是标准四元数。小车侧是否按角度解释该字段需要确认。

### 3.4 小车接收协同指令

当前状态：Sailors 有 DDS -> ROS 桥接参考，Adapter 未封装。

真实代码来源：

- `saw_dds/src/TrackConverterROSPub.cpp`

DDS 输入：

| Topic | Type |
|---|---|
| `PoseMsgTopic` | `PoseMsg` |

ROS 输出：

| 接口 | 类型 | 方向 |
|---|---|---|
| `track_pose` | `geometry_msgs/Pose` | DDS -> ROS 输出 |

注意：

- 代码中 `nh.advertise<geometry_msgs::Pose>("track_pose", 10)` 使用相对 topic 名，通常会解析为 `/track_pose`，但仍建议现场用 `rostopic list` 确认。

建议封装 skill：

- `receive_tracking_command`

输入建议：

| 参数 | 类型 | 说明 |
|---|---|---|
| `timeout_seconds` | float | 等待 DDS 指令超时时间 |
| `expected_topic` | string | 默认 `/track_pose` |

输出建议：

| 字段 | 说明 |
|---|---|
| `received` | 是否收到 |
| `target_pose` | 收到的目标 |
| `timestamp` | 接收时间 |

成功判断：

- 小车侧 `track_converter_pub` 或等效节点启动。
- `rostopic echo /track_pose` 可看到目标 pose。
- 后续导航或跟踪模块能消费该 pose。

待确认项：

- 小车侧实际启动的是 `track_converter_pub` 还是其他接收程序。
- 小车收到 `/track_pose` 后，是进入导航接近，还是直接启动视觉跟踪。

### 3.5 小车前往目标位置

当前状态：Adapter 已有命名地点导航；动态目标 pose 导航未封装。

可用能力：

- 命名点导航：`scout_navigation_manager`
- 目标 pose：来自 DDS -> ROS `/track_pose`

缺失能力：

- 当前 `scout_navigation_manager` 只接受 YAML 中命名 waypoint，不接受任意 `geometry_msgs/Pose`。
- 如果小车需要根据人员位置前往目标点，需要新增一个“pose goal”适配接口，或确认 Sailors 原系统已有对应接口。

建议下一步确认：

- 小车侧是否可以直接向 `/move_base_simple/goal` 或 `/move_base/goal` 下发 `track_pose` 转换后的目标。
- 是否需要限制目标点距离人员一定距离，避免直接撞向人员。

### 3.6 小车执行静态人员跟踪

当前状态：Sailors `toy_utils` 有参考链路，Adapter 未封装；现场是否启用待确认。

真实代码来源：

- `toy_utils/perception_toy/tracking/tracking_main.py`
- `toy_utils/planner_toy/track_planner/src/base_planner.cpp`
- `toy_utils/planner_toy/track_planner/launch/track_planner.launch`
- `toy_utils/planner_toy/config/paramater.yaml`

`tracking_main.py`：

- 订阅：`/DetectMsg`
- 发布：`TrackMsg`
- 类型：`msgs/TrackArray`

`msgs/TrackArray`：

```text
msgs/Track[] data
time timestamp
```

`msgs/Track`：

```text
int32 track_id
time timestamp
int32 imgh
int32 imgw
float32 distw
float32 disth
float32 centerx
float32 centery
float32 velox
float32 veloy
```

`base_planner.cpp`：

- 订阅：`/TrackMsg`
- 订阅：`/camera/depth/image_raw`
- 发布：`/cmd_vel`
- 控制策略：根据目标 bbox 位置和底部位置，用 PID 计算线速度和角速度。

成功判断：

- `/DetectMsg` 有人员目标。
- `/TrackMsg` 有 track 数据。
- `/cmd_vel` 输出跟踪速度。
- 没有目标时 `/cmd_vel` 停止。

待确认项：

- `planner_toy` 目录存在 `CATKIN_IGNORE`，现场是否已经去除或另有编译版本。
- 当前 `base_planner.cpp` 中 `_dep_result = NULL;` 会强制走无深度分支，是否为现场期望行为。
- 跟踪 planner 是否适合“大车检测到静态人员后，小车到达附近再跟踪”的 Demo 阶段。

## 4. 推荐封装顺序

按真实接口风险和 Demo 主线优先级，建议如下：

1. `patrol_fixed_points`
   - 复用已验证 `scout_navigation_manager`。
   - 先实现顺序点位导航，不涉及感知。

2. `check_person_detected`
   - 先只读现有 topic。
   - 不重写检测模型。
   - 优先现场确认 `sensing_node` 的 track pose topic。

3. `publish_tracking_command`
   - 复用 `/track_pose -> PoseMsgTopic` 的 DDS 桥接。
   - 加入去重和冷却策略。

4. `receive_tracking_command`
   - 在小车侧确认 `PoseMsgTopic -> /track_pose`。
   - 输出是否收到和收到的 pose。

5. `track_static_person`
   - 如果现场启用 `toy_utils` 链路，则封装启动/状态查询。
   - 如果未启用，先不要重写跟踪算法，只记录缺口。

6. `demo_orchestrator_agent`
   - 固定主线编排，不让 LLM 自由扩展流程。
   - 状态机至少包含：`idle`、`patrolling`、`detecting`、`person_detected`、`dispatching`、`waiting_ack`、`tracking`、`finished`、`error`。

## 5. 现场最小确认清单

### 5.1 已验证 adapter 能力复测

```bash
python3 agent/chat_agent.py --show-capabilities
python3 agent/scout_main_agent.py --text "去工位2" --dry-run
python3 agent/scout_main_agent.py --text "前进1秒然后停止" --dry-run
python3 skills/scout_navigation_manager/scripts/navigate.py --go "工位2"
python3 skills/scout_move_control/scripts/move_control_client.py --cmd "stop 0.5"
```

### 5.2 Sailors 感知 topic 确认

```bash
bash 3sensing_node.bash
rostopic list | grep -E "track|detect|object|camera"
rostopic echo /track_pose
```

如果没有 `/track_pose`，查看 `sensing_node` 日志中的：

```text
We publish track pose to:
```

### 5.3 DDS 桥接确认

大车侧：

```bash
bash 4dds_bridge.sh
rostopic pub /track_pose geometry_msgs/Pose ...
```

小车侧：

```bash
rosrun saw_dds track_converter_pub
rostopic echo /track_pose
```

需要确认：

- 哪一端运行 `track_converter_sub`。
- 哪一端运行 `track_converter_pub`。
- `PoseMsgTopic` 是否能跨车通信。

### 5.4 toy_utils 静态跟踪确认

```bash
roslaunch perception_toy detection_tracking.launch
roslaunch planner_toy track_planner.launch
rostopic echo /DetectMsg
rostopic echo /TrackMsg
rostopic echo /cmd_vel
```

如果 `planner_toy` 未编译，先确认是否移除 `CATKIN_IGNORE` 是现场允许动作。

## 6. 当前不应做的事

- 不重新训练人员检测模型。
- 不替换 Fast DDS。
- 不重构 `sailors_onboard-main`。
- 不把 OpenClaw 机械臂逻辑迁移进无人车 Demo。
- 不实现动态人员、多目标、多车调度。
- 不绕过现有 `/cmd_vel`、`move_base`、`sensing_node`、`saw_dds` 自造一套完整系统。

## 7. 下一步开发建议

下一步建议先封装 `patrol_fixed_points`，因为它只依赖已验证的导航 skill，风险最低，同时直接补齐 Demo 主线第一段。

同时并行做现场接口确认：

- `sensing_node` 实际发布的 track pose topic 名称；
- 大车侧 `/track_pose -> PoseMsgTopic` 是否可用；
- 小车侧 `PoseMsgTopic -> /track_pose` 是否可用；
- `toy_utils` 的 `/DetectMsg -> /TrackMsg -> /cmd_vel` 链路是否在现场构建环境中可运行。
