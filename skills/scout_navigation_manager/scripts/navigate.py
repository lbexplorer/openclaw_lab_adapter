#!/usr/bin/env python3
"""Client helper for Scout named-waypoint navigation."""

import argparse
import os
import re
import sys
import time

import yaml

try:
    import rospy
    from std_msgs.msg import String
    from std_srvs.srv import Trigger
except ImportError:  # pragma: no cover
    rospy = None
    String = None
    Trigger = None

try:  # pragma: no cover
    from scout_openclaw_msgs.srv import SetString
except ImportError:  # pragma: no cover
    SetString = None


def ensure_ros():
    if rospy is None:
        raise RuntimeError("ROS1 Python dependencies not available. Please source your ROS1 environment first.")


def default_waypoint_path():
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "navigation_position.yaml")


def normalize_text(text):
    return re.sub(r"\s+", "", (text or "")).strip().lower()


def load_waypoint_names(path):
    with open(path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    positions = raw.get("navigation_positions") or raw.get("destinations") or {}
    return sorted(positions.keys())


def resolve_waypoint_name(path, user_text):
    with open(path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    positions = raw.get("navigation_positions") or raw.get("destinations") or {}
    normalized_input = normalize_text(user_text)
    if not normalized_input:
        return None

    alias_to_name = {}
    for name, pose in positions.items():
        aliases = []
        if isinstance(pose, dict):
            aliases = pose.get("aliases", []) or []
        if isinstance(aliases, str):
            aliases = [aliases]

        for candidate in [name] + list(aliases):
            normalized_candidate = normalize_text(candidate)
            if normalized_candidate:
                alias_to_name[normalized_candidate] = name

    exact_match = alias_to_name.get(normalized_input)
    if exact_match is not None:
        return exact_match

    for alias, canonical_name in sorted(alias_to_name.items(), key=lambda item: len(item[0]), reverse=True):
        if alias and alias in normalized_input:
            return canonical_name
    return None


def get_status():
    rospy.wait_for_service("/scout_navigation_manager/navigation_status", timeout=5.0)
    client = rospy.ServiceProxy("/scout_navigation_manager/navigation_status", Trigger)
    return client().message


def list_positions():
    rospy.wait_for_service("/scout_navigation_manager/list_positions", timeout=5.0)
    client = rospy.ServiceProxy("/scout_navigation_manager/list_positions", Trigger)
    return client().message


def set_pose(name):
    if SetString is not None:
        rospy.wait_for_service("/scout_navigation_manager/set_pose", timeout=5.0)
        client = rospy.ServiceProxy("/scout_navigation_manager/set_pose", SetString)
        response = client(data=name)
        return response.success, response.message

    publisher = rospy.Publisher("/scout_navigation_manager/set_pose", String, queue_size=1)
    deadline = time.time() + 2.0
    while publisher.get_num_connections() == 0 and time.time() < deadline and not rospy.is_shutdown():
        time.sleep(0.05)
    publisher.publish(String(data=name))
    return True, "published via topic fallback"


def wait_for_dispatched(timeout=3.0):
    """等待服务端发布目标坐标信息到 /scout_navigation_manager/goal_dispatched。

    Args:
        timeout (float): 等待超时秒数，默认3秒。

    Returns:
        str or None: 坐标信息字符串，超时则返回None。
    """
    try:
        msg = rospy.wait_for_message(
            "/scout_navigation_manager/goal_dispatched", String, timeout=timeout
        )
        return msg.data
    except rospy.ROSException:
        return None


def main():
    parser = argparse.ArgumentParser(description="Scout navigation manager client")
    parser.add_argument("--status", action="store_true", help="Query navigation status")
    parser.add_argument("--list", action="store_true", help="List positions")
    parser.add_argument("--go", type=str, help='Send target name, e.g. --go "原点"')
    parser.add_argument("--waypoints", default=default_waypoint_path(), help="Waypoint YAML path")
    args = parser.parse_args()

    ensure_ros()
    rospy.init_node("scout_navigation_manager_client", anonymous=True)

    if args.status:
        print(get_status())
        return
    if args.list:
        print(list_positions())
        return
    if args.go:
        names = load_waypoint_names(args.waypoints)
        resolved_name = resolve_waypoint_name(args.waypoints, args.go)
        if resolved_name is None:
            print("unknown waypoint: %s" % args.go)
            print("available: %s" % ",".join(names))
            sys.exit(2)
        success, message = set_pose(args.go)
        dispatched = wait_for_dispatched(timeout=3.0)
        if dispatched:
            print("坐标: %s" % dispatched)
        print("success=%s resolved=%s message=%s" % (success, resolved_name, message))
        return

    parser.print_help(sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
