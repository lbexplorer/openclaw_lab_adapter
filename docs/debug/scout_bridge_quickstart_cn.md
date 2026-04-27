# Scout 桥接快速开始

本文只保留现场调试最常用的启动和测试命令。完整排查细节见 `skills调试.md`。

默认项目目录：

```bash
cd /ssd1/workspace/openclaw_lab_adapter
source /opt/ros/noetic/setup.bash
```

## 1. 小车启动

终端 1：启动底盘、传感器和基础驱动。

```bash
cd /ssd1/workspace/openclaw_lab_adapter
source /opt/ros/noetic/setup.bash
bash 1startup.bash
```

基础检查：

```bash
rostopic list | grep -E "/scan|/imu|/odom|/cmd_vel"
```

终端 2：启动地图、定位和导航。

```bash
cd /ssd1/workspace/openclaw_lab_adapter
source /opt/ros/noetic/setup.bash
bash 2nav.bash
```

导航检查：

```bash
rosnode list | grep -E "map_server|amcl|move_base"
rostopic list | grep move_base
```

## 2. 桥接启动

终端 3：启动命名地点导航 skill。

```bash
cd /ssd1/workspace/openclaw_lab_adapter
source /opt/ros/noetic/setup.bash
python3 skills/scout_navigation_manager/scripts/navigation_manager_server.py \
  --waypoints skills/scout_navigation_manager/config/navigation_position.yaml
```

终端 4：启动底盘动作 skill。

```bash
cd /ssd1/workspace/openclaw_lab_adapter
source /opt/ros/noetic/setup.bash
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
python3 skills/scout_navigation_manager/scripts/navigate.py --go "巡逻点二"
python3 skills/scout_navigation_manager/scripts/navigate.py --go "工位2"
python3 skills/scout_navigation_manager/scripts/navigate.py --go "去火星基地"
```

ROS service 测试：

```bash
rosservice call /scout_navigation_manager/set_pose "data: '原点'"
rosservice call /scout_navigation_manager/set_pose "data: '工位2'"
rosservice call /scout_navigation_manager/navigation_status
```

底盘动作测试：

```bash
python3 skills/scout_move_control/scripts/move_control_client.py --cmd "forward 1"
python3 skills/scout_move_control/scripts/move_control_client.py --cmd "left 1"
python3 skills/scout_move_control/scripts/move_control_client.py --cmd "stop 0.5"
python3 skills/scout_move_control/scripts/move_control_client.py --cmd "forward 1, stop 0.5, left 1"
```

## 4. LLM 调度

先配置模型密钥，可放在项目根目录 `.env`：

```bash
OPENCLAW_LLM_API_KEY=your_key
OPENCLAW_LLM_BASE_URL=https://api.moonshot.cn/v1
OPENCLAW_LLM_MODEL=kimi-k2.5
```

查看 agent 能力：

```bash
python3 agent/chat_agent.py --show-capabilities
python3 agent/scout_main_agent.py --list-skills
```

dry-run 调度测试，不控制小车：

```bash
python3 agent/chat_agent.py --dry-run
python3 agent/scout_main_agent.py --text "去工位2" --dry-run
python3 agent/scout_main_agent.py --text "前进1秒然后停止" --dry-run
```

真实调度测试，确认现场安全后再执行：

```bash
python3 agent/scout_main_agent.py --text "去工位2"
python3 agent/scout_main_agent.py --text "前进1秒然后停止"
```

## 5. 最小闭环

按顺序确认：

```bash
bash 1startup.bash
bash 2nav.bash
python3 skills/scout_navigation_manager/scripts/navigation_manager_server.py --waypoints skills/scout_navigation_manager/config/navigation_position.yaml
python3 skills/scout_move_control/scripts/move_control_server.py
python3 agent/scout_main_agent.py --text "去工位2" --dry-run
python3 agent/scout_main_agent.py --text "前进1秒然后停止" --dry-run
```

如果 dry-run 正常，再去掉 `--dry-run` 做真实动作测试。
