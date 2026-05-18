# Docs Index

项目文档统一放在 `docs/` 下，按用途分类管理。根目录 [README.md](../README.md) 只保留项目入口和关键链接，详细启动、接口和调试信息维护在本目录。

## debug

调试、启动、排查和现场记录：

- [debug/scout_bridge_quickstart_cn.md](debug/scout_bridge_quickstart_cn.md)：现场启动、adapter skill、巡逻、检测、协同交接和 agent 调度主入口。
- [debug/智能体调试记录.md](debug/智能体调试记录.md)：agent 调试记录主入口，合并历史 4.26 和 5.11 记录。
- [debug/坐标点记录.md](debug/坐标点记录.md)：1201 地图现场点位原始坐标记录，坐标数据不做二次改写。
- [debug/ros相关指令.md](debug/ros相关指令.md)：通用 ROS / RViz 查看命令。

## design

方案设计、项目范围和协议说明：

- [design/project_scope_cn.md](design/project_scope_cn.md)：项目范围和边界。
- [design/liubo_sailors_demo_skill_breakdown.md](design/liubo_sailors_demo_skill_breakdown.md)：Sailors Demo skill 拆解。
- [design/skill_protocol_cn.md](design/skill_protocol_cn.md)：skill 输入输出协议说明。

## interfaces

真实无人车接口确认、topic / service / DDS / launch 入口和现场链路说明：

- [interfaces/README.md](interfaces/README.md)：接口文档入口和维护原则。
- [interfaces/sailors_demo_interface_confirmation.md](interfaces/sailors_demo_interface_confirmation.md)：Sailors Demo 接口确认总文档。
- [interfaces/sailors_tracking_command_interfaces.md](interfaces/sailors_tracking_command_interfaces.md)：协同指令、DDS、跟踪接口速查。

## codex

Codex / agent 协作规则和项目上下文参考：

- [codex/00_PROJECT_BRIEF.md](codex/00_PROJECT_BRIEF.md)
- [codex/01_REPO_BOUNDARIES.md](codex/01_REPO_BOUNDARIES.md)
- [codex/02_TASK_ROUTER.md](codex/02_TASK_ROUTER.md)
- [codex/03_SKILL_CONTRACT.md](codex/03_SKILL_CONTRACT.md)
- [codex/04_AGENT_CONTRACT.md](codex/04_AGENT_CONTRACT.md)
- [codex/05_ROS_DDS_NAVIGATION_NOTES.md](codex/05_ROS_DDS_NAVIGATION_NOTES.md)
- [codex/06_WORKFLOWS.md](codex/06_WORKFLOWS.md)
- [codex/07_ACCEPTANCE_CRITERIA.md](codex/07_ACCEPTANCE_CRITERIA.md)
- [codex/08_OUTPUT_TEMPLATES.md](codex/08_OUTPUT_TEMPLATES.md)

## images

文档图片统一放在 `images/` 下。Markdown 文档中优先使用相对路径引用，例如：

```markdown
![alt text](../images/image.png)
```

## log

历史日志入口保留在 `log/`。后续项目进度优先维护 [log/DEVELOPMENT_LOG.md](log/DEVELOPMENT_LOG.md)。
