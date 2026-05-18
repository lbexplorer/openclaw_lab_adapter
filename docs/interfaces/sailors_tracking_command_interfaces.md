# Sailors 协同指令与静态跟踪接口速查

本文记录当前已确认的 `sailors_onboard-main` 真实接口，用于后续封装以下 Demo 主线能力：

```text
检测到静态人员
-> 发送协同指令
-> 小车接收指令
-> 小车前往目标位置
-> 小车执行静态人员跟踪
```

## 1. 真实接口结论

### 1.1 协同指令发送：ROS `/track_pose` 到 DDS `PoseMsgTopic`

用途：大车侧把检测到的人员目标位姿发送给 DDS。

真实代码：

- `..\sailors_onboard-main\sailors_onboard-main\ros1_ws\sailors\onboard\saw_dds\src\TrackConverterROSSub.cpp`
- `..\sailors_onboard-main\sailors_onboard-main\ros1_ws\sailors\onboard\saw_dds\dds_idl\PoseMsg.idl`
- `..\sailors_onboard-main\sailors_onboard-main\ros1_ws\sailors\onboard\saw_dds\CMakeLists.txt`

启动入口：

```bash
source /opt/ros/noetic/setup.bash
source /ssd1/workspace/sailors_onboard/build/devel/setup.bash
rosrun saw_dds track_converter_sub
```

脚本入口：

```text
..\sailors_onboard-main\sailors_onboard-main\sh\quick_start\4dds_bridge.sh
```

ROS 输入：

| Topic | Type | 说明 |
|---|---|---|
| `/track_pose` | `geometry_msgs/Pose` | 大车侧人员目标位姿输入 |

DDS 输出：

| Topic | Type | 说明 |
|---|---|---|
| `PoseMsgTopic` | `PoseMsg` | 跨车发送的目标位姿 |

DDS 类型：

```text
struct PoseMsg
{
    unsigned long index;
    sequence<double> position;
    sequence<double> orientation;
};
```

成功判断：

- `track_converter_sub` 已启动。
- DDS publisher matched。
- 发布 `/track_pose` 后，代码会将 position 和 orientation 写入 `PoseMsgTopic`。

注意：

- `TrackConverterROSSub.cpp` 只有在 DDS publisher matched 且 `index == 1` 时才写 DDS。
- 因此现场应先启动小车侧 DDS subscriber，再从大车侧发布目标。

### 1.2 小车接收协同指令：DDS `PoseMsgTopic` 到 ROS `track_pose`

用途：小车侧从 DDS 接收人员目标位姿，并重新发布为 ROS pose。

真实代码：

- `..\sailors_onboard-main\sailors_onboard-main\ros1_ws\sailors\onboard\saw_dds\src\TrackConverterROSPub.cpp`

启动入口：

```bash
source /opt/ros/noetic/setup.bash
source /ssd1/workspace/sailors_onboard/build/devel/setup.bash
rosrun saw_dds track_converter_pub
```

DDS 输入：

| Topic | Type | 说明 |
|---|---|---|
| `PoseMsgTopic` | `PoseMsg` | 从大车侧收到的目标位姿 |

ROS 输出：

| Topic | Type | 说明 |
|---|---|---|
| `track_pose` | `geometry_msgs/Pose` | 小车侧收到的目标位姿 |

注意：

- 代码中使用 `nh.advertise<geometry_msgs::Pose>("track_pose", 10)`，是相对 topic 名。通常解析为 `/track_pose`，但现场应以 `rostopic list` 为准。
- 接收成功后可用 `rostopic echo /track_pose` 确认。

### 1.3 人员目标位姿来源：Sailors 感知节点

用途：大车侧感知节点生成 `geometry_msgs/Pose` 目标位姿。

真实代码：

- `..\sailors_onboard-main\sailors_onboard-main\ros1_ws\sailors\onboard\perception\sensing\sensing_node.cpp`
- `..\sailors_onboard-main\sailors_onboard-main\ros1_ws\sailors\onboard\perception\sensing\camera\camera_object_detection_nodelet.cpp`
- `..\sailors_onboard-main\sailors_onboard-main\ros1_ws\sailors\onboard\perception\sensing\common\publish_channel.hpp`

启动入口：

```bash
source /opt/ros/noetic/setup.bash
source /ssd1/workspace/sailors_onboard/build/devel/setup.bash
rosparam load /ssd1/workspace/sailors_onboard/calibration.yaml
export SAW_CONFIG_DIR=/ssd1/workspace/sailors_onboard/ros1_ws/sailors/onboard
export SAW_DATA_DIR=/ssd1/workspace/sailors_onboard/ros1_ws/sailors/onboard
rosrun perception sensing_node
```

