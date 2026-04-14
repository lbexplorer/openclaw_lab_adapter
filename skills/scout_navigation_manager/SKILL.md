---
name: scout_navigation_manager
description: "Scout 风格命名地点导航 skill。通过 waypoint 配置驱动底层导航系统，默认对接 ROS1 move_base。"
---

# Scout 导航管理器 / Scout Navigation Manager

## 服务

- `/scout_navigation_manager/navigation_status`
- `/scout_navigation_manager/list_positions`
- `/scout_navigation_manager/get_navigation_mode`
- `/scout_navigation_manager/set_pose`

## 状态

| 状态 | 含义 |
|------|------|
| `ready` | 空闲，可接收目标 |
| `moving to xxx` | 正在导航 |
| `finish` | 已到达 |

## 默认导航模式

`named_waypoints`

## 调试方式

```bash
python3 skills/scout_navigation_manager/scripts/navigate.py --list
python3 skills/scout_navigation_manager/scripts/navigate.py --go 原点
```

## 关键规则

1. 发目标前先查状态
2. 发目标前先确认地点名存在
3. 导航进行中不要并发发新目标
4. 当前默认依赖 ROS1 `move_base`
