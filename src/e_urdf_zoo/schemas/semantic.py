"""Schema for semantic.yaml."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FrameInfo(BaseModel):
    """Named frames of interest."""

    model_config = ConfigDict(extra="allow")

    root: str | None = None
    mounting: str | None = None
    tcp: str | None = None


class SemanticGroup(BaseModel):
    """A semantic group of links/joints (finger, palm, arm, etc.)."""

    model_config = ConfigDict(extra="allow")

    type: str
    links: list[str] = Field(default_factory=list)
    joints: list[str] = Field(default_factory=list)
    side: str | None = None
    roles: list[str] = Field(default_factory=list)
    source: str = "heuristic"
    confidence: float = 0.6
    warnings: list[str] = Field(default_factory=list)


class ContactSurface(BaseModel):
    """Contact surface definition."""

    model_config = ConfigDict(extra="allow")

    group_type: str = "unknown"
    links: list[str] = Field(default_factory=list)
    source: str = "heuristic"


class MountingInfo(BaseModel):
    """Mounting compatibility."""

    model_config = ConfigDict(extra="allow")

    compatible_mounts: list[str] = Field(default_factory=list)
    required_adapter: str | None = None


class SemanticSchema(BaseModel):
    """Top-level semantic.yaml schema."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "e_urdf.semantic.v1"
    identity: dict[str, str] = Field(default_factory=dict)
    frames: FrameInfo = Field(default_factory=FrameInfo)
    groups: dict[str, SemanticGroup] = Field(default_factory=dict)
    contact_surfaces: dict[str, ContactSurface] = Field(default_factory=dict)
    mounting: MountingInfo = Field(default_factory=MountingInfo)
    notes: list[str] = Field(default_factory=list)
