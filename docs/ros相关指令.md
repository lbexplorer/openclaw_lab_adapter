用 map_server + RViz 看地图
终端一
source /opt/ros/noetic/setup.bash
roscore
---启动roscore和加载ros环境
终端二
source /opt/ros/noetic/setup.bash
rosrun map_server map_server /实际路径/1201.yaml
------------

终端三
source /opt/ros/noetic/setup.bash
rviz
-----------
启动rviz