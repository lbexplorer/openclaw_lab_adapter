#!/usr/bin/env python3
"""ROS1 adapter that exposes OpenClaw-style move control for Scout-like platforms."""

import math
import threading
import time

try:
    import rospy
    from geometry_msgs.msg import Twist
    from std_msgs.msg import String
    from std_srvs.srv import Trigger, TriggerResponse
except ImportError:  # pragma: no cover
    rospy = None
    Twist = None
    String = None
    Trigger = None
    TriggerResponse = None


DEFAULT_LINEAR = 0.20
DEFAULT_ANGULAR = 0.60
DEFAULT_MOVE_DURATION = 2.0
DEFAULT_STOP_DURATION = 0.5
DEFAULT_GAP_DURATION = 0.5
PUBLISH_HZ = 20.0


def parse_command_sequence(command):
    if not command or not command.strip():
        raise ValueError("empty command")

    actions = []
    for part in command.replace("，", ",").split(","):
        item = part.strip()
        if not item:
            continue
        pieces = item.split()
        direction = pieces[0].lower()
        if direction not in {"forward", "backward", "left", "right", "stop"}:
            raise ValueError("unknown direction: %s" % direction)
        if len(pieces) > 2:
            raise ValueError("invalid action syntax: %s" % item)
        if len(pieces) == 2:
            duration = float(pieces[1])
        elif direction == "stop":
            duration = DEFAULT_STOP_DURATION
        else:
            duration = DEFAULT_MOVE_DURATION
        if duration < 0.0 or not math.isfinite(duration):
            raise ValueError("invalid duration for %s" % direction)
        actions.append((direction, duration))

    if not actions:
        raise ValueError("no valid actions")
    return actions


def build_twist(direction):
    twist = Twist()
    if direction == "forward":
        twist.linear.x = DEFAULT_LINEAR
    elif direction == "backward":
        twist.linear.x = -DEFAULT_LINEAR
    elif direction == "left":
        twist.angular.z = DEFAULT_ANGULAR
    elif direction == "right":
        twist.angular.z = -DEFAULT_ANGULAR
    return twist


class ScoutMoveControlServer(object):
    def __init__(self):
        self._lock = threading.Lock()
        self._move_status = "stop"
        self._cmd_pub = rospy.Publisher("/cmd_vel", Twist, queue_size=10)
        self._command_sub = rospy.Subscriber(
            "/scout_move_control/chassis_command", String, self._command_callback, queue_size=10
        )
        self._status_srv = rospy.Service(
            "/scout_move_control/move_status", Trigger, self._move_status_callback
        )
        rospy.loginfo("Scout move control server started")

    def _set_status(self, value):
        with self._lock:
            self._move_status = value

    def _get_status(self):
        with self._lock:
            return self._move_status

    def _move_status_callback(self, _request):
        return TriggerResponse(success=True, message=self._get_status())

    def _command_callback(self, msg):
        command = msg.data.strip()
        if not command:
            return

        with self._lock:
            if self._move_status == "moving":
                rospy.logwarn("Rejecting move command while moving: %s", command)
                return
            self._move_status = "moving"

        try:
            actions = parse_command_sequence(command)
        except ValueError as exc:
            rospy.logerr("Invalid move command '%s': %s", command, exc)
            self._publish_stop()
            self._set_status("stop")
            return

        worker = threading.Thread(target=self._execute_actions, args=(actions,), daemon=True)
        worker.start()

    def _publish_twist_for_duration(self, twist, duration):
        deadline = time.time() + duration
        rate = rospy.Rate(PUBLISH_HZ)
        while not rospy.is_shutdown() and time.time() < deadline:
            self._cmd_pub.publish(twist)
            rate.sleep()

    def _publish_stop(self):
        self._cmd_pub.publish(Twist())

    def _execute_actions(self, actions):
        try:
            for index, (direction, duration) in enumerate(actions):
                twist = build_twist(direction)
                self._publish_twist_for_duration(twist, duration)
                self._publish_stop()
                if index < len(actions) - 1:
                    time.sleep(DEFAULT_GAP_DURATION)
        finally:
            self._publish_stop()
            self._set_status("stop")


def main():
    if rospy is None:
        raise RuntimeError("ROS1 Python dependencies not available. Please source your ROS1 environment first.")

    rospy.init_node("scout_move_control")
    ScoutMoveControlServer()
    rospy.spin()


if __name__ == "__main__":
    main()
