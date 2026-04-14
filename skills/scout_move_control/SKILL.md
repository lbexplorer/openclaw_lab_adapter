---
name: scout_move_control
description: "控制 Scout 风格底盘移动。通过话题 /scout_move_control/chassis_command 发送字符串命令，内部转换为底层速度控制接口。默认对接 ROS1 /cmd_vel。"
---

# Scout 底盘运动控制 / Scout Chassis Move Control

## 话题 / Topic

- **话题名**: `/scout_move_control/chassis_command`
- **消息类型**: `std_msgs/String`

## 服务 / Service

- **服务名**: `/scout_move_control/move_status`
- **类型**: `std_srvs/Trigger`

### 状态值

| 状态 | 含义 |
|------|------|
| `stop` | 空闲/完成 |
| `moving` | 运动中 |

## 命令格式

```text
forward 1, stop 0.5, left 1
```

## 支持动作

- `forward <t>`
- `backward <t>`
- `left <t>`
- `right <t>`
- `stop <t>`

## 调试方式

```bash
python3 skills/scout_move_control/scripts/move_control_client.py --status
python3 skills/scout_move_control/scripts/move_control_client.py --cmd "forward 1"
```

## 关键规则

1. 发送前先查状态
2. 运动中不要并发发新命令
3. 真实底层当前默认使用 ROS1 `/cmd_vel`
