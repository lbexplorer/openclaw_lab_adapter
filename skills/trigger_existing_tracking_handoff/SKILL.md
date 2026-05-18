---
name: trigger_existing_tracking_handoff
description: "大车侧现有协同交接 skill。读取已有 /track_pose，确认人员目标已进入现有大车到小车协同链路。"
---

# Trigger Existing Tracking Handoff

## 能力边界

该 skill 只封装现有大车侧协同链路的可观测状态：

```text
sensing_node 已输出 /track_pose
-> 现有 bridge / 小车协同系统接入
-> 小车按现场既有流程响应
```

它不主动发布 `/track_pose`，不启动 DDS 或 ros1_bridge，不远程控制小车，不直接发布 `/cmd_vel`。

## 输入

| 参数 | 类型 | 说明 |
|---|---|---|
| `topic` | string | 默认 `/track_pose` |
| `timeout_seconds` | float | 等待一条目标 pose 的超时时间 |
| `require_subscriber` | bool/string | 是否要求 topic 上已有 subscriber |

## 输出

返回统一 `SkillResult`，核心 `data` 字段：

| 字段 | 说明 |
|---|---|
| `handoff_triggered` | 是否确认目标已进入现有协同交接链路 |
| `target_pose` | 从 `/track_pose` 读取到的人员目标 pose |
| `source_topic` | 实际读取 topic |
| `bridge_subscriber_seen` | 是否观察到 topic subscriber |
| `ros_publishers` | ROS master 中该 topic 的 publisher 列表 |
| `ros_subscribers` | ROS master 中该 topic 的 subscriber 列表 |
| `handoff_mode` | 固定为 `existing_vehicle_pipeline` |
| `dds_topic` | 已确认 DDS 目标 topic，默认 `PoseMsgTopic` |

## 命令

```bash
python3 skills/trigger_existing_tracking_handoff/scripts/trigger_handoff.py --check
python3 skills/trigger_existing_tracking_handoff/scripts/trigger_handoff.py --status
python3 skills/trigger_existing_tracking_handoff/scripts/trigger_handoff.py --check --require-subscriber true
```

## 成功判断

- `--check` 在超时前读取到 `geometry_msgs/Pose`。
- 如果 `require_subscriber=true`，还需要 ROS master 中该 topic 有 subscriber。
- 成功只代表“大车侧目标已交给现有协同链路”，不强制确认小车已收到或已经开始跟踪。
