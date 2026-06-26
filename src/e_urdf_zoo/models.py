"""Data models for e-URDF-Zoo assets."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .schemas import (
    CapabilitiesSchema,
    ManifestSchema,
    ProvidersSchema,
    SafetySchema,
    SandboxSchema,
    SemanticSchema,
    ValidationResult,
    validate_manifest,
    validate_safety,
)


@dataclass
class AssetSummary:
    """Lightweight summary of an asset for listing and searching."""

    id: str
    name: str
    category: str
    path: Path
    status: str = "experimental"
    version: str = "0.1.0"
    is_legacy: bool = False
    aliases: list[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    """Aggregated validation report for an asset bundle."""

    asset_id: str
    overall: str  # PASS | PASS_WITH_WARNINGS | FAIL
    results: dict[str, ValidationResult] = field(default_factory=dict)
    messages: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "overall": self.overall,
            "results": {
                name: result.to_dict() for name, result in self.results.items()
            },
            "messages": self.messages,
        }


class EmbodimentAsset:
    """Represents a complete robot embodiment asset bundle.

    Supports both the new manifest-driven layout and the legacy ``e_urdf.json``
    + ``model.xml`` layout through the same public API.
    """

    def __init__(self, asset_id: str, base_path: Path):
        self.robot_id = asset_id
        self.asset_id = asset_id
        self.base_path = Path(base_path)
        self._manifest: ManifestSchema | None = None
        self._legacy_config: dict[str, Any] | None = None
        self._semantic: SemanticSchema | None = None
        self._capabilities: CapabilitiesSchema | None = None
        self._safety: SafetySchema | None = None
        self._providers: ProvidersSchema | None = None
        self._sandbox: SandboxSchema | None = None

    # ------------------------------------------------------------------
    # Manifest / legacy detection
    # ------------------------------------------------------------------
    @property
    def is_manifest(self) -> bool:
        """True if this asset uses the new manifest-driven layout."""
        return (self.base_path / "manifest.yaml").exists()

    @property
    def manifest(self) -> ManifestSchema | None:
        """Return the parsed manifest, or None for legacy assets."""
        if self._manifest is None and self.is_manifest:
            path = self.base_path / "manifest.yaml"
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            self._manifest = ManifestSchema.model_validate(data)
        return self._manifest

    @property
    def legacy_config(self) -> dict[str, Any] | None:
        """Return the parsed legacy e_urdf.json, or None for manifest assets."""
        if self._legacy_config is None and not self.is_manifest:
            path = self.base_path / "e_urdf.json"
            if path.exists():
                self._legacy_config = json.loads(path.read_text(encoding="utf-8"))
        return self._legacy_config

    # ------------------------------------------------------------------
    # Backwards-compatible properties
    # ------------------------------------------------------------------
    @property
    def config(self) -> dict[str, Any]:
        """Return a configuration dict compatible with legacy consumers."""
        if self.legacy_config is not None:
            return self.legacy_config
        return self._manifest_as_legacy_config()

    @property
    def model_xml(self) -> Path:
        """Return path to the primary model file."""
        legacy = self.base_path / "model.xml"
        if legacy.exists():
            return legacy
        if self.manifest and self.manifest.model.urdf:
            return self.base_path / self.manifest.model.urdf
        return legacy

    @property
    def model_urdf(self) -> Path | None:
        """Return path to URDF model file for manifest assets."""
        if self.manifest and self.manifest.model.urdf:
            return self.base_path / self.manifest.model.urdf
        return None

    @property
    def system_prompt(self) -> str:
        """Load and return the system prompt."""
        return self._read_prompt("system.md")

    @property
    def tools_usage(self) -> str:
        """Load and return the tools usage guide."""
        return self._read_prompt("tools_usage.md")

    @property
    def safety_prompt(self) -> str:
        """Load and return the safety prompt."""
        return self._read_prompt("safety.md")

    @property
    def name(self) -> str:
        """Return embodiment name."""
        if self.manifest:
            return self.manifest.asset.name
        return self.config.get("embodiment_name", self.asset_id)

    @property
    def robot_type(self) -> str:
        """Return robot type / category."""
        if self.manifest:
            return self.manifest.asset.category
        return self.config.get("semantics", {}).get("robot_type", "unknown")

    @property
    def category(self) -> str:
        """Return asset category."""
        return self.robot_type

    @property
    def dof(self) -> int:
        """Return degrees of freedom."""
        if self.manifest and self.manifest.robot.dof is not None:
            return self.manifest.robot.dof
        return self.config.get("kinematics", {}).get("dof", 0)

    @property
    def status(self) -> str:
        """Return asset validation status."""
        if self.manifest:
            return self.manifest.asset.status
        return self.config.get("validation_status", "experimental")

    @property
    def version(self) -> str:
        """Return asset version."""
        if self.manifest:
            return self.manifest.asset.version
        return self.config.get("version", "0.1.0")

    # ------------------------------------------------------------------
    # New manifest-driven accessors
    # ------------------------------------------------------------------
    @property
    def semantic(self) -> SemanticSchema | None:
        if self._semantic is None and self.manifest:
            path = self.base_path / self.manifest.semantics.semantic_file
            if path.exists():
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                self._semantic = SemanticSchema.model_validate(data)
        return self._semantic

    @property
    def capabilities(self) -> CapabilitiesSchema | None:
        if self._capabilities is None and self.manifest:
            path = self.base_path / self.manifest.semantics.capabilities_file
            if path.exists():
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                self._capabilities = CapabilitiesSchema.model_validate(data)
        return self._capabilities

    @property
    def safety(self) -> SafetySchema | None:
        if self._safety is None and self.manifest:
            path = self.base_path / self.manifest.semantics.safety_file
            if path.exists():
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                self._safety = SafetySchema.model_validate(data)
        return self._safety

    @property
    def providers(self) -> ProvidersSchema | None:
        if self._providers is None and self.manifest:
            path = self.base_path / self.manifest.semantics.providers_file
            if path.exists():
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                self._providers = ProvidersSchema.model_validate(data)
        return self._providers

    @property
    def sandbox(self) -> SandboxSchema | None:
        if self._sandbox is None and self.manifest:
            path = self.base_path / self.manifest.semantics.sandbox_file
            if path.exists():
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                self._sandbox = SandboxSchema.model_validate(data)
        return self._sandbox

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _read_prompt(self, filename: str) -> str:
        prompts_dir = self.base_path / "prompts"
        if self.manifest:
            prompts_dir = self.base_path / self.manifest.semantics.prompts_dir
        path = prompts_dir / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _manifest_as_legacy_config(self) -> dict[str, Any]:
        """Build a legacy-compatible config dict from a manifest asset."""
        if not self.manifest:
            return {}
        manifest = self.manifest
        return {
            "embodiment_id": manifest.asset.id,
            "embodiment_name": manifest.asset.name,
            "version": manifest.asset.version,
            "validation_status": manifest.asset.status,
            "meta": {
                "manufacturer": manifest.asset.vendor,
                "model": manifest.asset.model,
                "description": manifest.asset.description,
            },
            "semantics": {
                "robot_type": manifest.asset.category,
                "affordances": [
                    cap.name for cap in (self.capabilities.capabilities if self.capabilities else [])
                ],
            },
            "kinematics": {
                "dof": manifest.robot.dof or 0,
            },
            "physical_firewall": {
                "engine": "mujoco",
                "validation_level": manifest.quality.validation_status,
                "max_simulation_horizon_sec": 5.0,
                "speed_up_factor": 1.0,
                "constraints": {
                    "real_robot_execution_allowed": manifest.runtime_policy.real_robot_execution_allowed,
                    "sandbox_required": manifest.runtime_policy.sandbox_required,
                },
            },
        }

    def __repr__(self) -> str:
        return f"EmbodimentAsset({self.asset_id}: {self.name}, {self.dof} DOF)"
