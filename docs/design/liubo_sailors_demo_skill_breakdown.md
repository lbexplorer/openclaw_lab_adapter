# Sailors Onboard Demo 技能设计方案

## 项目概述

本方案面向当前实验室 demo，基于 Sailors Onboard 系统，围绕 `1201` 区域构建“大车巡逻、人员检测、DDS 下发、小车执行”的最小业务闭环。  
当前测试条件为静态人员场景，目标是完成技能拆分、接口约束和联调方案设计。

## 设计原则

本方案中的 skills 设计遵循以下原则：

1. **面向业务闭环拆分**
   - skills 的划分围绕“巡逻、检测、下发、执行、编排”这条业务链路展开
   - 优先保证 demo 主链路清晰、完整、可联调

2. **单一职责**
   - 每个 skill 只负责一类事情，不承担跨层职责
   - `PatrolExecutionSkill` 只负责巡逻
   - `PersonPresenceDetectionSkill` 只负责人检测
   - `DetectionDispatchSkill` 只负责消息下发
   - `TrackingCommandConsumerSkill` 只负责小车执行
   - `DemoOrchestrationSkill` 只负责流程编排和状态管理

3. **接口解耦**
   - skill 之间通过标准输入、输出、事件和消息协作
   - 不直接依赖其他 skill 的内部实现
   - 上下游关系限定在接口层，而不是代码层

4. **贴合当前 demo 边界**
   - 设计以 `1201` 场景和静态人员测试为边界
   - 先支撑“能跑通、能联调、能验收”的能力，再逐步扩展

5. **先稳定能力，再补统一编排**
   - 优先固化巡逻、检测、下发、执行四类核心能力
   - 编排 skill 负责统一状态管理，但不替代其他 skills 的核心职责

6. **可独立开发、可组合联调**
   - 每个 skill 都应具备清晰输入输出
   - 开发阶段可通过 mock 事件、模拟消息、替代数据源进行独立验证
   - 联调阶段再按统一协议完成组合

## 系统架构

### 技能架构

| 技能名称 | 功能描述 | 实现要点 |
|---------|---------|--------|
| PatrolExecutionSkill | 控制大车按固定点位执行巡逻任务 | 加载 waypoint 配置，执行循环巡逻，输出导航状态 |
| PersonPresenceDetectionSkill | 持续检测巡逻区域内是否存在人员 | 持续获取图像，执行人员检测，输出检测事件 |
| DetectionDispatchSkill | 将检测结果转换为 DDS 指令消息 | 构建标准消息，发布指定 Topic，控制重复发送 |
| TrackingCommandConsumerSkill | 小车接收指令并执行跟踪/接近任务 | 订阅 DDS Topic，解析目标信息，启动导航或跟踪 |
| DemoOrchestrationSkill | 管理 demo 运行状态与技能协作 | 管理启停、状态流转、异常处理与任务编排 |

### 技能依赖关系

```text
PatrolExecutionSkill
        |
        v
PersonPresenceDetectionSkill
        |
        v
DetectionDispatchSkill
        |
        v
TrackingCommandConsumerSkill

DemoOrchestrationSkill 负责统一编排与状态管理
```

## 详细设计

### 1. 巡逻执行技能 (PatrolExecutionSkill)

#### 功能

- 控制大车在 `1201` 地图固定点位之间巡逻
- 支持按顺序执行和循环巡逻
- 输出巡逻状态与导航事件

#### 输入

- `map_id`
- `patrol_points`
- `loop`

#### 输出

- `patrol_status`
- `current_waypoint`
- `navigation_event`

#### 实现流程

1. **初始化**：加载地图与巡逻点配置
2. **点位导航**：依次向目标点发送导航任务
3. **状态更新**：监听导航状态并输出巡逻事件
4. **循环执行**：完成一轮后按配置继续巡逻

#### 配置示例

```yaml
patrol_points:
  - id: point1
    pose: [x1, y1, yaw1]
  - id: point2
    pose: [x2, y2, yaw2]
  - id: point3
    pose: [x3, y3, yaw3]
  - id: point4
    pose: [x4, y4, yaw4]
loop: true
map_id: "1201"
```

### 2. 人员存在检测技能 (PersonPresenceDetectionSkill)

#### 功能

- 持续检测巡逻区域内是否存在人员
- 输出检测结果、置信度和目标位置信息
- 为下游 DDS 下发提供统一检测事件

#### 输入

- `image_topic`
- `target_class`
- `confidence_threshold`
- `cooldown_ms`

#### 输出

- `person_detected`
- `confidence`
- `target_position`
- `detection_timestamp`

#### 实现流程

1. **模型加载**：加载人员检测模型或检测服务
2. **图像采集**：持续获取相机图像
3. **持续推理**：循环执行人员检测
4. **结果过滤**：按阈值、时间窗和重复策略过滤结果
5. **事件输出**：输出标准检测事件

#### 设计约束

- 当前采用持续运行模式
- 当前检测目标固定为 `person`
- 当前以静态人员测试为主

### 3. 检测下发技能 (DetectionDispatchSkill)

#### 功能

- 接收检测事件
- 构建标准 DDS 消息
- 向指定 Topic 发布跟踪指令

#### 输入

- `detection_event`
- `dds_topic`
- `message_schema`
- `publish_policy`

#### 输出

- `dispatch_success`
- `message_id`
- `dispatch_timestamp`

#### 实现流程

