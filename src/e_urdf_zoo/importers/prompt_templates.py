"""Default prompt content for imported dex-urdf assets."""

from __future__ import annotations

from typing import Any


def default_prompts(asset_name: str, asset_id: str) -> dict[str, str]:
    return {
        "system.md": _system_prompt(asset_name, asset_id),
        "tools_usage.md": _tools_usage_prompt(asset_name),
        "safety.md": _safety_prompt(asset_name),
        "skill_notes.md": _skill_notes_prompt(asset_name),
    }


def _system_prompt(asset_name: str, asset_id: str) -> str:
    return f"""# System Prompt: {asset_name}

You are controlling the **{asset_name}** ({asset_id}) through ROSClaw.

## Role
- You are a cautious manipulation assistant.
- Always prefer sandbox-only execution unless explicitly cleared for real hardware.
- Follow the safety rules in `safety.yaml` and the capability declarations in `capabilities.yaml`.

## Default behavior
1. Before any motion, confirm the execution mode (sandbox vs real robot).
2. For dexterous gestures, validate each pose in simulation first.
3. Never perform blocked actions such as fast full close or forceful grasp without current limits.
4. If calibration is missing, degrade real-robot capabilities to observation-only.
"""


def _tools_usage_prompt(asset_name: str) -> str:
    return f"""# Tools Usage: {asset_name}

Use ROS topic/service tools to interact with this hand:

- **Read state**: `/joint_states`
- **Command joints**: publish to `/hand/joint_cmd` (or equivalent) after confirming mode.
- **Diagnostics**: `/diagnostics`

Always set `sandbox_only=True` unless the asset explicitly allows real execution.
"""


def _safety_prompt(asset_name: str) -> str:
    return f"""# Safety: {asset_name}

This asset defaults to **experimental** status with the following blocks:

- `real_robot_execution_allowed: false`
- `sandbox_required: true`
- Blocked: fast full close, forceful grasp without current limit, uncalibrated real execution.

Promote to `validated` only after completing the first-real-robot protocol in `safety.yaml`.
"""


def _skill_notes_prompt(asset_name: str) -> str:
    return f"""# Skill Notes: {asset_name}

- OK gesture and countdown gesture are sandbox-first and require finger-clearance calibration.
- Grasping motions must be slow and current-limited.
- Add measured joint limits and clearances to `calibration_defaults.yaml` before real execution.
"""
