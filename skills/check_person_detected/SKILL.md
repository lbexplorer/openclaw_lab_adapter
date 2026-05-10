# check_person_detected

## 能力边界

`check_person_detected` 是人员检测结果读取 skill，只订阅已有 ROS topic，不启动视觉模型，不重新实现检测算法。

当前优先读取 Sailors `sensing_node` 输出的 `/track_pose`。如果现场使用 `toy_utils` 静态检测链路，也可以读取 `/DetectMsg`。

## 输入

| 参数 | 类型 | 说明 |
|---|---|---|
| `source` | string | `track_pose`、`detect_msg` 或 `auto`，默认 `track_pose` |
| `topic` | string | 覆盖默认 topic |
| `timeout_seconds` | float | 等待单次消息的超时时间 |
| `max_age_seconds` | float | 消息允许的最大年龄，当前用于结果记录 |
| `confidence_threshold` | float | `/DetectMsg` 置信度阈值 |

## 输出

返回统一 `SkillResult`：

| 字段 | 说明 |
|---|---|
| `data.person_detected` | 是否检测到人员 |
| `data.source` | 实际读取的数据源 |
| `data.source_topic` | 实际订阅 topic |
| `data.target_pose` | 使用 `/track_pose` 时返回目标 pose |
| `data.detections` | 使用 `/DetectMsg` 时返回符合阈值的检测框 |
| `data.message_age_seconds` | 消息年龄，能取到 header/stamp 时记录 |

## 命令

```bash
python3 skills/check_person_detected/scripts/check_person_detected.py --check
python3 skills/check_person_detected/scripts/check_person_detected.py --check --source detect_msg
python3 skills/check_person_detected/scripts/check_person_detected.py --status
```

## 成功判断

- `/track_pose` 收到 `geometry_msgs/Pose` 时，表示已有可用于协同下发的人员目标位姿。
- `/DetectMsg` 收到 `msgs/TargetArray` 时，存在满足 `confidence_threshold` 的 person 目标表示检测到人员。
- 没有人员但检测 topic 正常返回空数组时，返回 `success` 且 `person_detected=false`。
- 等待超时或 ROS 依赖不可用时，返回 `timeout` 或 `unavailable`。
