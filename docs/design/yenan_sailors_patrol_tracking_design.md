# 大车巡逻与小车跟踪系统设计方案

## 项目概述

本项目基于 Sailors Onboard 系统，实现大车巡逻、人员检测、DDS通信和小车跟踪的完整流程。系统将在1201区域开展常态化巡逻作业，同步进行人员检测，并在检测到人员时通过DDS通信通知小车执行跟踪任务。

## 系统架构

### 技能架构

| 技能名称 | 功能描述 | 实现要点 |
|---------|---------|--------|
| PatrolControlSkill | 控制大车在地图上的4个标定点位之间巡逻 | 加载巡逻点位配置，实现点位导航和循环巡逻 |
| PersonDetectionSkill | 使用大模型持续检测巡逻区域内的人员 | 加载预训练模型，持续获取图像，实时推理 |
| DDSCommunicationSkill | 通过DDS通信机制传输人员检测信息 | 初始化DDS环境，构建和发布消息 |
| PersonTrackingSkill | 控制小车前往目标位置跟踪人员 | 订阅DDS消息，解析目标位置，执行导航 |
| SystemCoordinationSkill | 协调各个技能的运行，处理系统级逻辑 | 管理技能生命周期，处理事件和错误 |

## 详细设计

### 1. 巡逻控制技能 (PatrolControlSkill)

#### 功能
- 控制大车在地图上的4个标定点位之间巡逻
- 实现点位间的自动切换和循环巡逻
- 监控巡逻状态，处理异常情况

#### 实现流程
1. **初始化**：加载巡逻点位配置文件
2. **点位导航**：依次导航到每个巡逻点位
3. **状态管理**：监控导航状态，处理导航失败情况
4. **循环巡逻**：完成所有点位后重新开始巡逻

#### 配置文件
```yaml
# patrol_points.yaml
patrol_points:
  - id: point1
    position: [x1, y1, theta1]
  - id: point2
    position: [x2, y2, theta2]
  - id: point3
    position: [x3, y3, theta3]
  - id: point4
    position: [x4, y4, theta4]
```

### 2. 人员检测技能 (PersonDetectionSkill)

#### 功能
- 使用大模型持续检测巡逻区域内的人员
- 实现不间断、持续性的人员检测
- 分析检测结果，判断是否存在目标人员

#### 实现流程
1. **模型加载**：加载预训练的人员检测模型
2. **图像获取**：持续获取相机图像
3. **模型推理**：使用大模型进行人员检测
4. **结果处理**：分析检测结果，判断是否存在人员
5. **状态更新**：更新人员检测状态，触发后续流程

#### 技术要点
- 采用持续运行模式，确保不间断检测
- 考虑大模型实时性，可能需要优化推理速度
- 实现检测结果的缓存和过滤，减少误报

### 3. DDS通信技能 (DDSCommunicationSkill)

#### 功能
- 通过DDS通信机制传输人员检测信息
- 确保消息的可靠传输和接收

#### 实现流程
1. **初始化**：初始化DDS通信环境
2. **消息构建**：构建包含人员位置的DDS消息
3. **消息发布**：发布消息到指定Topic
4. **状态监控**：监控通信状态，确保消息传递成功

#### 消息格式
```json
{
  "person_detected": true,
  "position": {
    "x": 1.0,
    "y": 2.0,
    "z": 0.0
  },
  "confidence": 0.95,
  "timestamp": "2026-04-21T10:00:00"
}
```

### 4. 人员跟踪技能 (PersonTrackingSkill)

#### 功能
- 控制小车前往目标位置跟踪人员
- 实现从小车接收到指令到执行跟踪的完整流程

#### 实现流程
1. **消息订阅**：订阅DDS通信的人员检测消息
2. **目标解析**：解析消息中的人员位置信息
3. **路径规划**：规划前往目标位置的路径
4. **导航执行**：控制小车前往目标位置
5. **跟踪监控**：监控跟踪状态，处理异常情况

### 5. 系统协调技能 (SystemCoordinationSkill)

#### 功能
- 协调各个技能的运行，处理系统级逻辑
- 管理技能间的通信和事件处理