1. **初始化**：加载 DDS 配置与 Topic 信息
2. **事件接收**：接收检测技能输出的检测事件
3. **消息构建**：组装标准指令消息
4. **消息发布**：发布到指定 DDS Topic
5. **状态记录**：记录发送结果与重发控制状态

#### 消息格式

```json
{
  "event": "person_detected",
  "map_id": "1201",
  "target_id": "person_001",
  "position": {
    "x": 1.0,
    "y": 2.0,
    "yaw": 0.0
  },
  "confidence": 0.95,
  "timestamp": "2026-04-21T10:00:00"
}
```

### 4. 跟踪指令消费技能 (TrackingCommandConsumerSkill)

#### 功能

- 接收 DDS 指令
- 解析目标位置与任务类型
- 控制小车执行接近或跟踪任务

#### 输入

- `dds_topic`
- `target_message`
- `navigation_interface`
- `tracking_policy`

#### 输出

- `tracking_status`
- `target_ack`
- `tracking_result`

#### 实现流程

1. **消息订阅**：订阅目标 DDS Topic
2. **消息解析**：解析目标位置、时间戳和置信度
3. **任务判定**：判断是否满足执行条件
4. **导航执行**：驱动小车前往目标区域
5. **任务反馈**：返回执行状态和结果

#### 当前范围

- 当前优先支持静态人员场景
- 当前验收以“收到指令后可启动接近/跟踪动作”为准

### 5. Demo 编排技能 (DemoOrchestrationSkill)

#### 功能

- 管理 demo 全流程启停
- 管理各技能状态流转
- 处理 demo 级异常与恢复

#### 输入

- 各技能状态事件
- 启停控制指令
- 异常告警事件

#### 输出

- `system_state`
- `orchestration_event`
- `recovery_action`

#### 实现流程

1. **技能初始化**：初始化各 skill 运行上下文
2. **状态监听**：监听巡逻、检测、下发、跟踪状态
3. **流程编排**：根据事件推动 demo 主流程
4. **异常处理**：处理导航失败、检测失败、消息异常
5. **任务收尾**：任务完成后恢复待命状态

#### 状态集合

- `idle`
- `patrolling`
- `detecting`
- `person_detected`
- `dispatching`
- `tracking`
- `finished`
- `error`

## 系统协作流程

1. **系统启动**：
   - Demo 编排技能初始化各技能
   - 巡逻执行技能进入巡逻状态

2. **巡逻阶段**：
   - 大车按固定点位执行巡逻
   - 人员检测技能持续运行

3. **检测触发**：
   - 检测到人员后输出标准检测事件
   - 下发技能构建并发布 DDS 消息

4. **小车执行**：
   - 小车订阅并解析 DDS 指令
   - 启动接近或跟踪任务

5. **任务完成**：
   - 小车返回执行状态
   - 系统恢复巡逻待命或继续巡逻

## 技术实现要点

1. **导航能力复用**：
   - 复用现有 `1201` 地图与导航栈
   - 重点封装巡逻任务能力

2. **检测持续运行**：
   - 检测模块持续执行
   - 通过阈值、冷却时间和重复控制减少误触发

3. **DDS 指令标准化**：
   - 固定 Topic 与消息结构
   - 明确事件类型、目标位置和时间戳字段

4. **技能解耦**：
   - 技能之间通过标准事件和消息交互
   - 避免直接依赖彼此内部实现

## 测试方案

1. **静态人员测试**：
   - 大车按固定点位巡逻
   - 检测模块识别静态人员
   - 验证检测事件能触发指令下发

2. **DDS 联调测试**：
   - 验证消息可正确发布和接收
   - 验证小车收到消息后能启动任务

3. **系统集成测试**：
   - 验证各技能状态流转正确
   - 验证主链路闭环稳定运行

## 部署与集成

### 启动文件

```xml
<!-- patrol_demo.launch -->
<launch>
  <node pkg="sailors_demo_skills" type="demo_orchestration_node.py" name="demo_orchestration_node" output="screen"/>
  <node pkg="sailors_demo_skills" type="patrol_execution_node.py" name="patrol_execution_node" output="screen"/>
  <node pkg="sailors_demo_skills" type="person_presence_detection_node.py" name="person_presence_detection_node" output="screen"/>
  <node pkg="sailors_demo_skills" type="detection_dispatch_node.py" name="detection_dispatch_node" output="screen"/>
  <node pkg="sailors_demo_skills" type="tracking_command_consumer_node.py" name="tracking_command_consumer_node" output="screen"/>
</launch>
```

### 目录结构

```text
sailors_demo_skills/
├── scripts/
│   ├── demo_orchestration_node.py
│   ├── patrol_execution_node.py
│   ├── person_presence_detection_node.py
│   ├── detection_dispatch_node.py
│   └── tracking_command_consumer_node.py
├── config/
│   ├── patrol_points.yaml
│   ├── detection_config.yaml
│   ├── dds_config.yaml
│   └── orchestration_config.yaml
├── launch/
│   └── patrol_demo.launch
├── package.xml
└── CMakeLists.txt
```

## 预期效果

通过以上设计，系统将能够：

- 大车在 `1201` 区域固定点位之间自动巡逻
- 巡逻过程中持续检测人员目标
- 检测到人员后通过 DDS 发布标准指令
- 小车接收指令后启动接近或跟踪任务
- 支持静态人员场景下的 demo 联调与验证
