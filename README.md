# OpenClaw Lab Adapter

`OpenClaw Lab Adapter` 是一个独立于 `openclaw` 的实验室适配项目，用来把现有无人车能力整理成更容易接入 OpenClaw 的 skills 和桥接层。源项目地址为：https://github.com/Hiwonder/openclaw/ --openclaw+ros

这个项目的定位不是直接复刻 `openclaw` 官方仓库，而是为实验室当前硬件、软件环境和后续二次开发预留空间。

## 目标

- 将已有无人车能力封装成 OpenClaw 可调用的 skill
- 保持底层执行与 OpenClaw 技能层解耦
- 为不同底盘、导航栈、传感器和机械臂留出适配空间
- 支持逐步替换 ROS1/ROS2、驱动、坐标系和硬件接口

## 当前阶段

第一阶段先提供两项基础能力，并增加一个项目级主智能体入口：

- `scout_move_control`
  - 自然语言风格的底盘动作封装
  - 对外表现为 OpenClaw 风格 topic/service
  - 当前底层默认对接 ROS1 `/cmd_vel`
- `scout_navigation_manager`
  - 命名地点导航
  - 当前底层默认对接 ROS1 `move_base`
  - 使用 YAML 管理 waypoint
- `scout_main_agent`
  - 作为项目主进程接入 Kimi 官方兼容 API
  - 负责将自然语言路由为本地 skills 调用
  - 当前支持调度 `scout_navigation_manager` 和 `scout_move_control`
  - 基于工具调用循环串行执行，适合作为 demo 智能体入口

## 目录结构

```text
openclaw_lab_adapter/
├── docs/                         # 项目说明与适配文档
├── agent/                        # 项目级主智能体入口
├── ros1_bridge/                  # ROS1 自定义消息/服务与桥接层
├── skills/                       # OpenClaw skills
│   ├── scout_move_control/
│   └── scout_navigation_manager/
└── templates/                    # 后续硬件适配模板占位
```

## 主智能体入口

在配置好环境变量后，可以直接用下面的方式把自然语言请求路由到本地 skills：

```bash
export OPENCLAW_LLM_API_KEY=your_key
export OPENCLAW_LLM_MODEL=kimi-k2.5
python3 agent/scout_main_agent.py --text "带我去前台"
python3 agent/scout_main_agent.py --text "前进1秒然后左转1秒" --dry-run
```

可选环境变量：

- `MOONSHOT_API_KEY`：Kimi 官方接口密钥，优先读取
- `KIMI_API_KEY`：Kimi 密钥别名，也会被识别
- `OPENCLAW_LLM_API_KEY`：自定义兼容网关密钥
- `OPENCLAW_LLM_BASE_URL`：兼容 OpenAI 的接口根地址，默认 `https://api.moonshot.cn/v1`
- `OPENCLAW_LLM_MODEL`：模型名称

## 与 openclaw 的关系

这个项目是独立项目，不要求直接并入 `openclaw` 仓库。

推荐工作方式：

1. 在这个项目里迭代实验室硬件适配
2. 等接口稳定后，再决定是否挑选部分能力同步回 `openclaw`

## 后续建议

- 把实验室真实底盘控制接口抽象到单独适配层
- 把导航栈、传感器、机械臂按设备拆成不同模块
- 把 waypoint、topic 名称、frame id、速度参数都改成可配置项
