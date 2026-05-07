---
name: scout_navigation_manager
description: "Scout 风格命名地点导航 skill。通过 1201 地图基准下的 waypoint/aliases 配置驱动底层导航系统，默认对接 ROS1 move_base。"
---

# Scout 导航管理器 / Scout Navigation Manager

## 服务

- `/scout_navigation_manager/navigation_status`
- `/scout_navigation_manager/list_positions`
- `/scout_navigation_manager/get_navigation_mode`
- `/scout_navigation_manager/set_pose`
- `/scout_navigation_manager/goal_dispatched` — 目标派发坐标 Topic（String，latched）

## 话题

| Topic | 类型 | 方向 | 说明 |
|-------|------|------|------|
| `/scout_navigation_manager/goal_dispatched` | `std_msgs/String` | 服务端发布 | 导航目标派发时发布坐标，格式包含地点名、position 和 orientation |

## 状态

| 状态 | 含义 |
|------|------|
| `ready` | 空闲，可接收目标 |
| `moving to xxx` | 正在导航 |
| `finish` | 已到达 |

## 默认导航模式

`named_waypoints`

## 地点映射

- 地点配置文件: `skills/scout_navigation_manager/config/navigation_position.yaml`
- 默认基准地图: `sailors_onboard-main` 中的 `scout_launch/maps/1201.yaml`
- 支持字段:
  - `x / y`: `map` 坐标系目标位置
  - `orientation.x / orientation.y / orientation.z / orientation.w`: `map` 坐标系目标朝向四元数
  - `description`: 地点说明
  - `aliases`: 自然语言别名，例如“去前台”“带我去仓库”

服务端会自动将自然语言短句归一化到标准地点名，再下发给 `move_base`。

## 调试方式

```bash
python3 skills/scout_navigation_manager/scripts/navigate.py --list
python3 skills/scout_navigation_manager/scripts/navigate.py --go 原点
python3 skills/scout_navigation_manager/scripts/navigate.py --go "带我去前台"
```

## 关键规则

1. 发目标前先查状态
2. 发目标前先确认地点名存在
3. 导航进行中不要并发发新目标
4. 当前默认依赖 ROS1 `move_base`
5. 如果要绑定新地点，优先只改 YAML，不改 Python 代码
