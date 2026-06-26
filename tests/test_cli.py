"""Tests for the e-urdf-zoo CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

CLI = [sys.executable, "-m", "e_urdf_zoo.cli"]


def _make_zoo(tmp_path: Path) -> Path:
    zoo = tmp_path / "robots"
    manifest_dir = zoo / "dexhands" / "inspire_hand" / "right"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.yaml").write_text(
        "schema_version: e_urdf.asset.v1\n"
        "asset:\n"
        "  id: dexhands/inspire_hand/right\n"
        "  name: Inspire Hand Right\n"
        "  category: dexterous_hand\n"
        "  vendor: Inspire Robots\n",
        encoding="utf-8",
    )
    (manifest_dir / "safety.yaml").write_text(
        "schema_version: e_urdf.safety.v1\n"
        "global_policy:\n"
        "  real_robot_execution_allowed: false\n"
        "  sandbox_required: true\n"
        "blocked_actions:\n"
        "  - id: fast_full_close\n"
        "    reason: overload risk\n",
        encoding="utf-8",
    )
    (manifest_dir / "capabilities.yaml").write_text(
        "schema_version: e_urdf.capabilities.v1\n"
        "capabilities: []\n"
        "forbidden_capabilities: []\n",
        encoding="utf-8",
    )
    (manifest_dir / "semantic.yaml").write_text(
        "schema_version: e_urdf.semantic.v1\n"
        "groups: {}\n"
        "frames: {}\n",
        encoding="utf-8",
    )

    legacy_dir = zoo / "ur5e"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "e_urdf.json").write_text(
        '{"embodiment_id": "ur5e", "embodiment_name": "UR5e", '
        '"semantics": {"robot_type": "arm"}, "kinematics": {"dof": 6}}',
        encoding="utf-8",
    )
    return zoo


def test_cli_list_table(tmp_path: Path):
    env = {"E_URDF_ZOO_PATH": str(tmp_path)}
    _make_zoo(tmp_path)
    result = subprocess.run(
        [*CLI, "list"], capture_output=True, text=True, env=env
    )
    assert result.returncode == 0
    assert "dexhands/inspire_hand/right" in result.stdout
    assert "UR5e" in result.stdout


def test_cli_list_json(tmp_path: Path):
    env = {"E_URDF_ZOO_PATH": str(tmp_path)}
    _make_zoo(tmp_path)
    result = subprocess.run(
        [*CLI, "list", "--format", "json"], capture_output=True, text=True, env=env
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    ids = {entry["id"] for entry in data}
    assert "dexhands/inspire_hand/right" in ids


def test_cli_info(tmp_path: Path):
    env = {"E_URDF_ZOO_PATH": str(tmp_path)}
    _make_zoo(tmp_path)
    result = subprocess.run(
        [*CLI, "info", "dexhands/inspire_hand/right"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    assert "Inspire Hand Right" in result.stdout


def test_cli_validate_manifest_asset(tmp_path: Path):
    env = {"E_URDF_ZOO_PATH": str(tmp_path)}
    _make_zoo(tmp_path)
    result = subprocess.run(
        [*CLI, "validate", "dexhands/inspire_hand/right", "--format", "json"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["overall"] == "PASS"


def test_cli_index_build(tmp_path: Path):
    env = {"E_URDF_ZOO_PATH": str(tmp_path)}
    _make_zoo(tmp_path)
    result = subprocess.run(
        [*CLI, "index", "build", "--output", str(tmp_path)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    assert (tmp_path / "index.json").exists()
    assert (tmp_path / "index.yaml").exists()


def test_cli_missing_asset(tmp_path: Path):
    env = {"E_URDF_ZOO_PATH": str(tmp_path)}
    _make_zoo(tmp_path)
    result = subprocess.run(
        [*CLI, "info", "does/not/exist"], capture_output=True, text=True, env=env
    )
    assert result.returncode == 1
    assert "not found" in result.stderr
