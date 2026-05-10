# AGENTS.md

## Codex 入口规则

本项目是无人车协同 Demo 项目，主线固定为：

```text
大车固定点巡逻
-> 持续人员检测
-> 检测到静态人员
-> 发送协同指令
-> 小车接收指令
-> 小车前往目标位置
-> 小车执行静态人员跟踪
```

每次任务先读取：

```text
AGENTS.md
docs/codex/02_TASK_ROUTER.md
```

不要默认完整读取 `CODEX_TASK.md` 或全部专题文档。根据任务类型读取所需文档和相关代码；简单任务保持最小读取，复杂任务优先保证完成质量和效果，必要时应扩展读取范围。

## 仓库修改边界

- 默认只允许修改 `openclaw_lab_adapter`。
- 当前开发目录为 `openclaw_lab_adapter`，位于本机 `D:\Program Files\科研材料\无人车\openclaw_lab_adapter`。
- `sailors_onboard-main` 位于同级目录 `..\sailors_onboard-main`，只作为真实无人车接口参考，真实接口以它为准，未经用户明确授权不得修改。
- `openclaw` 位于同级目录 `..\openclaw`，只作为 skill 组织方式参考，未经用户明确授权不得修改。
- 不得把项目目标扩展为通用机器人平台。

## 工作方式

- 简单任务可直接读取相关上下文、修改并说明验证方式。
- 复杂任务需要先明确计划和确认边界；如果已启用 Codex Plan mode，使用 Plan mode 的计划机制，不要重复生成第二份计划。
- 未启用 Plan mode 时，复杂任务先给出简要计划，等待用户确认后再修改。
- 涉及新增或修改 skill、agent 主流程、ROS / DDS / 导航 / 跟踪接口、真实机器人运动安全、跨模块重构、新依赖或新架构时，均视为复杂任务。

## 最高优先级原则

```text
Demo 主线 > 真实接口 > 最小改动 > 稳定可演示 > 代码优雅 > 未来扩展
```
