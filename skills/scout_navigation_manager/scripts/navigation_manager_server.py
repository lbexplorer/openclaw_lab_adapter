#!/usr/bin/env python3
"""ROS1 waypoint navigation adapter with natural-language alias resolution.

这个脚本实现了一个ROS1导航管理服务器，用于Scout无人车的waypoint导航。
它支持通过自然语言别名解析目标位置，并与move_base action服务器通信来执行导航任务。
"""

import argparse
import math
import os
import re
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
    """将偏航角（度）转换为四元数。

    Args:
        yaw_degrees (float): 偏航角，单位为度。

    Returns:
        tuple: 四元数 (x, y, z, w)。
    """
    half = math.radians(yaw_degrees) * 0.5
    return (0.0, 0.0, math.sin(half), math.cos(half))


def normalize_text(text):
    """规范化文本：移除空白字符并转换为小写。

    Args:
        text (str): 输入文本。

    Returns:
        str: 规范化后的文本。
    """
    return re.sub(r"\s+", "", (text or "")).strip().lower()


def build_alias_candidates(name, aliases):
    """构建别名候选列表，去重并规范化。

    Args:
        name (str): 主要名称。
        aliases (list): 别名列表。

    Returns:
        list: 去重后的 (原始别名, 规范化别名) 元组列表。
    """
    candidates = [name]
    candidates.extend(aliases or [])
    deduped = []
    seen = set()
    for candidate in candidates:
        normalized = normalize_text(candidate)
        if not normalized or normalized in seen:
            continue
        deduped.append((candidate, normalized))
        seen.add(normalized)
    return deduped


