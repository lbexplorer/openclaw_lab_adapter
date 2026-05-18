# 开发文档

本文档是 `openclaw_lab_adapter` 的统一开发记录和项目整理入口，用于持续记录项目进展、关键决策、验证情况和遗留问题，方便后续回顾、排查问题和新上下文接手项目。

本文档合并自：

- 根目录原 `DEVELOPMENT_LOG.md`
- `docs/log/开发文档.md`

它不替代 `README.md`，也不写成详细教程。README 负责说明项目是什么、怎么启动和当前能力；本文档负责记录每个阶段做了什么、解决了什么、还剩什么。

## 维护规则

- 最新记录放在最上方。
- 普通任务简洁记录：写清日期、改动范围、完成内容、验证方式和遗留问题即可。
- 关键阶段详细记录：补充背景、问题、实现结果、验证结果、风险边界和后续计划。
- 文档记录应区分“已完成”“已验证”“待确认”“缺口”，不要把未验证链路写成已完成能力。
- 涉及真实无人车接口、ROS / DDS / 导航 / 跟踪、运动安全或跨仓库参考时，应标明接口来源和风险边界。
- 后续开发进度优先维护本文档，避免在 `docs/log/开发文档.md` 等旧日志入口继续分散记录。

## 2026-05-16 - 更新 README 审阅入口

- 类型：文档整理。
- 改动范围：`README.md`、`docs/README.md`、`agent/README.md`、`docs/interfaces/README.md`、`test/README.md`、`DEVELOPMENT_LOG.md`。
- 完成内容：更新根目录 README 为导师审阅入口，明确 Demo 主线、当前能力、快速启动、关键文档和安全边界；同步 `docs/`、`agent/`、`interfaces/`、`test/` 子目录 README，补齐调试主入口、真实接口边界、agent 调度方式和新增静态测试说明。
- 验证方式：检查 README 链接指向和本机绝对路径，确认未修改代码行为、ROS / DDS / 导航 / 跟踪接口或真实运动控制链路。
- 遗留问题：README 中的现场启动命令仍需依赖无人车 ROS Noetic 环境和现场脚本验证。

## 2026-05-16 - 整理 docs/debug 文档入口

- 类型：文档整理。
- 改动范围：`docs/README.md`、`docs/debug/`、`DEVELOPMENT_LOG.md`。
- 完成内容：将现场启动、skill 调试和最小闭环命令统一到 `docs/debug/scout_bridge_quickstart_cn.md`；将 4.26 和 5.11 agent 调试记录合并到 `docs/debug/智能体调试记录.md`；保留旧文件作为历史兼容入口；整理 `docs/debug/坐标点记录.md` 标题和说明，未改动原始坐标数值；清理 debug 文档中的 Windows 本机绝对路径。
- 验证方式：人工检查文档职责边界，并用文本搜索确认 `docs/debug/` 中不再残留 `D:\Program Files\...` 形式的本机绝对路径。
- 遗留问题：车端 `/ssd1/...` 路径仍按现场运行环境保留为部署约定，后续如车端目录变化需同步调整启动文档。


## 2026-05-14 - 优化 agent 服务预检启动容错

- 类型：agent 启动和失败处理优化。
- 改动范围：`agent/chat_agent.py`、`agent/config/agent_config.yaml`、`skills/skill_protocol.py`、`test/test_chat_agent_static.py`、`test/test_scout_main_agent_static.py`、`DEVELOPMENT_LOG.md`。
- 完成内容：将 chat agent 执行动作前的导航、移动、巡逻服务检查从一次性判定改为短时间重试，减少 ROS service 刚启动但尚未被客户端发现时误报“服务未启动”的情况；新增可配置的 `service_preflight_timeout_seconds` 和 `service_preflight_poll_seconds`；补充 ROS service 等待超时的 `unavailable` 分类。
- 验证方式：运行 `python -m py_compile ...`、`python test\test_chat_agent_static.py`、`python test\test_scout_main_agent_static.py` 和 `Get-ChildItem test -Filter test_*.py | ForEach-Object { python $_.FullName }`，均通过。
- 遗留问题：本次只优化本仓库 agent 预检时序，不修改真实 ROS service、`move_base`、`cmd_vel` 或 Sailors 启动脚本；仍需在无人车 ROS Noetic 环境现场验证实际启动窗口时序。



