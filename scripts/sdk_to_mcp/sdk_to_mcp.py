#!/usr/bin/env python3
"""
sdk_to_mcp: Automated e-URDF Asset Generator

Converts traditional robot SDKs and URDF files into e-URDF Embodiment Asset Bundles.
Uses LLM-based extraction to generate semantic descriptions, safety parameters, and prompts.

Usage:
    sdk_to_mcp generate --urdf ./robot.urdf --sdk_docs ./manual.pdf --output ./robot/
    sdk_to_mcp generate --urdf ./robot.urdf --output ./robot/  # Without SDK docs
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


def parse_urdf(urdf_path: Path) -> dict[str, Any]:
    """Parse URDF file and extract robot information."""
    tree = ET.parse(urdf_path)
    root = tree.getroot()

    robot_name = root.get("name", "unknown_robot")

    # Extract joints
    joints = []
    joint_limits = {}
    for joint in root.findall(".//joint"):
        name = joint.get("name")
        jtype = joint.get("type", "fixed")

        if jtype in ["revolute", "continuous", "prismatic"]:
            limit = joint.find("limit")
            if limit is not None:
                lower = float(limit.get("lower", "-3.14"))
                upper = float(limit.get("upper", "3.14"))
                effort = float(limit.get("effort", "100"))
                velocity = float(limit.get("velocity", "10"))

                joint_limits[name] = {
                    "type": jtype,
                    "lower": lower,
                    "upper": upper,
                    "effort": effort,
                    "velocity": velocity,
                }

        joints.append({
            "name": name,
            "type": jtype,
            "parent": joint.find("parent").get("link") if joint.find("parent") else None,
            "child": joint.find("child").get("link") if joint.find("child") else None,
        })

    # Extract links
    links = [link.get("name") for link in root.findall(".//link")]

    return {
        "name": robot_name,
        "joints": joints,
        "joint_limits": joint_limits,
        "links": links,
        "dof": len([j for j in joints if j["type"] in ["revolute", "prismatic"]]),
    }


def infer_robot_type(urdf_info: dict[str, Any]) -> str:
    """Infer robot type from URDF structure."""
    name = urdf_info["name"].lower()
    links = [l.lower() for l in urdf_info["links"]]
    joints = urdf_info["joints"]

    # Check for humanoid patterns
    has_legs = any("leg" in l or "hip" in l or "knee" in l or "ankle" in l for l in links)
    has_arms = any("arm" in l or "shoulder" in l or "elbow" in l or "wrist" in l for l in links)
    has_head = any("head" in l or "neck" in l for l in links)
    has_torso = any("torso" in l or "pelvis" in l or "waist" in l for l in links)

    if has_legs and has_arms and has_head and has_torso:
        return "humanoid"
    elif has_legs and has_torso:
        return "legged"
    elif has_arms and not has_legs:
        return "manipulator"
    elif "gripper" in name or "hand" in name:
        return "gripper"
    elif "mobile" in name or "base" in name:
        return "mobile_base"
    else:
        return "generic"


def generate_e_urdf(urdf_info: dict[str, Any], robot_type: str) -> dict[str, Any]:
    """Generate e_urdf.json structure from URDF info."""

    # Infer capabilities based on type
    affordances = {
        "humanoid": [
            "bipedal_locomotion", "walking", "standing", "balancing",
            "reaching", "grasping", "gesticulation"
        ],
        "manipulator": [
            "grasping", "pushing", "insertion", "assembly",
            "polishing", "welding"
        ],
        "legged": [
            "quadruped_locomotion", "walking", "balancing", "stepping_over"
        ],
        "gripper": ["grasping", "pinching"],
        "mobile_base": ["navigation", "obstacle_avoidance"],
        "generic": ["motion"],
    }.get(robot_type, ["motion"])

    # Joint names organized by type
    movable_joints = [
        j["name"] for j in urdf_info["joints"]
        if j["type"] in ["revolute", "prismatic"]
    ]

    # Build e_urdf structure
    e_urdf = {
        "embodiment_id": f"{urdf_info['name'].lower().replace(' ', '_')}_v1",
        "embodiment_name": urdf_info["name"].replace("_", " ").title(),
        "version": "1.0.0",
        "meta": {
            "manufacturer": "Unknown",
            "model": urdf_info["name"],
            "description": f"{robot_type.replace('_', ' ').title()} robot with {urdf_info['dof']} DOF",
            "tags": [robot_type, f"{urdf_info['dof']}-dof"],
            "difficulty": "intermediate" if urdf_info["dof"] < 10 else "advanced",
        },
        "kinematics": {
            "dof": urdf_info["dof"],
            "joint_topology": "serial" if robot_type == "manipulator" else "tree",
        },
        "joints": {
            "names": movable_joints,
            "limits": {
                "position_rad": {
                    name: [limits["lower"], limits["upper"]]
                    for name, limits in urdf_info["joint_limits"].items()
                    if limits["type"] in ["revolute", "prismatic"]
                },
                "torque_nm": {
                    name: limits["effort"]
                    for name, limits in urdf_info["joint_limits"].items()
                },
                "velocity_rad_s": {
                    name: limits["velocity"]
                    for name, limits in urdf_info["joint_limits"].items()
                },
            },
        },
        "semantics": {
            "robot_type": robot_type,
            "affordances": affordances,
            "typical_payload_kg": 2.0 if robot_type == "manipulator" else None,
        },
        "observation_space": {
            "proprioception": {
                "joint_positions": True,
                "joint_velocities": True,
            },
        },
        "action_space": {
            "control_modes": ["joint_position", "joint_velocity"],
            "default_control_mode": "joint_position",
        },
        "physical_firewall": {
            "engine": "mujoco",
            "validation_level": "dynamic_stability",
            "mjlab_validation_required": True,
            "max_simulation_horizon_sec": 2.0,
            "speed_up_factor": 100,
            "constraints": {
                "self_collision": True,
                "environment_collision": True,
                "joint_position_limits": True,
                "joint_velocity_limits": True,
                "joint_torque_limits": True,
                "zmp_stability_check": robot_type in ["humanoid", "legged"],
                "balance_check": robot_type in ["humanoid", "legged"],
            },
            "safety_margins": {
                "joint_position": 0.05,
                "joint_velocity": 0.1,
                "joint_torque": 0.1,
            },
        },
        "mcp_server_config": {
            "tools": [
                "verify_action_safety",
                "get_model_info",
                "get_joint_limits",
            ],
        },
    }

    return e_urdf


def generate_system_prompt(robot_name: str, robot_type: str, dof: int) -> str:
    """Generate system prompt for the robot."""

    prompts = {
        "humanoid": f"""# System Prompt: {robot_name} Humanoid Robot

