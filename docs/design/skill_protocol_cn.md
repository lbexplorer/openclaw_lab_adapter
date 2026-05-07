# openclaw_lab_adapter 统一 Skill 协议

## 目标

本协议服务于当前 Demo 主线：

```text
大车固定点巡逻
→ 持续人员检测
→ 检测到静态人员
→ 发送协同指令
→ 小车接收指令
→ 小车前往目标位置
→ 小车执行静态人员跟踪
```

协议目标不是重写无人车底层能力，而是在 `openclaw_lab_adapter` 中为 agent 和 skills 建立稳定边界：

- 所有 skill 使用统一结果结构；
- skill 能返回执行状态；
- agent 能读取 skill result 并决定下一步；
- 同时支持同步 skill 和异步 skill；
- 后续新增 Demo skills 时遵循同一输入输出约定。

## 统一 SkillResult

每次 skill 调用必须返回一个可 JSON 序列化的字典：

```json
{
  "skill": "scout_navigation_manager",
  "status": "success",
  "execution_mode": "async",
  "message": "导航任务已完成。",
  "data": {
    "arguments": {
      "target": "工位2"
    }
  },
  "error": null,
  "trace": {
    "command": ["python", "skills/scout_navigation_manager/scripts/navigate.py", "--go", "工位2"],
    "returncode": 0,
    "stdout": "",
    "stderr": ""
  }
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `skill` | string | 是 | skill 名称 |
| `status` | string | 是 | 统一执行状态 |
| `execution_mode` | string | 是 | `sync` 或 `async` |
| `message` | string | 是 | 面向用户和调试的简短说明 |
| `data` | object | 是 | 结构化业务数据，例如参数、原始状态、目标点 |
| `error` | object/null | 是 | 失败时包含 `code` 和 `message` |
| `trace` | object | 是 | 调试信息，例如命令、返回码、标准输出 |

## status 枚举

| status | 含义 | agent 行为 |
|---|---|---|
| `success` | skill 已完成且成功 | 更新状态，向用户报告成功 |
| `failed` | skill 已完成但失败 | 不更新为成功状态，向用户报告失败原因 |
| `running` | 异步任务仍在执行 | 继续等待或向用户报告仍在执行 |
| `accepted` | 指令已被底层服务接收，但尚未完成 | 查询状态或等待异步结果 |
| `timeout` | 等待异步结果超时 | 报告尚未完成，不宣称成功 |
| `unavailable` | ROS 服务、脚本或底层能力不可用 | 提示启动对应服务 |
| `invalid_input` | 参数非法、目标不存在或命令格式错误 | 提示用户修正输入 |

## execution_mode

### sync

同步 skill 在一次调用内返回最终结果。

适用能力：

- `get_demo_status`
- `check_person_detected`
- `receive_tracking_command`
- `stop_vehicle`
- 查询导航/底盘状态

要求：

- 返回 `success`、`failed`、`unavailable` 或 `invalid_input` 等终态；
- 不返回 `accepted`；
- `data` 中放入可供 agent 判断的结构化状态。

### async

异步 skill 调用后可能不会立即完成。

适用能力：

- `patrol_fixed_points`
- `start_person_detection`
- `publish_tracking_command`
- `scout_navigation_manager`
- `track_static_person`

要求：

- 首次调用可以返回 `accepted` 或 `running`；
- 必须提供状态查询能力，供 agent 后续读取；
- 到达终态时返回 `success`、`failed`、`timeout`、`unavailable` 或 `invalid_input`；
- agent 不能把 `accepted` 直接展示为任务成功。

## 当前适配策略

现有 ROS-facing 脚本暂不强制重写。agent 执行层会把脚本返回码、标准输出和状态查询结果归一化为 `SkillResult`。

当前已接入：

- `scout_navigation_manager`
  - 执行模式：`async`
  - 初始成功下发：`accepted`
  - `finish`：`success`
  - `moving to xxx`：`running`
  - 下发后回到 `ready` 但没有 `finish`：`failed`

- `scout_move_control`
  - 执行模式：`async`
  - 初始成功下发：`accepted`
  - `moving`：`running`
  - `stop`：`success`

## 后续新增 skill 模板

新增 skill 时应先明确：

1. 对应 Demo 主线中的哪一步；
2. 是否同步完成；
3. 输入参数 schema；
4. 成功判断标准；
5. 失败判断标准；
6. 状态查询方式；
7. `data` 中 agent 需要读取哪些字段。

推荐返回：

```python
from skills import skill_protocol

result = skill_protocol.make_result(
    skill="check_person_detected",
    status=skill_protocol.SkillStatus.SUCCESS,
    execution_mode=skill_protocol.ExecutionMode.SYNC,
    message="已检测到静态人员。",
    data={"detected": True, "target": {"x": 1.2, "y": 0.4}},
)
```
