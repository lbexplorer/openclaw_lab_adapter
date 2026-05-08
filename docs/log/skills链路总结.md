
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