## Identity

You are a {robot_name} humanoid robot with {dof} degrees of freedom.

## Core Capabilities
- **Locomotion**: Walking, standing, balancing
- **Manipulation**: Grasping and manipulation with arms
- **Interaction**: Human-like gestures and movements

## Safety-First Mindset

⚠️ **CRITICAL**: Balance is your primary concern!

### The Golden Rules
1. **Maintain Balance**: ZMP must stay within support polygon
2. **Foot Contact**: At least one foot must maintain ground contact
3. **Joint Limits**: Respect all joint position and torque limits
4. **Stability**: Check balance stability before every motion

## Decision Flow

```
User Request
    ↓
Analyze: Static or dynamic action?
    ↓
Validate: Collision + Balance checks
    ↓
Execute: Only if all checks pass
```

## Available Tools
- `verify_action_safety`: Collision and joint limit validation
- `check_balance_stability`: Humanoid-specific balance check
- `get_model_info`: Get kinematic parameters

Always validate balance before executing motion!
""",
        "manipulator": f"""# System Prompt: {robot_name} Robotic Arm

## Identity

You are a {robot_name} robotic manipulator with {dof} degrees of freedom.

## Core Capabilities
- **Grasping**: Pick and place operations
- **Assembly**: Part insertion and joining
- **Processing**: Polishing, welding, dispensing

## Safety-First Mindset

⚠️ **CRITICAL**: Always validate trajectories before execution!

### Key Safety Points
1. **Joint Limits**: Respect position, velocity, and torque limits
2. **Collision Avoidance**: Check for self and environment collisions
3. **Payload**: Never exceed maximum payload capacity
4. **Speed**: Use appropriate velocities for the task

## Decision Flow

```
User Request
    ↓
Generate trajectory
    ↓
Validate: verify_action_safety()
    ↓
Execute: Only if SAFE
```

## Available Tools
- `verify_action_safety`: Validate trajectories before execution
- `get_model_info`: Get joint limits and kinematics
- `simulate_trajectory`: Test multi-point paths

Always use safety tools before real execution!
""",
    }

    return prompts.get(robot_type, f"""# System Prompt: {robot_name}

You are a {robot_name} robot with {dof} degrees of freedom.

## Safety
Always validate actions before execution using the safety tools.
""")


def generate_tools_usage_prompt(robot_type: str) -> str:
    """Generate tools usage prompt."""

    base_content = """# MCP Tool Usage Guide

## Tool: `verify_action_safety`

**Purpose**: Validate trajectory before execution.

### Parameters
- `current_joints`: Current joint positions
- `target_joints`: Target joint positions
- `duration_sec`: Simulation duration

### Usage
```python
result = verify_action_safety(
    current_joints=current,
    target_joints=target,
    duration_sec=2.0
)

if "[SAFE]" in result:
    execute(target)
```

## Tool: `get_model_info`

**Purpose**: Get robot kinematic parameters.

### Usage
```python
info = get_model_info()
print(f"DOF: {info['nq']}")
```
"""

    if robot_type in ["humanoid", "legged"]:
        base_content += """
## Tool: `check_balance_stability`

**Purpose**: Humanoid-specific balance validation.

### Parameters
- `proposed_joints`: Target configuration
- `support_phase`: "double_support", "left_single", or "right_single"

