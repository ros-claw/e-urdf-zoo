"""Schema for providers.yaml."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProviderInterface(BaseModel):
    """A provider interface definition."""

    model_config = ConfigDict(extra="allow")

    id: str
    type: str
    roles: list[str] = Field(default_factory=list)
    topic: str | None = None
    required: bool = False


class ProviderCategory(BaseModel):
    """A category of provider interfaces."""

    model_config = ConfigDict(extra="allow")

    required: list[ProviderInterface] = Field(default_factory=list)
    optional: list[ProviderInterface] = Field(default_factory=list)


class McpServerRecommendation(BaseModel):
    """Recommended MCP server for this asset."""

    model_config = ConfigDict(extra="allow")

    id: str
    applies_to: list[str] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)


class ProvidersSchema(BaseModel):
    """Top-level providers.yaml schema."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "e_urdf.providers.v1"
    provider_interfaces: dict[str, ProviderCategory] = Field(default_factory=dict)
    mcp: dict[str, list[McpServerRecommendation]] = Field(default_factory=dict)