脚本入口：

```text
..\sailors_onboard-main\sailors_onboard-main\sh\quick_start\3sensing_node.bash
```

已确认类型：

```cpp
using TrackPosePublishChannelDataType = geometry_msgs::Pose;
```

发布链路：

```text
camera_object_detection_nodelet
-> TrackPosePublishChannel
-> MessagePublication<geometry_msgs::Pose>
-> saw_comm::topic::kTrackPose
```

待现场确认：

- `saw_comm::topic::kTrackPose` 实际展开后的 ROS topic 名称。
- 现场是否已经映射为 `/track_pose`。

现场确认命令：

```bash
rostopic list | grep -E "track|pose|detect"
rostopic echo /track_pose
```

如果没有 `/track_pose`，查看 `sensing_node` 日志：

```text
We publish track pose to:
```

### 1.4 静态人员跟踪控制：`/TrackMsg` 到 `/cmd_vel`

用途：小车侧根据检测框跟踪人员，并输出底盘速度。

真实代码：

- `..\sailors_onboard-main\sailors_onboard-main\ros1_ws\sailors\onboard\toy_utils\planner_toy\track_planner\src\base_planner.cpp`
- `..\sailors_onboard-main\sailors_onboard-main\ros1_ws\sailors\onboard\toy_utils\planner_toy\track_planner\src\main.cpp`
- `..\sailors_onboard-main\sailors_onboard-main\ros1_ws\sailors\onboard\toy_utils\planner_toy\track_planner\launch\track_planner.launch`
- `..\sailors_onboard-main\sailors_onboard-main\ros1_ws\sailors\onboard\toy_utils\planner_toy\config\paramater.yaml`

启动入口：

```bash
roslaunch planner_toy track_planner.launch
```

ROS 输入：

| Topic | Type | 说明 |
|---|---|---|
| `/TrackMsg` | `msgs/TrackArray` | 跟踪目标检测框 |
| `/camera/depth/image_raw` | `sensor_msgs/Image` | 深度图，可选 |

ROS 输出：

| Topic | Type | 说明 |
|---|---|---|
| `/cmd_vel` | `geometry_msgs/Twist` | 跟踪控制速度 |

控制逻辑：

- 有 `/TrackMsg` 时，根据 bbox 位置计算线速度和角速度。
- 没有目标时发布零速度。
- PID 参数从 ROS param 读取。

关键参数：

```yaml
/pid_angular:
  p: 0.5
  i: 0.0
  d: 0.0

/pid_linear:
  p: 0.5
  i: 0.0
  d: 0.0

/scale:
  linear: 100
  angular: 400
  depth: 0.8
```

已知问题：

- `planner_toy` 目录存在 `CATKIN_IGNORE`，现场是否已编译需要确认。
- `base_planner.cpp` 消费的是 `/TrackMsg`，不是 `/track_pose`。
- 因此 DDS 收到的 `track_pose` 不能直接驱动该跟踪控制器。

### 1.5 检测框到 TrackMsg：`/DetectMsg` 到 `/TrackMsg`

用途：把相机检测框转换为跟踪检测框，供 `track_planner` 使用。

真实代码：

- `..\sailors_onboard-main\sailors_onboard-main\ros1_ws\sailors\onboard\toy_utils\perception_toy\tracking\tracking_main.py`
- `..\sailors_onboard-main\sailors_onboard-main\ros1_ws\sailors\onboard\toy_utils\perception_toy\sensing\camera\camera_object_detection\camera_object_detection_main.py`
- `..\sailors_onboard-main\sailors_onboard-main\ros1_ws\sailors\onboard\toy_utils\msgs\msg\Target.msg`
- `..\sailors_onboard-main\sailors_onboard-main\ros1_ws\sailors\onboard\toy_utils\msgs\msg\TargetArray.msg`
- `..\sailors_onboard-main\sailors_onboard-main\ros1_ws\sailors\onboard\toy_utils\msgs\msg\Track.msg`
- `..\sailors_onboard-main\sailors_onboard-main\ros1_ws\sailors\onboard\toy_utils\msgs\msg\TrackArray.msg`

启动入口：

```bash
roslaunch perception_toy detection_tracking.launch
```

检测发布：

| Topic | Type | 说明 |
|---|---|---|
| `/DetectMsg` | `msgs/TargetArray` | 相机检测框 |

跟踪发布：

| Topic | Type | 说明 |
|---|---|---|
| `TrackMsg` | `msgs/TrackArray` | 供跟踪 planner 使用 |

`camera_object_detection_main.py` 当前默认过滤：

