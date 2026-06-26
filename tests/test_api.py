"""Tests for the public e_urdf_zoo API."""

from __future__ import annotations

from pathlib import Path

import e_urdf_zoo as zoo
from e_urdf_zoo.loader import AssetLoader


def test_list_robots_finds_manifest_and_legacy(tmp_path: Path, monkeypatch):
    zoo_path = tmp_path / "robots"
    manifest_dir = zoo_path / "dexhands" / "test" / "right"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.yaml").write_text(
        "schema_version: e_urdf.asset.v1\n"
        "asset:\n"
        "  id: dexhands/test/right\n"
        "  name: Test Hand\n"
        "  category: dexterous_hand\n",
        encoding="utf-8",
    )
    (manifest_dir / "safety.yaml").write_text(
        "schema_version: e_urdf.safety.v1\n"
        "global_policy:\n"
        "  real_robot_execution_allowed: false\n"
        "  sandbox_required: true\n",
        encoding="utf-8",
    )

    legacy_dir = zoo_path / "legacy_bot"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "e_urdf.json").write_text(
        '{"embodiment_id": "legacy_bot", "embodiment_name": "Legacy Bot"}',
        encoding="utf-8",
    )

    monkeypatch.setenv("E_URDF_ZOO_PATH", str(tmp_path))
    robots = zoo.list_robots()
    assert "dexhands/test/right" in robots
    assert "legacy_bot" in robots


def test_load_embodiment_returns_unified_object(tmp_path: Path, monkeypatch):
    zoo_path = tmp_path / "robots"
    manifest_dir = zoo_path / "humanoids" / "unitree" / "g1" / "default"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.yaml").write_text(
        "schema_version: e_urdf.asset.v1\n"
        "asset:\n"
        "  id: humanoids/unitree/g1/default\n"
        "  name: Unitree G1\n"
        "  category: humanoid\n"
        "  vendor: Unitree\n",
        encoding="utf-8",
    )
    (manifest_dir / "safety.yaml").write_text(
        "schema_version: e_urdf.safety.v1\n"
        "global_policy:\n"
        "  real_robot_execution_allowed: false\n"
        "  sandbox_required: true\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("E_URDF_ZOO_PATH", str(tmp_path))
    asset = zoo.load_embodiment("humanoids/unitree/g1/default")
    assert asset.name == "Unitree G1"
    assert asset.category == "humanoid"
    assert asset.is_manifest
    assert "embodiment_id" in asset.config


def test_get_robot_info(tmp_path: Path, monkeypatch):
    zoo_path = tmp_path / "robots"
    legacy_dir = zoo_path / "my_robot"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "e_urdf.json").write_text(
        '{"embodiment_id": "my_robot", "embodiment_name": "My Robot", '
        '"semantics": {"robot_type": "arm"}, "kinematics": {"dof": 3}}',
        encoding="utf-8",
    )

    monkeypatch.setenv("E_URDF_ZOO_PATH", str(tmp_path))
    info = zoo.get_robot_info("my_robot")
    assert info["name"] == "My Robot"
    assert info["type"] == "arm"
    assert info["dof"] == 3
    assert info["is_manifest"] is False


def test_default_loader_uses_env_var(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("E_URDF_ZOO_PATH", str(tmp_path))
    loader = AssetLoader()
    assert loader.zoo_path == tmp_path / "robots"