def load_waypoints(path):
    """从YAML文件加载航点数据。

    Args:
        path (str): YAML文件路径。

    Returns:
        dict: 包含地图ID、框架ID、位置和别名映射的元数据。
    """
    with open(path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    if "navigation_positions" not in raw and "destinations" in raw:
        raw["navigation_positions"] = raw["destinations"]

    positions = raw.get("navigation_positions", {})
    normalized_positions = {}
    alias_to_name = {}

    for name, pose in positions.items():
        aliases = pose.get("aliases", []) if isinstance(pose, dict) else []
        if isinstance(aliases, str):
            aliases = [aliases]
        normalized_positions[name] = {
            "x": float(pose.get("x", 0.0)),
            "y": float(pose.get("y", 0.0)),
            "yaw": float(pose.get("yaw", 0.0)),
            "description": str(pose.get("description", "")).strip(),
            "aliases": aliases,
        }
        for _, normalized_alias in build_alias_candidates(name, aliases):
            alias_to_name[normalized_alias] = name

    metadata = {
        "map_id": raw.get("map_id", ""),
        "frame_id": raw.get("frame_id", "map"),
        "positions": normalized_positions,
        "alias_to_name": alias_to_name,
    }
    return metadata


class ScoutNavigationManagerServer(object):
    """Scout导航管理服务器类。

    该类管理Scout无人车的waypoint导航，支持通过别名解析目标位置，
    并与move_base action服务器通信来执行导航任务。
    """

    def __init__(self, waypoint_path, frame_id="map"):
        """初始化导航管理服务器。

        Args:
            waypoint_path (str): 航点YAML文件路径。
            frame_id (str): 导航目标的坐标框架ID，默认为'map'。
        """
        metadata = load_waypoints(waypoint_path)
        self._frame_id = metadata.get("frame_id") or frame_id
        self._map_id = metadata.get("map_id") or ""
        self._waypoints = metadata["positions"]
        self._alias_to_name = metadata["alias_to_name"]
        self._status = "ready"
        self._lock = threading.Lock()

        # 创建move_base action客户端
        self._client = actionlib.SimpleActionClient("/move_base", MoveBaseAction)
        # 订阅设置姿态的话题
        self._topic_sub = rospy.Subscriber(
            "/scout_navigation_manager/set_pose", String, self._set_pose_topic_callback, queue_size=10
        )
        # 提供导航状态服务
        self._status_srv = rospy.Service(
            "/scout_navigation_manager/navigation_status", Trigger, self._navigation_status_callback
        )
        # 提供列出位置的服务
        self._list_srv = rospy.Service(
            "/scout_navigation_manager/list_positions", Trigger, self._list_positions_callback
        )
        # 提供获取导航模式的服务
        self._mode_srv = rospy.Service(
            "/scout_navigation_manager/get_navigation_mode", Trigger, self._get_navigation_mode_callback
        )
        if SetString is not None:
            # 如果可用，提供设置姿态的服务
            
            self._set_pose_srv = rospy.Service(
                "/scout_navigation_manager/set_pose", SetString, self._set_pose_service_callback
            )
        else:
            self._set_pose_srv = None
            rospy.logwarn("scout_openclaw_msgs/SetString unavailable, using topic fallback only")

        # 等待move_base action服务器启动
        rospy.loginfo("Waiting for /move_base action server...")
        self._client.wait_for_server()
        rospy.loginfo(
            "Scout navigation manager started with %d waypoint(s), map_id=%s, frame_id=%s",
            len(self._waypoints),
            self._map_id or "unknown",
            self._frame_id,
        )

    def _set_status(self, value):
        """设置导航状态（线程安全）。

        Args:
            value (str): 新的状态值。
        """
        with self._lock:
            self._status = value

    def _get_status(self):
        """获取当前导航状态（线程安全）。

        Returns:
            str: 当前状态。
        """
        with self._lock:
            return self._status

    def _navigation_status_callback(self, _request):
        """导航状态服务的回调函数。

        Args:
            _request: 服务请求（未使用）。

        Returns:
            TriggerResponse: 包含当前状态的响应。
        """
        return TriggerResponse(success=True, message=self._get_status())

    def _list_positions_callback(self, _request):
        """列出位置服务的回调函数。

        Args:
            _request: 服务请求（未使用）。

        Returns:
            TriggerResponse: 包含所有位置名称的响应。
        """
        return TriggerResponse(success=True, message=",".join(sorted(self._waypoints.keys())))

    def _get_navigation_mode_callback(self, _request):
        """获取导航模式服务的回调函数。

        Args:
            _request: 服务请求（未使用）。

        Returns:
            TriggerResponse: 返回导航模式（固定为"named_waypoints"）。
        """
        return TriggerResponse(success=True, message="named_waypoints")

    def _resolve_target_name(self, raw_text):
        """解析目标名称，支持别名和模糊匹配。

        Args:
            raw_text (str): 原始输入文本。

        Returns:
            str or None: 解析后的目标名称，如果未找到则返回None。
        """
        normalized_text = normalize_text(raw_text)
        if not normalized_text:
            return None

        # 精确匹配
        exact_match = self._alias_to_name.get(normalized_text)
        if exact_match is not None:
            return exact_match

        # 模糊匹配：允许自然语言指令包含别名
        for alias, canonical_name in sorted(
            self._alias_to_name.items(), key=lambda item: len(item[0]), reverse=True
        ):
            if alias and alias in normalized_text:
                return canonical_name
        return None

    def _set_pose_topic_callback(self, msg):
        """设置姿态话题的回调函数。

        Args:
            msg (String): 包含目标名称的消息。
        """
        name = msg.data.strip()
        if name:
            success, message = self._dispatch_target(name)
            if not success:
                rospy.logwarn("Failed to dispatch target '%s': %s", name, message)

    def _set_pose_service_callback(self, request):
        """设置姿态服务的回调函数。

        Args:
            request (SetString): 服务请求，包含目标名称。

        Returns:
            SetStringResponse: 服务响应。
        """
        success, message = self._dispatch_target(request.data.strip())
        return SetStringResponse(success=success, message=message)

    def _dispatch_target(self, name):
        """调度导航目标到move_base。

        Args:
            name (str): 目标名称。

        Returns:
            tuple: (成功标志, 消息)。
        """
        if not name:
            return False, "target name is empty"
        if self._get_status().startswith("moving to "):
            return False, "navigation is busy"

        target_name = self._resolve_target_name(name)
        if target_name is None:
            return False, "can't find the navigation goal: %s" % name

        pose = self._waypoints.get(target_name)
        if pose is None:
            return False, "can't find the navigation goal: %s" % name

        # 构建MoveBaseGoal
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

        # 更新状态并发送目标
        self._set_status("moving to %s" % target_name)
        rospy.loginfo(
            "Resolved navigation request '%s' -> '%s' (x=%.3f, y=%.3f, yaw=%.1f)",
            name,
            target_name,
            pose["x"],
            pose["y"],
            pose["yaw"],
        )
        self._client.send_goal(
            goal,
            done_cb=lambda state, result, target=target_name: self._done_callback(target, state, result),
        )
        return True, "true"

    def _done_callback(self, target, terminal_state, _result):
        """导航完成回调函数。

        Args:
            target (str): 目标名称。
            terminal_state: 终端状态。
            _result: 结果（未使用）。
        """
        if terminal_state == GoalStatus.SUCCEEDED:
            self._set_status("finish")
            rospy.loginfo("Navigation finished: %s", target)
            return
        self._set_status("ready")
        rospy.logwarn("Navigation failed or ended early for %s, state=%s", target, terminal_state)


def main():
    """主函数：解析命令行参数并启动ROS节点。"""
    if rospy is None:
        raise RuntimeError("ROS1 Python dependencies not available. Please source your ROS1 environment first.")

    parser = argparse.ArgumentParser(description="Scout navigation manager server")
    default_waypoints = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "config", "navigation_position.yaml"
    )
    parser.add_argument("--waypoints", default=default_waypoints, help="Waypoint YAML path")
    parser.add_argument("--frame-id", default="map", help="Frame id for move_base goals")
    args = parser.parse_args()

    # 初始化ROS节点
    rospy.init_node("scout_navigation_manager")
    # 创建服务器实例
    ScoutNavigationManagerServer(args.waypoints, frame_id=args.frame_id)
    # 进入ROS事件循环
    rospy.spin()


if __name__ == "__main__":
    main()
