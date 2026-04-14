# Scout 桥接快速开始

## 1. 启动底层环境

在 `sailors_onboard-main` 的 ROS1 环境中启动：

```bash
roslaunch scout_launch startup.launch
roslaunch scout_launch nav.launch
```

## 2. 编译自定义服务

将 `ros1_bridge/scout_openclaw_msgs` 放入你的 catkin 工作空间 `src/` 下：

```bash
catkin_make
source devel/setup.bash
```

如果暂时不编译 `SetString.srv`，导航适配层仍可通过 `std_msgs/String` 话题后备运行。

## 3. 启动桥接服务

```bash
python3 skills/scout_move_control/scripts/move_control_server.py

python3 skills/scout_navigation_manager/scripts/navigation_manager_server.py \
  --waypoints skills/scout_navigation_manager/config/navigation_position.yaml
```

## 4. 调试客户端

```bash
python3 skills/scout_move_control/scripts/move_control_client.py --cmd "forward 1, stop 0.5, left 1"

python3 skills/scout_navigation_manager/scripts/navigate.py --list
python3 skills/scout_navigation_manager/scripts/navigate.py --go 原点
```

## 5. 接入 OpenClaw

将 `skills/` 下的技能目录部署到 OpenClaw 的 workspace 中，然后由主智能体按 skill 文档中的接口调用。

## 当前已知限制

- 只做了移动和导航
- waypoint 只内置了基础点位
- 真实 Mission 发布、日志聚合、硬件异常恢复还没接入
