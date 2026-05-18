# Scout Navigation and LLM Skills Startup Guide

---

## **Before starting, confirm the robot area is clear. Direct chassis commands can publish `/cmd_vel` and move the vehicle.**

---

# 1 Prerequisites

Before using adapter skills, the Scout base must already be running.

Required on the robot side:

- `1startup.sh` has been started.
- `2nav.bash` has been started.
- ROS Noetic environment is available.
- Sailors onboard workspace is available.
- `move_base` is running normally.
- `/cmd_vel`, `/odom`, `/scan` and navigation topics are visible.

Quick check:

```bash
rostopic list | grep -E "/scan|/odom|/cmd_vel"
rosnode list | grep -E "map_server|amcl|move_base"
```

---

# 2 Start Adapter Skills

## Method 1: One-click Startup (Recommended)

```bash
sudo apt install terminator -y   # First time only
cd /ssd1/workspace_lb/openclaw_lab_adapter
bash scripts/launch_skills_terminator.sh
```

Automatically opens 2 Terminator windows:

| Tab | Name | Command | Purpose |
|-----|------|---------|---------|
| 1 | navigation skill | `navigation_manager_server.py` | named waypoint navigation adapter |
| 2 | move skill | `move_control_server.py` | chassis movement adapter |

This script only starts adapter skill services. It does not start `1startup.sh` or `2nav.bash`.

## Method 2: Manual Startup

### Tab 1: Navigation Skill

```bash
cd /ssd1/workspace/openclaw_lab_adapter
source /opt/ros/noetic/setup.bash
source /ssd1/workspace/sailors_onboard/build/devel/setup.bash
python3 skills/scout_navigation_manager/scripts/navigation_manager_server.py \
  --waypoints skills/scout_navigation_manager/config/navigation_position.yaml
```

### Tab 2: Move Skill

```bash
cd /ssd1/workspace/openclaw_lab_adapter
source /opt/ros/noetic/setup.bash
source /ssd1/workspace/sailors_onboard/build/devel/setup.bash
python3 skills/scout_move_control/scripts/move_control_server.py
```

## Skills Verification

```bash
rosservice call /scout_navigation_manager/list_positions
rosservice call /scout_navigation_manager/navigation_status
python3 skills/scout_move_control/scripts/move_control_client.py --status
```

---

# 3 Start LLM Agent

## Method 1: One-click Startup (Recommended)

```bash
cd /ssd1/workspace/openclaw_lab_adapter
bash scripts/launch_agent_terminator.sh
```

This opens `agent/chat_agent.py` in a Terminator window.

## Method 2: Manual Startup

```bash
cd /ssd1/workspace/openclaw_lab_adapter
source /opt/ros/noetic/setup.bash
source /ssd1/workspace/sailors_onboard/build/devel/setup.bash
python3 agent/chat_agent.py
```

LLM environment variables can be placed in `.env`:

```bash
OPENCLAW_LLM_API_KEY=your_key
OPENCLAW_LLM_BASE_URL=https://api.moonshot.cn/v1
OPENCLAW_LLM_MODEL=kimi-k2.5
```

## Dry-run Test

```bash
python3 agent/scout_main_agent.py --text "去原点" --dry-run
python3 agent/scout_main_agent.py --text "前进1秒然后停止" --dry-run
python3 agent/scout_main_agent.py --text "开始巡逻" --dry-run
```

---

# 4 Real Movement Test

Only run after the robot area is clear.

```bash
python3 agent/scout_main_agent.py --text "去巡逻点3"
python3 agent/scout_main_agent.py --text "前进1秒然后停止"
```
