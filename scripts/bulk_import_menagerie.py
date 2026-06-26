#!/usr/bin/env python3
"""Bulk Import Script: Generate skeleton e-URDF bundles from MuJoCo Menagerie.

This script creates basic e_urdf.json configurations for all robots in menagerie,
which can be refined later with full semantic descriptions and prompts.

Usage:
    python bulk_import_menagerie.py /path/to/mujoco_menagerie
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


def infer_robot_type(robot_name: str, xml_path: Path) -> str:
    """Infer robot type from name and XML structure."""
    name_lower = robot_name.lower()

    # Keywords mapping
    if any(k in name_lower for k in ["humanoid", "g1", "h1", "adam", "op3", "talos"]):
        return "humanoid"
    elif any(k in name_lower for k in ["arm", "panda", "iiwa", "ur5", "ur10", "franka", "sawyer", "gen3", "rizon", "piper", "arx"]):
        return "manipulator"
    elif any(k in name_lower for k in ["quadruped", "anymal", "spot", "barkour", "go1", "go2", "a1", "cassie", "so101"]):
        return "quadruped"
    elif any(k in name_lower for k in ["hand", "shadow", "leap", "tetheria", "2f85", "robotiq"]):
        return "gripper"
    elif any(k in name_lower for k in ["drone", "crazyflie", "skydio", "x2"]):
        return "aerial"
    elif any(k in name_lower for k in ["mobile", "stretch", "tiago", "tidybot", "toddlerbot"]):
        return "mobile_manipulator"
    elif "biped" in name_lower or "cassie" in name_lower:
        return "biped"

    # Try to infer from XML structure
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        has_legs = any("leg" in j.get("name", "").lower() for j in root.findall(".//joint"))
        has_arms = any(any(x in j.get("name", "").lower() for x in ["arm", "shoulder", "elbow"]) for j in root.findall(".//joint"))

        if has_legs and has_arms:
            return "humanoid"
        elif has_legs:
            return "legged"
        elif has_arms:
            return "manipulator"
    except:
        pass

    return "generic"


def count_dofs(xml_path: Path) -> int:
    """Count degrees of freedom from XML."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        return len([j for j in root.findall(".//joint") if j.get("type") in ["revolute", "prismatic", "continuous"]])
    except:
        return 0


def generate_skeleton_e_urdf(robot_id: str, robot_type: str, dof: int, xml_file: str) -> dict:
    """Generate a skeleton e_urdf.json configuration."""
    # Base affordances by type
    affordances_by_type = {
        "humanoid": ["walking", "standing", "balancing", "reaching", "grasping", "gesticulation"],
        "manipulator": ["grasping", "pushing", "insertion", "assembly", "polishing", "welding"],
        "quadruped": ["quadruped_locomotion", "walking", "trotting", "balancing", "stepping_over"],
        "gripper": ["grasping", "pinching", "holding"],
        "aerial": ["flight", "hovering", "navigation", "aerial_manipulation"],
        "mobile_manipulator": ["navigation", "grasping", "manipulation", "delivery"],
        "biped": ["bipedal_locomotion", "walking", "balancing"],
        "legged": ["locomotion", "walking", "balancing"],
        "generic": ["motion"],
    }

    # Default descriptions by type
    descriptions_by_type = {
        "humanoid": f"{robot_id.replace('_', ' ').title()} - a humanoid robot designed for versatile tasks and human interaction.",
        "manipulator": f"{robot_id.replace('_', ' ').title()} - a robotic manipulator arm for precise manipulation tasks.",
        "quadruped": f"{robot_id.replace('_', ' ').title()} - a quadruped robot designed for agile locomotion over varied terrain.",
        "gripper": f"{robot_id.replace('_', ' ').title()} - a robotic end-effector for grasping and manipulation.",
        "aerial": f"{robot_id.replace('_', ' ').title()} - an aerial drone for flight and aerial operations.",
        "mobile_manipulator": f"{robot_id.replace('_', ' ').title()} - a mobile robot with manipulation capabilities.",
        "biped": f"{robot_id.replace('_', ' ').title()} - a bipedal robot for dynamic walking and balancing.",
        "legged": f"{robot_id.replace('_', ' ').title()} - a legged robot for locomotion.",
        "generic": f"{robot_id.replace('_', ' ').title()} - a robotic system.",
    }

    # Safety checks by type
    zmp_check = robot_type in ["humanoid", "biped", "legged"]
    balance_check = robot_type in ["humanoid", "biped", "legged", "quadruped"]

    return {
        "embodiment_id": f"{robot_id}_v1",
        "embodiment_name": robot_id.replace("_", " ").title(),
        "version": "0.1.0-skeleton",
        "meta": {
            "manufacturer": "Unknown",
            "model": robot_id,
            "description": descriptions_by_type.get(robot_type, descriptions_by_type["generic"]),
            "tags": [robot_type, f"{dof}-dof", "menagerie-import"],
            "difficulty": "intermediate" if dof < 15 else "advanced",
            "imported_from": "mujoco_menagerie",
            "status": "skeleton",
            "note": "This is a skeleton configuration. Full semantic description and prompts needed."
        },
        "kinematics": {
            "dof": dof,
            "joint_topology": "tree" if robot_type in ["humanoid", "quadruped"] else "serial",
            "workspace_type": "omnidirectional" if robot_type in ["humanoid", "quadruped", "aerial"] else "cylindrical"
        },
        "semantics": {
            "robot_type": robot_type,
            "affordances": affordances_by_type.get(robot_type, affordances_by_type["generic"]),
            "difficulty": "advanced" if dof > 20 else "intermediate"
        },
        "observation_space": {
            "proprioception": {
                "joint_positions": True,
                "joint_velocities": True,
                "joint_torques": True
            }
        },
        "action_space": {
            "control_modes": ["joint_position", "joint_velocity"],
            "default_control_mode": "joint_position"
        },
        "physical_firewall": {
            "engine": "mujoco",
            "validation_level": "dynamic_stability",
            "mjlab_validation_required": True,
            "max_simulation_horizon_sec": 2.0,
            "speed_up_factor": 100,
            "constraints": {
                "self_collision": robot_type in ["humanoid", "quadruped"],
                "environment_collision": True,
                "joint_position_limits": True,
                "joint_velocity_limits": True,
                "joint_torque_limits": True,
                "zmp_stability_check": zmp_check,
                "balance_check": balance_check
            },
            "safety_margins": {
                "joint_position": 0.05,
                "joint_velocity": 0.1,
                "joint_torque": 0.1
            }
        },
        "mcp_server_config": {
            "tools": ["verify_action_safety", "get_model_info", "get_joint_limits"],
            "resources": [f"e_urdf://{robot_id}/config"]
        },
        "_todo": [
            "Add detailed joint limits from Menagerie model",
            "Add manufacturer information",
            "Write system.md prompt",
            "Write tools_usage.md guide",
            "Add SDK mappings",
            "Test with mjlab-mcp-server"
        ]
    }