```python
filter_classes=[1]  # person : 1
```

## 2. 关键缺口

当前真实接口存在一个断点：

```text
DDS 接收链路输出：track_pose / geometry_msgs::Pose
静态跟踪控制输入：/TrackMsg / msgs::TrackArray
```

也就是说：

- `track_converter_pub` 可以把大车检测到的人员目标位姿传到小车侧。
- `track_planner` 不能直接消费这个 pose。
- 现有静态跟踪控制器需要小车本地相机检测生成 `/DetectMsg`，再转成 `/TrackMsg`。

因此后续不能直接把 `track_pose` 当成 `track_planner` 的输入。需要先明确 Demo 策略：

1. 小车收到 `track_pose` 后先导航到目标附近，再启动本地视觉检测和 `/TrackMsg` 跟踪；
2. 或新增一个最小 adapter，把 `track_pose` 转为安全的导航目标；
3. 不建议直接把 `track_pose` 转成 `/cmd_vel`，除非先明确安全边界、限速、停止条件和避障策略。

## 3. 最小 skill 封装建议

### 3.1 `publish_tracking_command`

职责：大车侧把人员目标位姿发布到 `/track_pose`，复用 `track_converter_sub` 发送 DDS。

输入：

| 字段 | 类型 | 说明 |
|---|---|---|
| `target_pose` | object | `geometry_msgs/Pose` 风格目标位姿 |
| `event_id` | string | 检测事件 ID，可选 |
| `topic` | string | 默认 `/track_pose` |

输出：

| 字段 | 说明 |
|---|---|
| `published` | 是否发布成功 |
| `ros_topic` | 实际发布 topic |
| `dds_topic` | 固定 `PoseMsgTopic` |
| `target_pose` | 本次发布的 pose |

成功判断：

- ROS topic 发布成功。
- 可选：短时间内本地订阅回读到同一条 pose。

### 3.2 `receive_tracking_command`

职责：小车侧确认是否收到 DDS 桥转出的目标位姿。

输入：

| 字段 | 类型 | 说明 |
|---|---|---|
| `topic` | string | 默认 `/track_pose` |
| `timeout_seconds` | float | 等待超时 |

输出：

| 字段 | 说明 |
|---|---|
| `received` | 是否收到 |
| `target_pose` | 收到的目标位姿 |
| `source_topic` | 实际监听 topic |

成功判断：

- `rospy.wait_for_message(topic, geometry_msgs/Pose)` 在超时前返回。

### 3.3 `track_static_person`

职责：封装小车静态人员跟踪入口。

当前建议：

- 第一版不要直接发布 `/cmd_vel`。
- 第一版只做真实链路状态检查和启动说明封装：
  - `/DetectMsg` 是否存在；
  - `/TrackMsg` 是否存在；
  - `/cmd_vel` 是否有跟踪输出；
  - `planner_toy` 是否可运行。

原因：

- 已确认 `track_planner` 的真实输入是 `/TrackMsg`，不是 `/track_pose`。
- 直接从 `track_pose` 推速度控制会绕过已有感知跟踪链路，安全风险更高。

## 4. 后续开发顺序

建议按以下顺序推进：

1. 实现 `publish_tracking_command`，补齐“发送协同指令”。
2. 实现 `receive_tracking_command`，补齐“小车接收指令”。
3. 确认小车收到 `track_pose` 后的实际执行策略。
4. 若采用导航接近，新增 pose goal 导航适配。
5. 若采用本地视觉静态跟踪，封装 `track_static_person` 为 `/DetectMsg -> /TrackMsg -> /cmd_vel` 的状态检查和控制入口。

## 5. 现场验证清单

大车侧：

```bash
source /opt/ros/noetic/setup.bash
source /ssd1/workspace/sailors_onboard/build/devel/setup.bash
rosrun perception sensing_node
rosrun saw_dds track_converter_sub
rostopic echo /track_pose
```

小车侧：

```bash
source /opt/ros/noetic/setup.bash
source /ssd1/workspace/sailors_onboard/build/devel/setup.bash
rosrun saw_dds track_converter_pub
rostopic echo /track_pose
```

静态跟踪链路：

```bash
roslaunch perception_toy detection_tracking.launch
roslaunch planner_toy track_planner.launch
rostopic echo /DetectMsg
rostopic echo /TrackMsg
rostopic echo /cmd_vel
```

必须确认：

- `PoseMsgTopic` 是否能跨车通信。
- 小车侧 `track_pose` 是否实际为 `/track_pose`。
- `planner_toy` 是否已经在现场构建环境中可运行。
- 小车前往目标位置是使用导航目标，还是到位后再启动本地视觉跟踪。
