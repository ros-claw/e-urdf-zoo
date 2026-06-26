"""Tests for the asset loader and index."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from e_urdf_zoo.index import AssetIndex
from e_urdf_zoo.loader import AssetLoader
from e_urdf_zoo.schemas import ValidationStatus


def _write_manifest(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def _write_safety(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def _write_legacy(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def sample_zoo(tmp_path: Path) -> Path:
    zoo = tmp_path / "robots"

    # New manifest asset
    manifest_dir = zoo / "dexhands" / "inspire_hand" / "right"
    _write_manifest(
        manifest_dir / "manifest.yaml",
        {
            "schema_version": "e_urdf.asset.v1",
            "asset": {
                "id": "dexhands/inspire_hand/right",
                "name": "Inspire Hand Right",
                "category": "dexterous_hand",
                "vendor": "Inspire Robots",
                "model": "inspire_hand",
                "variant": "right",
            },
            "robot": {"dof": 11},
            "runtime_policy": {
                "real_robot_execution_allowed": False,
                "sandbox_required": True,
            },
        },
    )
    _write_safety(
        manifest_dir / "safety.yaml",
        {
            "schema_version": "e_urdf.safety.v1",
            "global_policy": {
                "real_robot_execution_allowed": False,
                "sandbox_required": True,
            },
            "blocked_actions": [
                {"id": "fast_full_close", "reason": "overload risk"}
            ],
        },
    )
    (manifest_dir / "capabilities.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "e_urdf.capabilities.v1",
                "capabilities": [],
                "forbidden_capabilities": [],
            }
        ),
        encoding="utf-8",
    )
    (manifest_dir / "semantic.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "e_urdf.semantic.v1",
                "groups": {},
                "frames": {},
            }
        ),
        encoding="utf-8",
    )

    # Legacy asset
    legacy_dir = zoo / "universal_robots_ur5e"
    _write_legacy(
        legacy_dir / "e_urdf.json",
        {
            "embodiment_id": "universal_robots_ur5e",
            "embodiment_name": "UR5e",
            "version": "1.0.0",
            "validation_status": "validated",
            "semantics": {"robot_type": "arm"},
            "kinematics": {"dof": 6},
            "meta": {"manufacturer": "Universal Robots", "model": "UR5e"},
        },
    )

    return zoo


def test_loader_discovers_manifest_and_legacy(sample_zoo: Path):
    loader = AssetLoader(sample_zoo)
    discovered = loader.discover()
    ids = {a for a, _ in discovered}
    assert "dexhands/inspire_hand/right" in ids
    assert "universal_robots_ur5e" in ids


def test_loader_lists_assets_by_category(sample_zoo: Path):
    loader = AssetLoader(sample_zoo)
    hands = loader.list_assets(category="dexterous_hand")
    assert len(hands) == 1
    assert hands[0].id == "dexhands/inspire_hand/right"

    arms = loader.list_assets(category="arm")
    assert len(arms) == 1
    assert arms[0].is_legacy


def test_loader_loads_manifest_asset(sample_zoo: Path):
    loader = AssetLoader(sample_zoo)
    asset = loader.load_asset("dexhands/inspire_hand/right")
    assert asset.is_manifest
    assert asset.name == "Inspire Hand Right"
    assert asset.dof == 11
    assert asset.manifest is not None
    assert asset.manifest.asset.category == "dexterous_hand"


def test_loader_loads_legacy_asset(sample_zoo: Path):
    loader = AssetLoader(sample_zoo)
    asset = loader.load_asset("universal_robots_ur5e")
    assert not asset.is_manifest
    assert asset.name == "UR5e"
    assert asset.dof == 6
    assert asset.config["embodiment_id"] == "universal_robots_ur5e"


def test_loader_search(sample_zoo: Path):
    loader = AssetLoader(sample_zoo)
    matches = loader.search_assets("inspire")
    assert any(m.id == "dexhands/inspire_hand/right" for m in matches)


def test_loader_validate_manifest_asset(sample_zoo: Path):
    loader = AssetLoader(sample_zoo)
    report = loader.validate_asset("dexhands/inspire_hand/right")
    assert report.overall == ValidationStatus.PASS.value
    assert "manifest.yaml" in report.results
    assert "safety.yaml" in report.results


def test_loader_validate_legacy_asset(sample_zoo: Path):
    loader = AssetLoader(sample_zoo)
    report = loader.validate_asset("universal_robots_ur5e")
    assert report.overall == ValidationStatus.PASS.value
    assert "e_urdf.json" in report.results


def test_index_build_and_load(sample_zoo: Path):
    index = AssetIndex(sample_zoo).build()
    assert len(index.entries) == 2
    paths = index.save(output_dir=sample_zoo.parent)
    assert paths["json"].exists()
    assert paths["yaml"].exists()

    loaded = AssetIndex(sample_zoo).load(paths["json"])
    assert len(loaded.entries) == 2
    assert loaded.lookup("dexhands/inspire_hand/right") is not None
