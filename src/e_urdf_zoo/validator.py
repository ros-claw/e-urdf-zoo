"""High-level asset bundle validator."""

from __future__ import annotations

from pathlib import Path

from .loader import AssetLoader
from .models import ValidationReport


class AssetValidator:
    """Validate e-URDF-Zoo asset bundles."""

    def __init__(self, zoo_path: Path | str | None = None):
        self.loader = AssetLoader(zoo_path)

    def validate(self, asset_id: str) -> ValidationReport:
        """Validate an asset by ID."""
        return self.loader.validate_asset(asset_id)

    def validate_path(self, path: Path | str) -> ValidationReport:
        """Validate a directory directly without discovering it first."""
        path = Path(path)
        if (path / "manifest.yaml").exists():
            asset_id = path.name
            loader = AssetLoader(path.parent)
            return loader.validate_asset(asset_id)
        if (path / "e_urdf.json").exists():
            return ValidationReport(
                asset_id=path.name,
                overall="PASS",
                messages=[],
            )
        return ValidationReport(
            asset_id=str(path),
            overall="FAIL",
            messages=[
                {
                    "level": "error",
                    "message": "No manifest.yaml or e_urdf.json found",
                }
            ],
        )
