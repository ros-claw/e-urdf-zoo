"""e-URDF-Zoo: The Official Device Driver Hub for ROSClaw.

This package provides semantic robot model definitions for AI agents,
combining physical models (MuJoCo) with safety configurations and LLM prompts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .index import AssetIndex
from .loader import AssetLoader
from .models import AssetSummary, EmbodimentAsset, ValidationReport

__version__ = "0.1.0"
__all__ = [
    "AssetIndex",
    "AssetLoader",
    "AssetSummary",
    "EmbodimentAsset",
    "ValidationReport",
    "get_robot_info",
    "get_zoo_path",
    "list_robots",
    "load_embodiment",
    "search_robots",
]


def get_zoo_path() -> Path:
    """Get the path to the e-URDF-Zoo robots directory."""
    return AssetLoader._default_zoo_path()


def list_robots(category: str | None = None) -> list[str]:
    """List all available robot embodiments in the zoo.

    Returns:
        List of asset IDs.

    """
    return [s.id for s in AssetLoader().list_assets(category=category)]


def search_robots(query: str) -> list[str]:
    """Search robot IDs, names, and categories."""
    return [s.id for s in AssetLoader().search_assets(query)]


def load_embodiment(asset_id: str) -> EmbodimentAsset:
    """Load a robot embodiment asset bundle.

    Args:
        asset_id: The asset identifier (e.g., "universal_robots_ur5e"
            or "dexhands/inspire_hand/right")

    Returns:
        EmbodimentAsset object with full configuration

    Raises:
        FileNotFoundError: If asset_id doesn't exist in the zoo
        ValueError: If the bundle is missing required files

    """
    return AssetLoader().load_asset(asset_id)


def get_robot_info(asset_id: str) -> dict[str, Any]:
    """Get quick information about a robot without loading full asset.

    Args:
        asset_id: The asset identifier

    Returns:
        Dictionary with basic robot info

    """
    asset = load_embodiment(asset_id)
    return {
        "id": asset_id,
        "name": asset.name,
        "type": asset.robot_type,
        "category": asset.category,
        "dof": asset.dof,
        "path": str(asset.base_path),
        "is_manifest": asset.is_manifest,
    }
