#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROS_SETUP="/opt/ros/noetic/setup.bash"
SAILORS_SETUP="${SAILORS_SETUP:-/ssd1/workspace/sailors_onboard/build/devel/setup.bash}"

if ! command -v terminator >/dev/null 2>&1; then
  echo "ERROR: terminator is not installed or not in PATH." >&2
  echo "Install terminator, or start the two adapter services manually from docs/debug/scout_bridge_quickstart_cn.md." >&2
  exit 1
fi

if [[ ! -f "${ROS_SETUP}" ]]; then
  echo "ERROR: ${ROS_SETUP} not found." >&2
  echo "This script must run on the robot Linux/ROS Noetic environment." >&2
  exit 1
fi

if [[ ! -f "${SAILORS_SETUP}" ]]; then
  echo "ERROR: ${SAILORS_SETUP} not found." >&2
  echo "Set SAILORS_SETUP to the real sailors_onboard devel setup path, or build/source the Sailors workspace first." >&2
  exit 1
fi

run_window() {
  local title="$1"
  local command="$2"

  terminator -T "${title}" -x bash -lc "
set -e
cd '${ROOT_DIR}'
source /opt/ros/noetic/setup.bash
source '${SAILORS_SETUP}'
echo '[${title}] repo: ${ROOT_DIR}'
echo '[${title}] sourced: ${ROS_SETUP}'
echo '[${title}] sourced: ${SAILORS_SETUP}'
echo '[${title}] command: ${command}'
set +e
${command}
status=\$?
set -e
echo
echo '[${title}] exited with status '\${status}
exec bash
" &
}

run_window \
  "openclaw navigation skill" \
  "python3 skills/scout_navigation_manager/scripts/navigation_manager_server.py --waypoints skills/scout_navigation_manager/config/navigation_position.yaml"

run_window \
  "openclaw move skill" \
  "python3 skills/scout_move_control/scripts/move_control_server.py"

echo "Started adapter skill windows with terminator."
echo "This script does not start 1startup.bash or 2nav.bash; confirm base robot services separately."
