# e-URDF-Zoo 🦾

[English](./README.md) | **中文**

> **ROSClaw 官方设备驱动中心** - 机器人与 AI 语义相遇的地方。

[![ROSClaw](https://img.shields.io/badge/ROSClaw-Ecosystem-blue)](https://github.com/ros-claw)
[![MuJoCo](https://img.shields.io/badge/MuJoCo-Menagerie-green)](https://github.com/google-deepmind/mujoco_menagerie)
[![License](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](LICENSE)

## 愿景

DeepMind 的 `mujoco_menagerie` 非常出色，但它纯粹是物理的。LLM 不理解纯物理 - 它们需要**语义和规则**。

**e-URDF-Zoo** 通过添加以下内容来弥合差距:
- 🧠 **语义描述符** - 这个机器人能做什么？
- 🛡️ **安全防火墙** - 物理限制是什么？
- 💬 **LLM 提示词** - AI 代理应该如何控制这个机器人？

## "具身资产包"

Zoo 中的每个机器人都是一个完整的、自描述的包:

```
robots/universal_robots_ur5e/
├── model.xml          # 物理基础: 来自 Menagerie 的 MuJoCo 模型
├── e_urdf.json        # 机器人灵魂: 安全、语义、感知
└── prompts/
    ├── system.md      # LLM 角色定义
    └── tools_usage.md # MCP 工具使用指南
```

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/ros-claw/e-urdf-zoo.git
cd e-urdf-zoo

# 安装依赖
pip install -e .
```

### 加载机器人

```python
from e_urdf_zoo import load_embodiment

# 加载带所有安全配置的 UR5e
ur5e = load_embodiment("universal_robots/ur5e")

# 与 mjlab-mcp-server 一起使用
from mjlab_mcp_server import PhysicsSandbox

sandbox = PhysicsSandbox(
    model_path=ur5e.model_xml,
    e_urdf_config=ur5e.config
)
```

## 支持的机器人

| 机器人 | 类型 | 状态 | 安全级别 |
|-------|------|--------|--------------|
| [UR5e](./robots/universal_robots_ur5e/) | 协作机械臂 | ✅ Ready | Dynamic |
| [Unitree G1](./robots/unitree_g1/) | 人形机器人 | ✅ Ready | ZMP 平衡 |

## 贡献您的机器人

我们使用 AI 来自动化硬件集成！

```bash
# 将您的机器人转换为 e-URDF 格式
sdk_to_mcp generate \
  --urdf ./my_robot.urdf \
  --sdk_docs ./manual.pdf \
  --output ./robots/my_robot/
```

AI 将自动:
1. 提取关节限制和物理参数
2. 生成带安全阈值的 `e_urdf.json`
3. 为您的特定硬件编写最优的 LLM 提示词

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM Agent (Claude/OpenClaw)               │
└─────────────────────────┬───────────────────────────────────┘
                          │ MCP 协议
┌─────────────────────────▼───────────────────────────────────┐
│              mjlab-mcp-server (潜意识)                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │ e-urdf-zoo   │───▶│   MuJoCo     │───▶│  安全        │   │
│  │  资产        │    │ 仿真         │    │  验证        │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │ ROS 2 / DDS
┌─────────────────────────▼───────────────────────────────────┐
│                    物理机器人硬件                             │
└─────────────────────────────────────────────────────────────┘
```

## 与 ROSClaw 集成

`e_urdf.json` 文件作为 MCP 资源暴露:

```json
{
  "mcpServers": {
    "rosclaw-ur5e": {
      "command": "python",
      "args": ["-m", "mjlab_mcp_server.server"],
      "env": {
        "E_URDF_ROBOT": "universal_robots_ur5e",
        "E_URDF_ZOO_PATH": "/path/to/e-urdf-zoo"
      }
    }
  }
}
```

## "潜意识"流程

1. **挂载**: 从 e-urdf-zoo 加载机器人到内存
2. **仿真**: LLM 生成动作 → `move_to(target)`
3. **拦截**: 不要立即发送到硬件！
4. **验证**: 以 100 倍速度运行物理仿真
   - 碰撞？ → `[FIREWALL] t=1.2s 碰撞`
   - 扭矩过载？ → `[FIREWALL] 降低加速度`
5. **释放**: 仅当 `SIM PASS` → 转发到 ROS 2

## 许可证

Apache 2.0 - See [LICENSE](LICENSE)

## 致谢

- [MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie) - 物理模型基础
- [ROSClaw](https://github.com/ros-claw) - 具身智能操作系统

---

**ROSClaw 具身智能操作系统的一部分**