#### 实现流程
1. **技能管理**：管理各个技能的生命周期
2. **事件处理**：处理技能间的事件和消息
3. **状态监控**：监控整个系统的运行状态
4. **错误处理**：处理系统错误和异常情况

## 系统协作流程

1. **系统启动**：
   - 系统协调技能初始化所有其他技能
   - 巡逻控制技能开始执行巡逻任务

2. **巡逻过程**：
   - 巡逻控制技能控制大车在点位间移动
   - 人员检测技能持续运行，分析相机图像
   - DDS通信技能待命，准备发送检测结果
   - 人员跟踪技能待命，准备接收指令

3. **人员检测**：
   - 人员检测技能检测到人员
   - 发送检测结果到系统协调技能
   - 系统协调技能触发DDS通信技能

4. **指令传输**：
   - DDS通信技能构建并发布DDS消息
   - 消息包含人员位置和置信度信息
   - 小车的人员跟踪技能接收消息

5. **跟踪执行**：
   - 人员跟踪技能解析消息，获取目标位置
   - 规划路径并控制小车前往目标位置
   - 到达目标位置后执行跟踪任务

6. **任务完成**：
   - 跟踪任务完成后，人员跟踪技能返回待命状态
   - 大车继续执行巡逻任务

## 技术实现要点

1. **大模型集成**：
   - 选择适合边缘设备的人员检测模型
   - 实现模型的持续推理和结果缓存
   - 优化推理速度，平衡实时性和准确性

2. **DDS通信**：
   - 利用现有的saw_dds模块
   - 定义清晰的消息格式和Topic名称
   - 实现消息的可靠传输和错误处理

3. **导航系统**：
   - 利用现有的move_base导航栈
   - 实现巡逻点位的自动切换
   - 处理导航过程中的异常情况

4. **系统集成**：
   - 设计模块化的技能架构
   - 实现技能间的高效通信
   - 确保系统的可靠性和稳定性

## 测试方案

1. **静态人员测试**：
   - 在地图上设置4个巡逻点位
   - 在巡逻路径上放置静态人员目标
   - 验证系统能否正确检测和跟踪人员

2. **系统集成测试**：
   - 验证技能间的协作是否正常
   - 测试DDS通信的可靠性
   - 评估系统的整体性能和稳定性

3. **边界情况测试**：
   - 测试多个人员同时出现的情况
   - 测试通信中断的情况
   - 测试导航异常的情况

## 部署与集成

### 启动文件
```xml
<!-- patrol_and_tracking.launch -->
<launch>
  <!-- 系统协调技能 -->
  <node pkg="sailors_skills" type="system_coordination_node.py" name="system_coordination_node" output="screen"/>
  
  <!-- 大车巡逻技能 -->
  <node pkg="sailors_skills" type="patrol_control_node.py" name="patrol_control_node" output="screen"/>
  
  <!-- 人员检测技能 -->
  <node pkg="sailors_skills" type="person_detection_node.py" name="person_detection_node" output="screen"/>
  
  <!-- DDS通信技能 -->
  <node pkg="sailors_skills" type="dds_communication_node.py" name="dds_communication_node" output="screen"/>
  
  <!-- 小车跟踪技能 -->
  <node pkg="sailors_skills" type="person_tracking_node.py" name="person_tracking_node" output="screen"/>
</launch>
```

### 目录结构
```
sailors_skills/
├── scripts/
│   ├── system_coordination_node.py
│   ├── patrol_control_node.py
│   ├── person_detection_node.py
│   ├── dds_communication_node.py
│   └── person_tracking_node.py
├── config/
│   ├── patrol_points.yaml
│   ├── detection_config.yaml
│   └── dds_config.yaml
├── launch/
│   └── patrol_and_tracking.launch
├── package.xml
└── CMakeLists.txt
```

## 预期效果

通过以上设计，系统将能够：
- 大车在1201区域的4个标定点位之间自动巡逻
- 持续检测区域内的人员，即使大模型实时性不足
- 当检测到人员时，通过DDS通知小车
- 小车自动前往目标位置进行跟踪
- 支持静态人员场景的测试验证

这个方案充分利用了现有的Sailors Onboard系统组件，同时集成了大模型目标检测和DDS通信功能，实现了大车和小车的协同工作。