# CODEX_TASK.md

本项目是无人车协同 Demo 项目。Codex 的任务是基于现有无人车真实运行能力，参考 OpenClaw 的 skill 组织方式，在 `openclaw_lab_adapter` 中封装 Demo 所需 skills，并开发 agent，让系统稳定跑通以下闭环：

```text
大车固定点巡逻
-> 持续人员检测
-> 检测到静态人员
-> 发送协同指令
-> 小车接收指令
-> 小车前往目标位置
-> 小车执行静态人员跟踪
```

本文件是项目说明索引，不作为每次任务必须完整读取的大文档。每次任务优先读取：

```text
AGENTS.md
docs/codex/02_TASK_ROUTER.md
```

然后根据任务类型读取对应专题文档和相关代码。

## 专题文档索引

- `docs/codex/00_PROJECT_BRIEF.md`：项目定位、Demo 主线、当前阶段能力边界和最高优先级原则。
- `docs/codex/01_REPO_BOUNDARIES.md`：`sailors_onboard-main`、`openclaw`、`openclaw_lab_adapter` 的角色和修改边界。
- `docs/codex/02_TASK_ROUTER.md`：按任务类型决定应读取哪些文档和代码，是 Codex 每次任务的主要路由入口；只负责指导读什么、改什么、避开什么。
- `docs/codex/03_SKILL_CONTRACT.md`：skill 的职责、边界、输入输出、成功失败判断和建议 skill 范围。
- `docs/codex/04_AGENT_CONTRACT.md`：agent 的职责、默认执行主线、skill 调用规则和缺失能力处理原则。
- `docs/codex/05_ROS_DDS_NAVIGATION_NOTES.md`：ROS / DDS / 导航 / 跟踪接口的谨慎规则和安全边界。
- `docs/codex/06_WORKFLOWS.md`：简单任务、复杂任务、Plan mode 适配、确认要求、上下文阅读和验证方式。
- `docs/codex/07_ACCEPTANCE_CRITERIA.md`：当前阶段 Demo 的验收标准。
- `docs/codex/08_OUTPUT_TEMPLATES.md`：简单任务、复杂任务和普通模式下复杂任务修改前计划的输出格式。

## 核心提醒

- 默认只修改 `openclaw_lab_adapter`。
- 三个项目同处于本机 `D:\Program Files\科研材料\无人车` 目录下。
- 当前开发项目路径为 `openclaw_lab_adapter`。
- `sailors_onboard-main` 是真实无人车接口参考源，相对当前项目路径为 `..\sailors_onboard-main`。
- `openclaw` 只作为 skill 组织方式参考，相对当前项目路径为 `..\openclaw`。
- 不替换 DDS，不重构底层控制链路，不自行发明底层接口。
- 不引入与当前 Demo 无关的复杂能力。