## 2026-05-14 - 精简 README 项目入口

- 类型：文档整理。
- 改动范围：`README.md`、`DEVELOPMENT_LOG.md`。
- 完成内容：将 README 从早期详细说明压缩为项目定位、Demo 主线、当前能力、快速启动入口、目录索引和安全边界；详细启动命令保留在 `docs/debug/` 子文档中。
- 验证方式：人工检查 README 链接和内容边界，确认未修改代码行为或真实接口。
- 遗留问题：后续新增能力时优先更新对应子文档，README 只维护入口级说明。

## 2026-05-14 - 增加简洁启动指南

- 类型：文档补充。
- 改动范围：`docs/debug/scout_navigation_llm_startup_guide.md`、`DEVELOPMENT_LOG.md`。
- 完成内容：参考样例新增无人车导航、adapter skills 和 LLM agent 的简洁启动指南，保留安全提醒、Terminator 启动、手动启动和最小验证命令。
- 验证方式：对照 Sailors `sh/quick_start` 脚本和本仓库 Terminator 启动脚本检查命令。
- 遗留问题：现场运行时仍需在无人车 Linux/ROS Noetic 环境验证。

## 2026-05-14 - 增加 Terminator 启动脚本

- 类型：启动脚本与文档补充。
- 改动范围：`scripts/`、`docs/debug/scout_bridge_quickstart_cn.md`、`DEVELOPMENT_LOG.md`。
- 完成内容：新增 `launch_skills_terminator.sh` 用于分窗口启动导航和底盘 adapter skill 服务；新增 `launch_agent_terminator.sh` 用于启动 `chat_agent.py`；脚本均显式加载 `/opt/ros/noetic/setup.bash` 和 Sailors 工作空间 setup，并保留现场手动确认底层 `1startup.bash`、`2nav.bash` 的安全边界。
- 验证方式：计划执行 Bash 语法检查和内容检查，确认脚本不启动真实底层车端服务、不修改 ROS / DDS / 导航 / 跟踪接口。
- 遗留问题：需要在无人车 Linux/ROS Noetic 环境中现场验证 Terminator 窗口启动效果。

## 2026-05-14 - 合并开发日志并统一事实源

- 类型：文档整理。
- 改动范围：`DEVELOPMENT_LOG.md`、`docs/log/开发文档.md`。
- 完成内容：将根目录开发日志和旧版 `docs/log/开发文档.md` 合并为根目录统一开发文档；保留旧文档中的提交时间、commit hash、问题描述和实现效果；将旧路径改为指向本文档，避免后续重复维护。
- 验证方式：人工对照两个源文档内容，确认历史阶段、接口边界、遗留问题和维护规则均已保留。
- 遗留问题：后续项目规范化时可继续把 README、接口文档、调试文档和任务路由文档之间的职责边界整理得更清晰。

## 2026-05-14 - 清理 skills 目录无关内容

- 类型：目录整理。
- 改动范围：`skills/`。
- 完成内容：删除废弃空壳目录 `skills/scout_llm_agent`、Python 运行缓存 `__pycache__` 和巡逻运行态文件 `skills/patrol_fixed_points/patrol_state.json`；保留协同 Demo 主线需要的 5 个 skill 和 `skill_protocol.py`。
- 验证方式：检查 `skills/` 剩余目录，确认仅保留 `check_person_detected`、`patrol_fixed_points`、`scout_move_control`、`scout_navigation_manager`、`trigger_existing_tracking_handoff` 和 `skill_protocol.py`。
- 遗留问题：后续可继续同步 README 和 agent 文档中的目录说明，确保对外入口与实际目录一致。

## 2026-05-11 - Codex 规则轻量化重构

- 类型：文档规则重构。
- 改动范围：`AGENTS.md`、`docs/codex/02_TASK_ROUTER.md`、`CODEX_TASK.md`、`docs/interfaces/README.md`、`DEVELOPMENT_LOG.md`。
- 完成内容：将 Codex 工作规则从详细操作手册收敛为“短而硬的护栏 + 轻量路由 + 自动进度记录”；保留 `docs/codex/00-08` 作为参考资料，降低日常默认读取成本；明确重要改动后维护 `DEVELOPMENT_LOG.md`。
- 验证方式：文档一致性检查和 `git diff` 范围检查；确认未修改代码行为、ROS / DDS / 导航 / 跟踪接口或真实运动控制链路。
- 遗留问题：后续实际任务中需要持续观察新规则是否足够轻量，必要时再压缩路由表。