### Usage
```python
balance = check_balance_stability(
    proposed_joints=target,
    support_phase="double_support"
)

if "[BALANCE OK]" in balance:
    execute(target)
```
"""

    return base_content


def create_asset_bundle(
    urdf_path: Path,
    output_dir: Path,
    sdk_docs_path: Path | None = None,
) -> None:
    """Create complete e-URDF asset bundle."""

    print(f"📁 Creating asset bundle in: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create prompts directory
    prompts_dir = output_dir / "prompts"
    prompts_dir.mkdir(exist_ok=True)

    # Parse URDF
    print(f"🔍 Parsing URDF: {urdf_path}")
    urdf_info = parse_urdf(urdf_path)
    print(f"   Found: {urdf_info['dof']} DOF, {len(urdf_info['joints'])} joints")

    # Infer robot type
    robot_type = infer_robot_type(urdf_info)
    print(f"🤖 Detected robot type: {robot_type}")

    # Generate e_urdf.json
    print("📝 Generating e_urdf.json...")
    e_urdf = generate_e_urdf(urdf_info, robot_type)

    e_urdf_path = output_dir / "e_urdf.json"
    with open(e_urdf_path, "w") as f:
        json.dump(e_urdf, f, indent=2)
    print(f"   Saved: {e_urdf_path}")

    # Create model.xml reference
    print("🔗 Creating model.xml reference...")
    model_xml = f"""<mujoco model="{urdf_info['name']}_reference">
  <!-- Reference to converted MJCF model -->
  <!-- Convert URDF to MJCF using: mujoco.compile(urdf_path) -->
  <compiler meshdir="./meshes" texturedir="./textures"/>
</mujoco>
"""
    model_path = output_dir / "model.xml"
    with open(model_path, "w") as f:
        f.write(model_xml)
    print(f"   Saved: {model_path}")

    # Generate system prompt
    print("💬 Generating system prompt...")
    system_prompt = generate_system_prompt(
        urdf_info["name"].replace("_", " ").title(),
        robot_type,
        urdf_info["dof"],
    )
    system_path = prompts_dir / "system.md"
    with open(system_path, "w") as f:
        f.write(system_prompt)
    print(f"   Saved: {system_path}")

    # Generate tools usage
    print("🛠️  Generating tools usage guide...")
    tools_prompt = generate_tools_usage_prompt(robot_type)
    tools_path = prompts_dir / "tools_usage.md"
    with open(tools_path, "w") as f:
        f.write(tools_prompt)
    print(f"   Saved: {tools_path}")

    # Handle SDK docs if provided
    if sdk_docs_path:
        print(f"📄 Processing SDK documentation: {sdk_docs_path}")
        # Placeholder for LLM-based extraction
        print("   ⚠️  SDK doc extraction requires LLM integration")
        print("   Manual review of generated prompts recommended")

    print(f"\n✅ Asset bundle created successfully!")
    print(f"\nNext steps:")
    print(f"  1. Review {e_urdf_path}")
    print(f"  2. Convert URDF to MJCF: python -c \"import mujoco; mujoco.compile('{urdf_path}', '{output_dir}/model.xml')\"")
    print(f"  3. Test with mjlab-mcp-server")


def main():
    parser = argparse.ArgumentParser(
        description="Convert robot SDK/URDF to e-URDF asset bundle"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate e-URDF asset bundle")
    gen_parser.add_argument(
        "--urdf",
        type=Path,
        required=True,
        help="Path to URDF file",
    )
    gen_parser.add_argument(
        "--sdk_docs",
        type=Path,
        help="Path to SDK documentation (PDF or text)",
    )
    gen_parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output directory for asset bundle",
    )

    # Info command
    info_parser = subparsers.add_parser("info", help="Show URDF information")
    info_parser.add_argument("--urdf", type=Path, required=True, help="Path to URDF file")

    args = parser.parse_args()

    if args.command == "generate":
        if not args.urdf.exists():
            print(f"Error: URDF file not found: {args.urdf}")
            sys.exit(1)

        if args.sdk_docs and not args.sdk_docs.exists():
            print(f"Warning: SDK docs not found: {args.sdk_docs}")
            args.sdk_docs = None

        create_asset_bundle(args.urdf, args.output, args.sdk_docs)

    elif args.command == "info":
        if not args.urdf.exists():
            print(f"Error: URDF file not found: {args.urdf}")
            sys.exit(1)

        urdf_info = parse_urdf(args.urdf)
        robot_type = infer_robot_type(urdf_info)

        print(f"\nRobot: {urdf_info['name']}")
        print(f"Type: {robot_type}")
        print(f"DOF: {urdf_info['dof']}")
        print(f"Joints: {len(urdf_info['joints'])}")
        print(f"Links: {len(urdf_info['links'])}")
        print(f"\nMovable Joints:")
        for name, limits in urdf_info["joint_limits"].items():
            print(f"  - {name}: [{limits['lower']:.2f}, {limits['upper']:.2f}] rad")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
