# e-URDF-Zoo 🦾

🌐 **English** | [中文](./README.zh.md)

> **The Official Device Driver Hub for ROSClaw** - Where robots meet AI semantics.

[![ROSClaw](https://img.shields.io/badge/ROSClaw-Ecosystem-blue)](https://github.com/ros-claw)
[![MuJoCo](https://img.shields.io/badge/MuJoCo-Menagerie-green)](https://github.com/google-deepmind/mujoco_menagerie)
[![License](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](LICENSE)

## Vision

DeepMind's `mujoco_menagerie` is excellent, but it's purely physical. LLMs don't understand pure physics - they need **semantics and rules**.

**e-URDF-Zoo** bridges the gap by adding:
- 🧠 **Semantic descriptors** - What can this robot do?
- 🛡️ **Safety firewalls** - What are the physical limits?
- 💬 **LLM prompts** - How should AI agents control this robot?

## The "Embodiment Asset Bundle"

Each robot in the Zoo is a complete, self-describing package:

```
robots/universal_robots_ur5e/
├── model.xml          # Physical base: MuJoCo model from Menagerie
├── e_urdf.json        # Robot soul: Safety, semantics, perception
└── prompts/
    ├── system.md      # LLM role definition
    └── tools_usage.md # MCP tool usage guide
```

## Quick Start

### Install

```bash
# Clone the repository
git clone https://github.com/ros-claw/e-urdf-zoo.git
cd e-urdf-zoo

# Install dependencies
pip install -e .
```

### Load a Robot

```python
from e_urdf_zoo import load_embodiment

# Load UR5e with all safety configs
ur5e = load_embodiment("universal_robots/ur5e")

# Use with mjlab-mcp-server
from mjlab_mcp_server import PhysicsSandbox

sandbox = PhysicsSandbox(
    model_path=ur5e.model_xml,
    e_urdf_config=ur5e.config
)
```

## Supported Robots

| Robot | Type | Status | Safety Level |
|-------|------|--------|--------------|
| [UR5e](./robots/universal_robots_ur5e/) | Collaborative Arm | ✅ Ready | Dynamic |
| [Unitree G1](./robots/unitree_g1/) | Humanoid | ✅ Ready | ZMP Balance |

## Contributing Your Robot

We use AI to automate hardware integration!

```bash
# Convert your robot to e-URDF format
sdk_to_mcp generate \
  --urdf ./my_robot.urdf \
  --sdk_docs ./manual.pdf \
  --output ./robots/my_robot/
```

The AI will automatically:
1. Extract joint limits and physical parameters
2. Generate `e_urdf.json` with safety thresholds
3. Write optimal LLM prompts for your specific hardware

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM Agent (Claude/OpenClaw)               │
└─────────────────────────┬───────────────────────────────────┘
                          │ MCP Protocol
┌─────────────────────────▼───────────────────────────────────┐
│              mjlab-mcp-server (Subconscious)                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │ e-urdf-zoo   │───▶│   MuJoCo     │───▶│  Safety      │   │
│  │  Assets      │    │ Simulation   │    │  Validation  │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │ ROS 2 / DDS
┌─────────────────────────▼───────────────────────────────────┐
│                    Physical Robot Hardware                   │
└─────────────────────────────────────────────────────────────┘
```

## Integration with ROSClaw

The `e_urdf.json` files are exposed as MCP Resources:

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

## The "Subconscious" Flow

1. **Mount**: Load robot from e-urdf-zoo into memory
2. **Simulate**: LLM generates action → `move_to(target)`
3. **Intercept**: Don't send to hardware yet!
4. **Validate**: Run 100x speed physics simulation
   - Collision? → `[FIREWALL] Collision at t=1.2s`
   - Torque overload? → `[FIREWALL] Reduce acceleration`
5. **Release**: Only if `SIM PASS` → forward to ROS 2

## License

Apache 2.0 - See [LICENSE](LICENSE)

## Acknowledgments

- [MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie) - Physical models base
- [ROSClaw](https://github.com/ros-claw) - Embodied Intelligence OS ([arXiv paper](https://arxiv.org/pdf/2604.04664))

---

**Part of the ROSClaw Embodied Intelligence Operating System**