## 2026-05-11 - 建立根目录开发进度记录

- 类型：文档维护。
- 改动范围：新增根目录 `DEVELOPMENT_LOG.md`。
- 完成内容：建立持续维护的开发记录入口，明确普通任务和关键阶段的分层记录方式，并整理当前项目状态、已形成能力、接口资料入口和后续维护规则。
- 验证方式：人工检查文档结构，确认未修改代码行为、真实接口和运动控制链路。
- 遗留问题：后续每次重要改动后需要主动追加记录，避免进度散落在调试文档和对话上下文中。

## 2026-05-10 - 人员检测、巡逻停止和协同交接链路补齐

### 背景

巡逻过程中缺少持续读取人员检测结果的能力，发现人员后无法自动中止巡逻并进入协同流程。大车到小车的交接链路也缺少 skill 封装，agent 只能描述流程，不能确认目标是否进入现有 `/track_pose` 链路。

同时需要明确 `/track_pose` 与小车本地 `/TrackMsg` 跟踪控制输入不同，不能直接把大车位姿当成小车速度控制输入。

### 已完成

- 新增 `check_person_detected`，支持读取 `/track_pose`，并预留 `/DetectMsg` 检测结果读取。
- 扩展 `patrol_fixed_points`，支持 `stop_on_detection=true`，检测到人员后停止当前巡逻导航。
- 新增 `trigger_existing_tracking_handoff`，用于确认人员目标已进入现有 `/track_pose` 协同链路。
- 更新 agent 路由与配置，支持人员检测、巡逻检测停止和协同交接状态确认。
- 补充 Sailors 跟踪接口说明，明确 DDS `PoseMsgTopic`、`/track_pose`、`/TrackMsg` 的关系和边界。
- 补充人员检测、巡逻联动、协同交接和 agent 解析相关静态测试。

### 已解决问题

- 巡逻不再只能等待单点导航完成，可以在检测到人员时停止。
- agent 可以读取人员检测和协同交接结果，而不是只描述流程。
- 明确 `/track_pose` 不能直接等同于小车本地 `/TrackMsg` 跟踪控制输入。

### 遗留问题

- 小车“前往目标位置”和“小车执行静态人员跟踪”的完整现场闭环仍需在真实运行环境中验证。
- `/DetectMsg` 备选链路需要结合现场检测节点和消息内容继续确认。

## 2026-05-09 - Sailors Demo 真实接口和协同链路确认

### 背景

Demo 0.3 文档只说明了 `ros1_bridge` 与 `/track_pose`，DDS 如何连接两车、小车后续是导航到目标附近还是直接跟踪，都需要在封装 skill 前明确。已有 Sailors 代码中检测、DDS、导航、跟踪入口分散，后续封装 skill 前需要先确认真实接口。

### 已完成

- 对比 Demo 0.2、Demo 0.3、quick start 脚本和 Sailors 启动入口。
- 初步确认大车侧 `/track_pose` 可通过 DDS `PoseMsgTopic` 传到小车侧。
- 明确小车静态跟踪控制主要消费 `/TrackMsg`，不是直接消费 `/track_pose`。
- 确定后续优先复用现有 DDS / ROS 链路，不重写底层通信和控制逻辑。

### 遗留问题

- 真实接口仍以 `..\sailors_onboard-main` 代码为准，接口文档需要随现场代码变化同步更新。
- 协同指令到小车导航和本地跟踪之间的边界仍需通过现场联调固化。

## 2026-05-08 - 巡逻状态管理、超时和取消机制增强

### 背景

agent 调用 skills 后缺少持续状态反馈，导航失败原因不够清晰，等待期间无法合理处理超时、失败和取消。无人车侧在执行时需要规划路径和寻路，不一定能到达目标点；发生错误时，agent 侧至少需要接收到明确状态，把流程跑通后再继续优化容错机制。

### 已完成

- 实现巡逻 skill，复用导航 skill 进行单轮巡逻。
- 完善导航失败反馈，避免失败终态被提前写成 ready。
- 给 agent 调用 skill 增加 600s 总超时，超时后统一返回 `SkillResult(status=timeout)`。
- 增加 agent 执行进度日志，显示当前 skill、参数和执行状态。
- 把步骤记录写入最终输出，便于排查和 Demo 展示。
- 实现 cancel / stop 机制，取消请求发出后、`move_base` 回调未返回前拒绝新导航目标，避免旧 cancel 回调覆盖新任务状态。

