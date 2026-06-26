"""Default capabilities.yaml content for imported dex-urdf assets."""

from __future__ import annotations

from typing import Any


def default_capabilities(category: str = "dexterous_hand") -> dict[str, Any]:
    """Return conservative capabilities for an imported hand/gripper."""
    if category in {"dexterous_hand", "hand"}:
        capabilities = [
            {
                "id": "open_hand",
                "name": "Open Hand",
                "scope": "manipulation",
                "risk": "low",
                "sandbox_required": True,
                "real_robot_execution_allowed": False,
            },
            {
                "id": "close_hand_slow",
                "name": "Close Hand Slowly",
                "scope": "manipulation",
                "risk": "medium",
                "sandbox_required": True,
                "real_robot_execution_allowed": False,
            },
            {
                "id": "ok_gesture",
                "name": "OK Gesture",
                "scope": "gesture",
                "risk": "medium",
                "sandbox_required": True,
                "real_robot_execution_allowed": False,
                "required_calibration": ["finger_clearance"],
            },
            {
                "id": "countdown_gesture",
                "name": "Countdown Gesture",
                "scope": "gesture",
                "risk": "medium",
                "sandbox_required": True,
                "real_robot_execution_allowed": False,
                "required_calibration": ["finger_clearance"],
            },
        ]
    else:
        capabilities = [
            {
                "id": "open_gripper",
                "name": "Open Gripper",
                "scope": "manipulation",
                "risk": "low",
                "sandbox_required": True,
                "real_robot_execution_allowed": False,
            },
            {
                "id": "close_gripper_slow",
                "name": "Close Gripper Slowly",
                "scope": "manipulation",
                "risk": "medium",
                "sandbox_required": True,
                "real_robot_execution_allowed": False,
            },
        ]

    forbidden = [
        {
            "id": "forceful_grasp_without_current_limit",
            "description": "Forceful grasping without active current/torque limit",
            "reason": "Can damage the hand and grasped object",
            "severity": "critical",
            "enforcement": {
                "policy_block": True,
                "sandbox_block": True,
                "real_robot_block": True,
            },
        },
        {
            "id": "fast_full_close",
            "description": "Close all fingers/joints to maximum at high speed",
            "reason": "Risk of collision and motor overload",
            "severity": "critical",
            "enforcement": {
                "policy_block": True,
                "sandbox_block": True,
                "real_robot_block": True,
            },
        },
    ]

    return {
        "schema_version": "e_urdf.capabilities.v1",
        "capabilities": capabilities,
        "forbidden_capabilities": forbidden,
    }
