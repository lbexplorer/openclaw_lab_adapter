#!/usr/bin/env python3
"""ROS1 named-waypoint navigation adapter for Scout-like platforms."""

import argparse
import math
import os
import threading

import yaml

try:
    import actionlib
    import rospy
    from actionlib_msgs.msg import GoalStatus
    from geometry_msgs.msg import PoseStamped
    from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
    from std_msgs.msg import String
    from std_srvs.srv import Trigger, TriggerResponse
except ImportError:  # pragma: no cover
    actionlib = None
    rospy = None
    GoalStatus = None
    PoseStamped = None
    MoveBaseAction = None
    MoveBaseGoal = None
    String = None
    Trigger = None
    TriggerResponse = None

try:  # pragma: no cover
    from scout_openclaw_msgs.srv import SetString, SetStringResponse
except ImportError:  # pragma: no cover
    SetString = None
    SetStringResponse = None


def quaternion_from_yaw_degrees(yaw_degrees):
    half = math.radians(yaw_degrees) * 0.5
    return (0.0, 0.0, math.sin(half), math.cos(half))


def load_waypoints(path):
    with open(path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    positions = raw.get("navigation_positions", {})
    return {
        name: {
            "x": float(pose.get("x", 0.0)),
            "y": float(pose.get("y", 0.0)),
            "yaw": float(pose.get("yaw", 0.0)),
        }
        for name, pose in positions.items()
    }


class ScoutNavigationManagerServer(object):
    def __init__(self, waypoint_path, frame_id="map"):
        self._frame_id = frame_id
        self._waypoints = load_waypoints(waypoint_path)
        self._status = "ready"
        self._lock = threading.Lock()

        self._client = actionlib.SimpleActionClient("/move_base", MoveBaseAction)
        self._topic_sub = rospy.Subscriber(
            "/scout_navigation_manager/set_pose", String, self._set_pose_topic_callback, queue_size=10
        )
        self._status_srv = rospy.Service(
            "/scout_navigation_manager/navigation_status", Trigger, self._navigation_status_callback
        )
        self._list_srv = rospy.Service(
            "/scout_navigation_manager/list_positions", Trigger, self._list_positions_callback
        )
        self._mode_srv = rospy.Service(
            "/scout_navigation_manager/get_navigation_mode", Trigger, self._get_navigation_mode_callback
        )
        if SetString is not None:
            self._set_pose_srv = rospy.Service(
                "/scout_navigation_manager/set_pose", SetString, self._set_pose_service_callback
            )
        else:
            self._set_pose_srv = None
            rospy.logwarn("scout_openclaw_msgs/SetString unavailable, using topic fallback only")

        rospy.loginfo("Waiting for /move_base action server...")
        self._client.wait_for_server()
        rospy.loginfo("Scout navigation manager started with %d waypoint(s)", len(self._waypoints))

    def _set_status(self, value):
        with self._lock:
            self._status = value

    def _get_status(self):
        with self._lock:
            return self._status

    def _navigation_status_callback(self, _request):
        return TriggerResponse(success=True, message=self._get_status())

    def _list_positions_callback(self, _request):
        return TriggerResponse(success=True, message=",".join(sorted(self._waypoints.keys())))

    def _get_navigation_mode_callback(self, _request):
        return TriggerResponse(success=True, message="named_waypoints")

    def _set_pose_topic_callback(self, msg):
        name = msg.data.strip()
        if name:
            success, message = self._dispatch_target(name)
            if not success:
                rospy.logwarn("Failed to dispatch target '%s': %s", name, message)

    def _set_pose_service_callback(self, request):
        success, message = self._dispatch_target(request.data.strip())
        return SetStringResponse(success=success, message=message)

    def _dispatch_target(self, name):
        if not name:
            return False, "target name is empty"
        if self._get_status().startswith("moving to "):
            return False, "navigation is busy"
        pose = self._waypoints.get(name)
        if pose is None:
            return False, "can't find the navigation goal: %s" % name

        goal = MoveBaseGoal()
        goal.target_pose = PoseStamped()
        goal.target_pose.header.frame_id = self._frame_id
        goal.target_pose.header.stamp = rospy.Time.now()
        goal.target_pose.pose.position.x = pose["x"]
        goal.target_pose.pose.position.y = pose["y"]
        qx, qy, qz, qw = quaternion_from_yaw_degrees(pose["yaw"])
        goal.target_pose.pose.orientation.x = qx
        goal.target_pose.pose.orientation.y = qy
        goal.target_pose.pose.orientation.z = qz
        goal.target_pose.pose.orientation.w = qw

        self._set_status("moving to %s" % name)
        self._client.send_goal(
            goal,
            done_cb=lambda state, result, target=name: self._done_callback(target, state, result),
        )
        return True, "true"

    def _done_callback(self, target, terminal_state, _result):
        if terminal_state == GoalStatus.SUCCEEDED:
            self._set_status("finish")
            rospy.loginfo("Navigation finished: %s", target)
            return
        self._set_status("ready")
        rospy.logwarn("Navigation failed or ended early for %s, state=%s", target, terminal_state)


def main():
    if rospy is None:
        raise RuntimeError("ROS1 Python dependencies not available. Please source your ROS1 environment first.")

    parser = argparse.ArgumentParser(description="Scout navigation manager server")
    default_waypoints = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "config", "navigation_position.yaml"
    )
    parser.add_argument("--waypoints", default=default_waypoints, help="Waypoint YAML path")
    parser.add_argument("--frame-id", default="map", help="Frame id for move_base goals")
    args = parser.parse_args()

    rospy.init_node("scout_navigation_manager")
    ScoutNavigationManagerServer(args.waypoints, frame_id=args.frame_id)
    rospy.spin()


if __name__ == "__main__":
    main()