### 已解决问题

- 导航失败原因不再丢失，可输出类似 `failed: target=... state=ABORTED(4)` 的终态信息。
- agent 侧不再无限等待 skill 执行结果。
- 取消和停止行为有了明确的状态边界。

### 遗留问题

- 异步持续巡逻暂未开放，需要在 Demo 和 stop / cancel 机制稳定后再推进。
- 真实运行中仍需持续观察导航失败、取消和重新下发目标的边界情况。

## 2026-05-07 - 统一 skills 协议和 agent 执行反馈

### 背景

已有 skills 可以被调用，但 agent 侧看不到明确执行结果，容易停留在“指令已下发”而不是“任务真实完成或失败”。智能体本身只能调用已有能力，如果底层 skill 不完整，agent 再复杂也只能停留在“会说但不会做”。

项目开发主线收敛为：

```text
技能接口标准化 -> 关键技能补齐 -> 智能体闭环编排
```

### 已完成

- 推进统一 skill 输入输出协议。
- 让 skill 返回执行状态，agent 能读取 `SkillResult`。
- 支持同步 skill 和异步 skill 的结果表达。
- 明确后续优先把 `sailors_onboard-main` 已有 ROS1 车端基础能力包装成稳定 skills，再让智能体做任务分解、调用和结果反馈。

### 遗留问题

- 后续新增 skill 需要继续遵守统一协议，避免 agent 侧结果解析重新分裂。

## 2026-05-06 - 修复 4.26 测试暴露的问题

- 类型：问题修复。
- 完成内容：确认 `/move_base_simple/goal` 缺少 action result 回调，不适合作为需要准确成功/失败语义的主链路；配置中直接保存 orientation `x/y/z/w`，适配服务不再从 yaw 二次换算。
- 已解决问题：避免 `navigation_status` 的 moving / finish 语义被 simple goal topic 弱化；减少坐标姿态二次换算误差来源。
- 遗留问题：导航结果语义仍应优先依赖 `move_base` action。

## 2026-04-27 22:47 - b629590 - 第一阶段稳定基线

### 已完成

- 标记第一阶段稳定版本。
- 补充阶段性 README、agent 说明、调试文档和设计文档。
- 整理 `docs/` 目录结构，将调试记录、方案设计、图片资源归类到 `debug/`、`design/`、`images/`。
- 更新导航点配置和静态测试说明，补充 agent 与 skills 的验证资料。

### 实现效果

- 项目形成可回溯的第一阶段稳定基线。
- 文档入口更清晰，调试截图、坐标记录、ROS 指令和 skill 调试记录集中管理。
- 静态测试和导航配置更贴近当前实验室演示环境。

## 2026-04-25 19:08 - c056fb6 - 实现 LLM Skill 编排 Agent

### 已完成

- 新增 `agent/chat_agent.py`，提供多轮对话式调试入口。
- 扩展 `agent/scout_main_agent.py`，支持将自然语言请求路由为本地 skills 调用。
- 增加 agent 配置文件和静态测试，覆盖能力清单、dry-run 调度、参数校验和执行确认流程。

### 实现效果

- agent 可以通过兼容 OpenAI 的大模型接口解析用户意图，并调度 `scout_navigation_manager`、`scout_move_control`。
- 支持 dry-run 模式，在不控制真实小车的情况下验证模型输出、参数和执行策略。
- 为后续协同 Demo 闭环提供智能体入口基础。

## 2026-04-23 19:40 - 9d88a1e - 实验室 Scout 适配集成工作

### 已完成

- 新增项目级 agent 原型、agent 配置和工作区配置。
- 补充 Sailors Demo skill 拆解、巡逻跟踪设计、项目范围说明和调试启动记录。
- 扩展导航点配置，加入实验室地图文件与静态测试脚本。
- 清理部分 Python 缓存文件，补充 `.gitignore`。

### 实现效果

- 项目从单个 skill 封装推进到“skills + agent + 文档 + 测试”的集成形态。
- 固定点导航、底盘动作和 agent 调度具备初步静态验证能力。
- Demo 目标进一步明确为围绕 Scout 无人车能力进行实验室适配。

