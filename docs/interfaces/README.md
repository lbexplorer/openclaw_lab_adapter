# 真实无人车接口文档

本目录集中存放项目开发过程中确认过的真实无人车接口文档，便于后续开发和导师审阅时快速理解当前 Demo 主线相关的 ROS / DDS / launch / topic / service 入口。

这些文档只记录确认结果，不替代仓库外 `sailors_onboard-main` 中的真实代码。真实接口发生变化时，应先以车端代码和现场验证为准，再同步更新本文档。

## 文档列表

- [sailors_demo_interface_confirmation.md](sailors_demo_interface_confirmation.md)：早期 Sailors Demo 接口确认总文档，覆盖导航、底盘、感知、DDS、跟踪等整体链路。
- [sailors_tracking_command_interfaces.md](sailors_tracking_command_interfaces.md)：协同指令发送、小车接收、静态人员跟踪接口速查，记录当前已确认的真实代码和最小 skill 封装建议。

## 当前接口边界

- 大车人员目标位姿优先复用现有 `/track_pose`。
- 大车到小车协同交接优先复用 Sailors 现有 DDS 链路，例如 `PoseMsgTopic`。
- 小车静态人员跟踪仍以现场已有接收和跟踪链路为准，不在本仓库重写底层控制。
- 本仓库 skills 只做读取、确认、封装和调度，不直接替代真实感知、DDS、导航或跟踪节点。

## 使用原则

- 真实接口以仓库外 `sailors_onboard-main` 中代码为准。
- 未确认的接口不要写成已完成能力，应明确标记为“待确认”或“缺口”。
- 如果现场代码、topic、launch 或启动脚本发生变化，应同步更新本目录文档。
- 涉及真实运动控制、`/cmd_vel`、导航目标下发或 DDS 链路变更时，需要先完成风险确认。
- 新增或更新接口文档后，应同步更新本文档列表；只有新增接口范围影响任务入口时，才同步调整 `../codex/02_TASK_ROUTER.md`。
