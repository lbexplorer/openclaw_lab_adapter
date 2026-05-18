# ROS 常用调试指令

本文只保留通用 ROS / RViz 查看命令。Scout adapter 的启动、skill 测试和最小闭环命令统一维护在 [scout_bridge_quickstart_cn.md](scout_bridge_quickstart_cn.md)。

## 用 map_server + RViz 查看地图

终端 1：启动 ROS master。

```bash
source /opt/ros/noetic/setup.bash
roscore
```

终端 2：加载地图。`maps/1201.yaml` 是本仓库内的相对路径；如果现场使用 Sailors 车端地图，请替换为现场实际地图路径。

```bash
source /opt/ros/noetic/setup.bash
rosrun map_server map_server maps/1201.yaml
```

终端 3：打开 RViz。

```bash
source /opt/ros/noetic/setup.bash
rviz
```

## 同步项目到车端

在仓库根目录执行，避免记录 Windows 本机绝对路径：

```bash
scp -r . nvidia@<robot-ip>:/ssd1/workspace/openclaw_lab_adapter/
```
