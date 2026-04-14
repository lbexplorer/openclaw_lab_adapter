#!/usr/bin/env python3
"""Client helper for Scout named-waypoint navigation."""

import argparse
import os
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


def load_waypoint_names(path):
    with open(path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return sorted((raw.get("navigation_positions") or {}).keys())


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
        if args.go not in names:
            print("unknown waypoint: %s" % args.go)
            print("available: %s" % ",".join(names))
            sys.exit(2)
        success, message = set_pose(args.go)
        print("success=%s message=%s" % (success, message))
        return

    parser.print_help(sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
