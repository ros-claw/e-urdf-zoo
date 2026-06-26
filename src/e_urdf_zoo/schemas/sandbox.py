"""Schema for sandbox.yaml."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EngineConfig(BaseModel):
    """Per-engine sandbox support status."""

    model_config = ConfigDict(extra="allow")

    supported: bool = False
    model_path: str | None = None
    status: str = "not_converted"


class TestPose(BaseModel):
    """A default test pose."""

    model_config = ConfigDict(extra="allow")

    id: str
    description: str = ""


class SandboxSchema(BaseModel):
    """Top-level sandbox.yaml schema."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "e_urdf.sandbox.v1"
    engines: dict[str, EngineConfig] = Field(default_factory=dict)
    validation: dict[str, list[str]] = Field(default_factory=dict)
    default_test_poses: list[TestPose] = Field(default_factory=list)