def create_skeleton_bundle(robot_id: str, menagerie_path: Path, output_base: Path) -> bool:
    """Create a skeleton e-URDF bundle for a robot."""
    robot_dir = menagerie_path / robot_id
    if not robot_dir.is_dir():
        return False

    # Find XML file
    xml_files = list(robot_dir.glob("*.xml"))
    if not xml_files:
        return False

    xml_file = xml_files[0]

    # Infer type and DOF
    robot_type = infer_robot_type(robot_id, xml_file)
    dof = count_dofs(xml_file)

    # Create output directory
    output_dir = output_base / robot_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate e_urdf.json
    e_urdf = generate_skeleton_e_urdf(robot_id, robot_type, dof, xml_file.name)
    with open(output_dir / "e_urdf.json", "w") as f:
        json.dump(e_urdf, f, indent=2)

    # Create model.xml reference
    model_xml = f"""<mujoco model="{robot_id}_reference">
  <!-- Reference to MuJoCo Menagerie model -->
  <include file="../../../../mujoco_menagerie/{robot_id}/{xml_file.name}"/>
</mujoco>
"""
    with open(output_dir / "model.xml", "w") as f:
        f.write(model_xml)

    return True


def main():
    parser = argparse.ArgumentParser(description="Bulk import Menagerie robots to e-URDF-Zoo")
    parser.add_argument("menagerie_path", type=Path, help="Path to mujoco_menagerie")
    parser.add_argument("--output", "-o", type=Path, default=Path("robots"), help="Output directory")
    parser.add_argument("--exclude", "-e", nargs="+", default=["test", "realsense_d435i", "assets"],
                        help="Directories to exclude")
    args = parser.parse_args()

    if not args.menagerie_path.exists():
        print(f"Error: Menagerie path not found: {args.menagerie_path}")
        sys.exit(1)

    args.output.mkdir(parents=True, exist_ok=True)

    # Find all robot directories
    robots = []
    for item in args.menagerie_path.iterdir():
        if item.is_dir() and item.name not in args.exclude and not item.name.startswith("."):
            if not item.name.endswith(".cff") and not item.name.endswith(".md"):
                robots.append(item.name)

    print(f"Found {len(robots)} potential robots in Menagerie")
    print("-" * 60)

    success = 0
    failed = 0

    for robot_id in sorted(robots):
        try:
            if create_skeleton_bundle(robot_id, args.menagerie_path, args.output):
                print(f"✓ {robot_id}")
                success += 1
            else:
                print(f"✗ {robot_id} (no XML found)")
                failed += 1
        except Exception as e:
            print(f"✗ {robot_id} (error: {e})")
            failed += 1

    print("-" * 60)
    print(f"Summary: {success} created, {failed} failed")
    print(f"Output: {args.output.absolute()}")


if __name__ == "__main__":
    main()
