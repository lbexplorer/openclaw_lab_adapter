#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROS_SETUP="/opt/ros/noetic/setup.bash"
SAILORS_SETUP="${SAILORS_SETUP:-/ssd1/workspace/sailors_onboard/build/devel/setup.bash}"

if ! command -v terminator >/dev/null 2>&1; then
  echo "ERROR: terminator is not installed or not in PATH." >&2
  echo "Install terminator, or start the agent manually with: python3 agent/chat_agent.py" >&2
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

terminator -T "openclaw chat agent" -x bash -lc "
set -e
cd '${ROOT_DIR}'
source /opt/ros/noetic/setup.bash
source '${SAILORS_SETUP}'
if [[ -f .env ]]; then
  set -a
  source .env
  set +a
  echo '[openclaw chat agent] loaded .env'
fi
echo '[openclaw chat agent] repo: ${ROOT_DIR}'
echo '[openclaw chat agent] sourced: ${ROS_SETUP}'
echo '[openclaw chat agent] sourced: ${SAILORS_SETUP}'
echo '[openclaw chat agent] command: python3 agent/chat_agent.py'
set +e
python3 agent/chat_agent.py
status=\$?
set -e
echo
echo '[openclaw chat agent] exited with status '\${status}
exec bash
" &

echo "Started chat agent window with terminator."
