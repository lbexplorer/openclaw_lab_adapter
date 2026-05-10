# 真实无人车接口文档

本目录用于集中存放项目开发过程中确认过的真实无人车接口文档。

这些文档的目标是让后续开发无需反复阅读 `sailors_onboard-main` 全量代码，就能快速了解当前 Demo 主线相关的真实接口、启动入口、输入输出和已知缺口。

## 文档列表

- `sailors_demo_interface_confirmation.md`：早期 Sailors Demo 接口确认总文档，覆盖导航、底盘、感知、DDS、跟踪等整体链路。
- `sailors_tracking_command_interfaces.md`：协同指令发送、小车接收、静态人员跟踪接口速查，记录当前已确认的真实代码和最小 skill 封装建议。

## 使用原则

- 真实接口以 `..\sailors_onboard-main` 中代码为准。
- 本目录只记录确认结果，不替代真实代码。
- 如果现场代码、topic、launch 或启动脚本发生变化，应同步更新本目录文档。
- 未确认的接口不要写成已完成能力，应明确标记为“待确认”或“缺口”。
- 新增或更新接口文档经用户审核确认后，应同步更新 `docs/codex/02_TASK_ROUTER.md` 中的文件路由，确保后续任务优先读取已确认文档。
