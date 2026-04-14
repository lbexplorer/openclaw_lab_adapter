#!/usr/bin/env python3
"""Client helper for the Scout move control adapter."""

import argparse
import sys
import time

try:
    import rospy
    from std_msgs.msg import String
    from std_srvs.srv import Trigger
except ImportError:  # pragma: no cover
    rospy = None
    String = None
    Trigger = None


def ensure_ros():
    if rospy is None:
        raise RuntimeError("ROS1 Python dependencies not available. Please source your ROS1 environment first.")


def query_status():
    rospy.wait_for_service("/scout_move_control/move_status", timeout=5.0)
    client = rospy.ServiceProxy("/scout_move_control/move_status", Trigger)
    return client().message


def send_command(command):
    publisher = rospy.Publisher("/scout_move_control/chassis_command", String, queue_size=1)
    deadline = time.time() + 2.0
    while publisher.get_num_connections() == 0 and time.time() < deadline and not rospy.is_shutdown():
        time.sleep(0.05)
    publisher.publish(String(data=command))


def main():
    parser = argparse.ArgumentParser(description="Scout move control client")
    parser.add_argument("--status", action="store_true", help="Query move status")
    parser.add_argument("--cmd", type=str, help='Command string, e.g. "forward 1, left 1"')
    args = parser.parse_args()

    ensure_ros()
    rospy.init_node("scout_move_control_client", anonymous=True)

    if args.status:
        print(query_status())
        return
    if args.cmd:
        send_command(args.cmd)
        print("sent: %s" % args.cmd)
        return

    parser.print_help(sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
