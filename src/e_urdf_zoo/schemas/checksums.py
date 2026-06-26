"""Schema for checksums.json."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ChecksumsSchema(BaseModel):
    """Top-level checksums.json schema."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "e_urdf.checksums.v1"
    generated_at: str = ""
    algorithm: str = "sha256"
    files: dict[str, str] = Field(default_factory=dict)
