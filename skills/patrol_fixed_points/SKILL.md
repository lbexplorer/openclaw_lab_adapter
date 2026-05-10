---
name: patrol_fixed_points
description: "大车固定点巡逻 skill。按配置顺序复用 scout_navigation_manager 到达命名巡逻点，为 Demo 主线第一步提供稳定调度入口。"
---

# 固定点巡逻 / Patrol Fixed Points

## 能力边界

该 skill 只负责按顺序调度已有 `scout_navigation_manager`。

它不直接控制电机，不绕过 `move_base`，不重新实现路径规划。启用 `stop_on_detection` 时，它只调用现有 `check_person_detected` 读取 `/track_pose`，不启动或重写视觉检测。

## 默认路线

```text
原点 -> 巡逻点2 -> 巡逻点3 -> 巡逻点4 -> 原点
```

默认配置文件：

```text
skills/patrol_fixed_points/config/patrol_points.yaml
```

## 输入

| 参数 | 类型 | 说明 |
|---|---|---|
| `patrol_points` | string | 逗号分隔巡逻点。为空时使用默认路线 |
| `loop` | string/bool | 是否循环。当前 Demo 默认 `false` |
| `stop_on_detection` | string/bool | 是否在巡逻过程中读取人员检测结果并在检测到人员后停止巡逻 |

## 输出

返回统一 `SkillResult`，核心 `data` 字段：

| 字段 | 说明 |
|---|---|
| `patrol_status` | `idle / moving / arrived / finished / detected_person / error` |
| `current_waypoint` | 当前巡逻目标点 |
| `completed_waypoints` | 已完成巡逻点 |
| `failed_waypoint` | 失败点位 |
| `last_navigation_status` | 最近一次导航状态 |
| `person_detected` | 启用检测停止并检测到人员时为 `true` |
| `target_pose` | 检测到人员时读取到的 `/track_pose` |
| `source_topic` | 检测来源 topic |

## 调试方式

```bash
python3 skills/patrol_fixed_points/scripts/patrol.py --status
python3 skills/patrol_fixed_points/scripts/patrol.py --run
python3 skills/patrol_fixed_points/scripts/patrol.py --run --stop-on-detection true
python3 skills/patrol_fixed_points/scripts/patrol.py --run --patrol-points "原点,巡逻点2,巡逻点3,巡逻点4,原点"
```

## 成功判断

1. 所有巡逻点都能在 `navigation_position.yaml` 中解析。
2. 每次只向 `scout_navigation_manager` 下发一个目标。
3. 当前目标达到 `finish` 后才下发下一个目标。
4. 全部点位完成后返回 `success`。
5. 如果 `stop_on_detection=true`，巡逻中检测到 `/track_pose` 后取消当前导航并返回 `detected_person`。

## 失败判断

- 点位不存在：`invalid_input`
- 导航服务不可用：`unavailable`
- 单点导航失败：`failed`
- 单点等待超过 `waypoint_timeout_seconds`：`timeout`
