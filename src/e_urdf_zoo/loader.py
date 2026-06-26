"""Asset loader and resolver for e-URDF-Zoo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .models import AssetSummary, EmbodimentAsset, ValidationReport
from .schemas import (
    CapabilitiesSchema,
    ManifestSchema,
    ProvidersSchema,
    SafetySchema,
    SandboxSchema,
    SemanticSchema,
    ValidationMessage,
    ValidationResult,
    ValidationStatus,
    validate_manifest,
    validate_safety,
)


class AssetLoader:
    """Loads and discovers assets in an e-URDF-Zoo robots directory."""

    def __init__(self, zoo_path: Path | str | None = None):
        if zoo_path is None:
            zoo_path = self._default_zoo_path()
        self.zoo_path = Path(zoo_path)

    # ------------------------------------------------------------------
    # Path discovery
    # ------------------------------------------------------------------
    @staticmethod
    def _default_zoo_path() -> Path:
        import os

        if env_path := os.environ.get("E_URDF_ZOO_PATH"):
            return Path(env_path) / "robots"
        package_dir = Path(__file__).parent.parent.parent
        return package_dir / "robots"

    def _resolve_asset_path(self, asset_id: str) -> Path:
        """Resolve an asset ID to its directory path."""
        if "/" in asset_id:
            candidate = self.zoo_path / asset_id.replace("/", "/")
        else:
            candidate = self.zoo_path / asset_id
        return candidate

    def asset_path(self, asset_id: str) -> Path:
        """Public accessor for resolved asset path."""
        return self._resolve_asset_path(asset_id)

    def discover(self) -> list[tuple[str, Path]]:
        """Discover all assets under the zoo path.

        Returns a list of (asset_id, base_path) tuples. Manifest-driven assets
        take precedence over legacy assets when both are present.
        """
        found: list[tuple[str, Path]] = []
        if not self.zoo_path.exists():
            return found

        for candidate in sorted(self.zoo_path.rglob("*")):
            if not candidate.is_dir():
                continue
            if (candidate / "manifest.yaml").exists():
                rel = candidate.relative_to(self.zoo_path).as_posix()
                found.append((rel, candidate))
            elif (candidate / "e_urdf.json").exists() and candidate.parent == self.zoo_path:
                found.append((candidate.name, candidate))

        return found

    # ------------------------------------------------------------------
    # Load / info
    # ------------------------------------------------------------------
    def load_asset(self, asset_id: str) -> EmbodimentAsset:
        """Load a single asset by ID."""
        path = self._resolve_asset_path(asset_id)
        if not path.exists():
            available = [a for a, _ in self.discover()]
            available_str = "\n  - ".join([""] + available) if available else "\n  (none found)"
            raise FileNotFoundError(
                f"Asset '{asset_id}' not found in e-URDF-Zoo.\n"
                f"Available assets:{available_str}\n"
                f"Zoo path: {self.zoo_path}"
            )
        if not (path / "manifest.yaml").exists() and not (path / "e_urdf.json").exists():
            raise ValueError(f"Invalid asset bundle: no manifest.yaml or e_urdf.json in {path}")
        return EmbodimentAsset(asset_id, path)

    load_embodiment = load_asset  # backwards-compatible alias

    def get_asset_manifest(self, asset_id: str) -> ManifestSchema:
        """Return the manifest schema for a manifest asset."""
        asset = self.load_asset(asset_id)
        if asset.manifest is None:
            raise ValueError(f"Asset '{asset_id}' does not have a manifest.yaml")
        return asset.manifest

    # ------------------------------------------------------------------
    # Listing / search
    # ------------------------------------------------------------------
    def list_assets(self, category: str | None = None) -> list[AssetSummary]:
        """List all assets, optionally filtered by category."""
        summaries: list[AssetSummary] = []
        for asset_id, path in self.discover():
            summary = self._summarize(asset_id, path)
            if category is None or summary.category == category:
                summaries.append(summary)
        return summaries

    def search_assets(self, query: str) -> list[AssetSummary]:
        """Search asset IDs, names, and categories."""
        query_lower = query.lower()
        matches: list[AssetSummary] = []
        for asset_id, path in self.discover():
            summary = self._summarize(asset_id, path)
            haystack = " ".join(
                [
                    summary.id,
                    summary.name,
                    summary.category,
                    " ".join(summary.aliases),
                ]
            ).lower()
            if query_lower in haystack:
                matches.append(summary)
        return matches

    def _summarize(self, asset_id: str, path: Path) -> AssetSummary:
        manifest_path = path / "manifest.yaml"
        if manifest_path.exists():
            try:
                data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
                asset = data.get("asset", {})
                return AssetSummary(
                    id=asset_id,
                    name=asset.get("name", asset_id),
                    category=asset.get("category", "unknown"),
                    path=path,
                    status=asset.get("status", "experimental"),
                    version=asset.get("version", "0.1.0"),
                    is_legacy=False,
                    aliases=list(data.get("aliases", {}).keys()),
                )
            except Exception:  # noqa: BLE001
                pass

        legacy_path = path / "e_urdf.json"
        if legacy_path.exists():
            try:
                data = json.loads(legacy_path.read_text(encoding="utf-8"))
                semantics = data.get("semantics", {})
                return AssetSummary(
                    id=asset_id,
                    name=data.get("embodiment_name", asset_id),
                    category=semantics.get("robot_type", "unknown"),
                    path=path,
                    status=data.get("validation_status", "experimental"),
                    version=data.get("version", "0.1.0"),
                    is_legacy=True,
                    aliases=[],
                )
            except Exception:  # noqa: BLE001
                pass

        return AssetSummary(
            id=asset_id,
            name=asset_id,
            category="unknown",
            path=path,
            is_legacy=False,
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate_asset(self, asset_id: str) -> ValidationReport:
        """Run the full bundle validation for an asset."""
        asset = self.load_asset(asset_id)
        results: dict[str, Any] = {}
        overall = ValidationStatus.PASS

        if asset.is_manifest:
            manifest_result = validate_manifest(asset.base_path / "manifest.yaml")
            results["manifest.yaml"] = manifest_result
            safety_path = asset.base_path / asset.manifest.semantics.safety_file
            results["safety.yaml"] = validate_safety(safety_path)

            cap_path = asset.base_path / asset.manifest.semantics.capabilities_file
            if cap_path.exists():
                results["capabilities.yaml"] = self._validate_capabilities(cap_path)
            else:
                results["capabilities.yaml"] = ValidationResult(
                    status=ValidationStatus.FAIL,
                    messages=[
                        ValidationMessage(
                            level="error",
                            message="capabilities.yaml not found",
                            path=str(cap_path),
                        )
                    ],
                )

            sem_path = asset.base_path / asset.manifest.semantics.semantic_file
            if sem_path.exists():
                results["semantic.yaml"] = self._validate_semantic(sem_path)
            else:
                results["semantic.yaml"] = ValidationResult(
                    status=ValidationStatus.FAIL,
                    messages=[
                        ValidationMessage(
                            level="error",
                            message="semantic.yaml not found",
                            path=str(sem_path),
                        )
                    ],
                )
        else:
            legacy_path = asset.base_path / "e_urdf.json"
            results["e_urdf.json"] = self._validate_legacy(legacy_path)

        messages: list[dict[str, Any]] = []
        for filename, result in results.items():
            if result.status == ValidationStatus.FAIL:
                overall = ValidationStatus.FAIL
            elif (
                result.status == ValidationStatus.PASS_WITH_WARNINGS
                and overall == ValidationStatus.PASS
            ):
                overall = ValidationStatus.PASS_WITH_WARNINGS
            for msg in result.messages:
                messages.append(
                    {
                        "file": filename,
                        "level": msg.level,
                        "message": msg.message,
                        "path": msg.path,
                    }
                )

        return ValidationReport(
            asset_id=asset_id,
            overall=overall.value,
            results=results,
            messages=messages,
        )

    def _validate_capabilities(self, path: Path) -> ValidationResult:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            CapabilitiesSchema.model_validate(data)
            return ValidationResult(status=ValidationStatus.PASS, messages=[])
        except Exception as exc:  # noqa: BLE001
            return ValidationResult(
                status=ValidationStatus.FAIL,
                messages=[
                    ValidationMessage(
                        level="error", message=str(exc), path=str(path)
                    )
                ],
            )

    def _validate_semantic(self, path: Path) -> ValidationResult:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            SemanticSchema.model_validate(data)
            return ValidationResult(status=ValidationStatus.PASS, messages=[])
        except Exception as exc:  # noqa: BLE001
            return ValidationResult(
                status=ValidationStatus.FAIL,
                messages=[
                    ValidationMessage(
                        level="error", message=str(exc), path=str(path)
                    )
                ],
            )

    def _validate_legacy(self, path: Path) -> ValidationResult:
        try:
            json.loads(path.read_text(encoding="utf-8"))
            return ValidationResult(status=ValidationStatus.PASS, messages=[])
        except Exception as exc:  # noqa: BLE001
            return ValidationResult(
                status=ValidationStatus.FAIL,
                messages=[
                    ValidationMessage(
                        level="error", message=str(exc), path=str(path)
                    )
                ],
            )
