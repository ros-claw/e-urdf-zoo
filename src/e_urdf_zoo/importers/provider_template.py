"""Default providers.yaml content for imported dex-urdf assets."""

from __future__ import annotations

from typing import Any


def default_providers(asset_name: str) -> dict[str, Any]:
    return {
        "schema_version": "e_urdf.providers.v1",
        "interfaces": [
            {
                "id": "joint_state",
                "category": "sensor",
                "description": "Joint positions, velocities, and efforts",
                "required": True,
                "ros1_topic": "/joint_states",
                "ros2_topic": "/joint_states",
            },
            {
                "id": "command",
                "category": "actuator",
                "description": "Position/effort commands to hand joints",
                "required": True,
                "ros1_topic": "/hand/joint_cmd",
                "ros2_topic": "/hand/joint_cmd",
            },
            {
                "id": "diagnostics",
                "category": "diagnostic",
                "description": "Current, temperature, fault diagnostics",
                "required": True,
                "ros1_topic": "/diagnostics",
                "ros2_topic": "/diagnostics",
            },
        ],
        "recommended_mcp_servers": [
            {
                "name": "ros-mcp-server",
                "purpose": "Bridge ROS topics/services to the agent",
                "required_for_real_robot": True,
            }
        ],
    }
