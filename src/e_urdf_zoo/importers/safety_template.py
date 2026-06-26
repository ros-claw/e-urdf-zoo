"""Default safety.yaml content for imported dex-urdf assets."""

from __future__ import annotations

from typing import Any


def default_safety(asset_name: str) -> dict[str, Any]:
    """Return a conservative safety policy for a third-party hand/gripper."""
    return {
        "schema_version": "e_urdf.safety.v1",
        "safety_status": "experimental",
        "global_policy": {
            "real_robot_execution_allowed": False,
            "sandbox_required": True,
            "provider_required": True,
            "calibration_required": True,
            "low_speed_first_run_required": True,
            "fault_monitor_required": True,
        },
        "limits": {
            "max_joint_velocity_rad_s": 1.0,
            "max_joint_acceleration_rad_s2": 2.0,
            "max_current_a": 1.0,
            "max_force_n": 10.0,
        },
        "runtime_monitors": {
            "watch_current": True,
            "watch_position_bounds": True,
            "watch_velocity_bounds": True,
            "watch_force": True,
            "emergency_stop_on_fault": True,
        },
        "trajectory_policy": {
            "require_sandbox_first": True,
            "require_low_speed_first": True,
            "require_per_pose_validation": True,
            "max_waypoints_without_human_confirmation": 1,
        },
        "blocked_actions": [
            {
                "id": "fast_full_close",
                "reason": "Risk of motor overload and collision damage",
                "scope": ["real_robot", "sandbox"],
            },
            {
                "id": "forceful_grasp_without_current_limit",
                "reason": "Grasping without active current/torque limit is forbidden",
                "scope": ["real_robot", "sandbox"],
            },
            {
                "id": "uncalibrated_real_execution",
                "reason": "Real robot execution requires clearance calibration",
                "scope": ["real_robot"],
            },
        ],
        "first_real_robot_protocol": {
            "required": True,
            "steps": [
                "Complete sandbox-only validation",
                "Upload clearance calibration",
                "Run low-speed range-of-motion check",
                "Enable current/torque monitors",
                "Human-in-the-loop confirmation per pose",
            ],
        },
    }
