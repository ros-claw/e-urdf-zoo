"""Schema for safety.yaml."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GlobalPolicy(BaseModel):
    """Global safety policy switches."""

    model_config = ConfigDict(extra="allow")

    real_robot_execution_allowed: bool = False
    sandbox_required: bool = True
    low_speed_first_run_required: bool = True
    current_limit_required: bool = True
    fault_monitor_required: bool = True
    manual_enable_required_after_validation: bool = True


class Limits(BaseModel):
    """Scaled safety limits."""

    model_config = ConfigDict(extra="allow")

    max_joint_speed_scale: float = 0.2
    max_joint_torque_scale: float = 0.2
    max_position_step_scale: float = 0.1
    require_joint_limit_margin: bool = True
    joint_limit_margin_ratio: float = 0.1


class RuntimeMonitors(BaseModel):
    """Required and recommended runtime monitors."""

    model_config = ConfigDict(extra="allow")

    required: list[str] = Field(default_factory=list)
    recommended: list[str] = Field(default_factory=list)


class TrajectoryPolicy(BaseModel):
    """Trajectory validation policy."""

    model_config = ConfigDict(extra="allow")

    require_sandbox_validation: bool = True
    require_self_collision_check: bool = True
    require_joint_limit_margin: bool = True
    require_contact_margin_for_thumb_index: bool = True
    require_incremental_pose_replay: bool = True


class BlockedAction(BaseModel):
    """An action that is blocked by policy."""

    model_config = ConfigDict(extra="allow")

    id: str
    reason: str


class FirstRealRobotProtocol(BaseModel):
    """Steps required before first real-robot execution."""

    model_config = ConfigDict(extra="allow")

    steps: list[str] = Field(default_factory=list)


class SafetySchema(BaseModel):
    """Top-level safety.yaml schema."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "e_urdf.safety.v1"
    safety_status: str = "experimental"
    global_policy: GlobalPolicy = Field(default_factory=GlobalPolicy)
    limits: Limits = Field(default_factory=Limits)
    runtime_monitors: RuntimeMonitors = Field(default_factory=RuntimeMonitors)
    trajectory_policy: TrajectoryPolicy = Field(default_factory=TrajectoryPolicy)
    blocked_actions: list[BlockedAction] = Field(default_factory=list)
    first_real_robot_protocol: FirstRealRobotProtocol = Field(
        default_factory=FirstRealRobotProtocol
    )