## 2026-04-16 20:21 - bafee3c - 导航服务发布目标点坐标

### 已完成

- 在 `scout_navigation_manager` 服务端新增 `goal_dispatched` topic，用于发布已下发的导航目标坐标。
- 更新导航客户端逻辑，使客户端能够订阅并显示服务端发布的目标点信息。
- 补充 `scout_navigation_manager` 的 skill 文档说明。

### 实现效果

- 导航目标下发后，可以通过 topic 观察目标点坐标。
- 客户端不只知道命令是否发送，还能看到服务端实际分发的目标位置。
- 为后续 agent 判断导航动作和协同指令效果提供了更清晰的运行反馈。

## 2026-04-16 19:12 - 7c0a810 - 增加地图目录

### 已完成

- 新增 `maps/1201.pgm` 和 `maps/1201.yaml` 地图文件。

### 实现效果

- 项目开始纳入实验室导航地图资源。
- 为 `move_base` 命名地点导航和 waypoint 配置提供地图基础。

## 2026-04-14 14:37 - 初始项目提交

### 已完成

- 初始化 `openclaw_lab_adapter` 项目结构。
- 新增 `ros1_bridge/scout_openclaw_msgs`，定义 ROS1 自定义服务 `SetString.srv`。
- 新增 `scout_move_control` skill，封装前进、后退、转向、停止等底盘动作。
- 新增 `scout_navigation_manager` skill，封装基于命名地点的导航能力。
- 提供导航点 YAML 配置、移动控制服务端/客户端、导航服务端/客户端和基础项目文档。

### 实现效果

- 项目具备 OpenClaw 风格 skill 组织雏形。
- 底盘运动控制默认对接 ROS1 `/cmd_vel`，导航能力默认对接 ROS1 `move_base`。
- 为后续封装无人车 Demo skills 和 agent 奠定基础。

## 后续计划

- 持续把重要开发进展同步到本文档，减少只存在于聊天上下文或零散调试记录中的信息。
- 继续验证“大车巡逻 -> 人员检测 -> 协同指令 -> 小车导航 -> 静态人员跟踪”的完整现场链路。
- 在真实接口变更后同步更新 `docs/interfaces/`、任务路由文档和本文档。
- 对高风险改动保持明确边界：不直接修改真实运动控制、ROS / DDS / 导航 / 跟踪接口，除非任务明确要求并完成风险确认。


## 记录模板

### 普通任务记录

```text
## YYYY-MM-DD - 简短标题

- 类型：
- 改动范围：
- 完成内容：
- 验证方式：
- 遗留问题：
```

### 关键阶段记录

```text
## YYYY-MM-DD - 阶段名称

### 背景

### 已完成

### 已解决问题

### 验证情况

### 遗留问题

### 后续计划
```

## 当前项目状态

截至 2026-05-14，项目处于围绕无人车协同 Demo 主线继续收敛和文档规范化的阶段。主线固定为：

```text
大车固定点巡逻
-> 持续人员检测
-> 检测到静态人员
-> 发送协同指令
-> 小车接收指令
-> 小车前往目标位置
-> 小车执行静态人员跟踪
```

已形成的基础能力：

- `scout_move_control`：底盘动作封装，默认对接 ROS1 `/cmd_vel`。
- `scout_navigation_manager`：命名地点导航，默认对接 ROS1 `move_base`。
- `patrol_fixed_points`：固定点巡逻，支持检测触发停止。
- `check_person_detected`：人员检测结果读取，默认读取 `/track_pose`，并预留 `/DetectMsg`。
- `trigger_existing_tracking_handoff`：确认人员目标进入现有协同跟踪链路。
- `scout_main_agent` / `chat_agent`：项目级 agent 入口，用于自然语言到本地 skills 的路由、dry-run 和调试。

已确认的接口资料入口：

- `docs/interfaces/sailors_demo_interface_confirmation.md`
- `docs/interfaces/sailors_tracking_command_interfaces.md`
- `docs/interfaces/README.md`

当前优先级：

- 优先复用 `sailors_onboard-main` 已有 DDS / ROS / 导航 / 跟踪链路。
- 不重写底层通信和控制逻辑。
- 不把项目目标扩展为通用机器人平台。
- 真实接口和运动安全优先于演示便利性。
