"""Schema for capabilities.yaml."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Capability(BaseModel):
    """A declared capability."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    scope: str = "manipulation"
    risk: str = "medium"
    body_parts: list[str] = Field(default_factory=list)
    sandbox_required: bool = True
    real_robot_execution_allowed: bool = False
    required_runtime_monitors: list[str] = Field(default_factory=list)
    required_calibration: list[str] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)


class ForbiddenCapability(BaseModel):
    """A capability that is explicitly forbidden."""

    model_config = ConfigDict(extra="allow")

    id: str
    description: str
    reason: str = ""
    severity: str = "critical"
    enforcement: dict[str, bool] = Field(default_factory=dict)


class CapabilitiesSchema(BaseModel):
    """Top-level capabilities.yaml schema."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "e_urdf.capabilities.v1"
    capabilities: list[Capability] = Field(default_factory=list)
    forbidden_capabilities: list[ForbiddenCapability] = Field(default_factory=list)
