
导航
agent / patrol_fixed_points
-> python3 skills/scout_navigation_manager/scripts/navigate.py --go 原点
-> navigate.py 解析“原点”是否合法
-> 调用 ROS 服务 /scout_navigation_manager/set_pose
-> navigation_manager_server.py 收到目标名
-> 解析别名/标准点位
-> 读取 navigation_position.yaml 中的坐标和四元数
-> 构造 MoveBaseGoal
-> send_goal 到 /move_base
-> move_base 执行规划和导航
-> navigation_manager_server.py 在 done callback 中更新状态
-> navigate.py --status 查询 /scout_navigation_manager/navigation_status
-> agent / patrol 根据状态判断 accepted / running / success / failed

navigate.py 给 agent、巡逻 skill、命令行测试提供统一入口。
navigation_manager_server.py 常驻 ROS 环境里，维护和 /move_base 的 action client 连接。



巡逻
用户自然语言
-> agent 选择 patrol_fixed_points
-> agent 启动 patrol.py --run
-> patrol.py 读取默认巡逻点配置
-> 校验巡逻点是否存在于导航点配置
-> 逐点调用 navigate.py --go 点位名
-> navigate.py 调用 /scout_navigation_manager/set_pose
-> navigation_manager_server.py 下发 move_base goal
-> patrol.py 轮询 navigate.py --status
-> 根据状态 finish / ready / failed / timeout 生成 SkillResult
-> agent 读取 SkillResult，把结果交给大模型组织回复



人员检测
用户自然语言
-> agent 选择 check_person_detected
-> agent 启动 check_person_detected.py --check
-> check_person_detected.py 读取 detection_config.yaml 默认配置
-> 默认 source=track_pose，订阅 /track_pose
-> Sailors sensing_node 持续运行相机检测、障碍物融合和位姿转换
-> camera_object_detection_nodelet.cpp 发现人员目标后生成 geometry_msgs/Pose
-> sensing_node.cpp 通过 saw_comm::topic::kTrackPose 发布 track pose
-> check_person_detected.py 通过 rospy.wait_for_message 等待一条检测结果
-> 收到 /track_pose 时认为已有可用于协同下发的人员目标位姿
-> 生成 SkillResult，data.person_detected=true，data.target_pose=目标位姿
-> agent 读取 SkillResult，把检测结果呈现给用户或交给后续协同指令 skill

备选链路：
check_person_detected.py --check --source detect_msg
-> 订阅 /DetectMsg
-> toy_utils/perception_toy 的 camera_object_detection_main.py 发布 msgs/TargetArray
-> tracking_main.py 可继续把 /DetectMsg 转成 /TrackMsg
-> check_person_detected.py 根据 target.frame_id 是否为 person/0x1/1 和 confidence_threshold 判断是否检测到人员
-> 生成 SkillResult，data.person_detected=true/false，data.detections=检测框列表

check_person_detected 只读取已有 ROS topic，不启动检测模型，不修改 sailors_onboard-main。
如果 ROS 依赖不可用，返回 unavailable；如果等待不到检测消息，返回 timeout；如果 topic 正常但 /DetectMsg 为空，返回 success 且 person_detected=false。
