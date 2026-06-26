"""Tests for manifest.yaml schema validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from e_urdf_zoo.schemas import (
    ManifestSchema,
    ValidationStatus,
    validate_manifest,
)


@pytest.fixture
def tmp_manifest(tmp_path: Path) -> Path:
    return tmp_path / "manifest.yaml"


def _write_manifest(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def test_minimal_valid_manifest_passes(tmp_manifest: Path):
    _write_manifest(
        tmp_manifest,
        {
            "schema_version": "e_urdf.asset.v1",
            "asset": {
                "id": "dexhands/inspire_hand/right",
                "name": "Inspire Hand Right",
                "category": "dexterous_hand",
            },
        },
    )
    result = validate_manifest(tmp_manifest)
    assert result.status == ValidationStatus.PASS


def test_missing_manifest_file_fails(tmp_path: Path):
    result = validate_manifest(tmp_path / "missing.yaml")
    assert result.status == ValidationStatus.FAIL
    assert any("not found" in m.message for m in result.messages)


def test_missing_asset_id_fails(tmp_manifest: Path):
    _write_manifest(tmp_manifest, {"schema_version": "e_urdf.asset.v1", "asset": {"name": "No ID", "category": "hand"}})
    result = validate_manifest(tmp_manifest)
    assert result.status == ValidationStatus.FAIL


def test_unknown_upstream_license_warns(tmp_manifest: Path):
    _write_manifest(
        tmp_manifest,
        {
            "schema_version": "e_urdf.asset.v1",
            "asset": {
                "id": "dexhands/test_hand/right",
                "name": "Test Hand",
                "category": "dexterous_hand",
            },
            "license": {"upstream_model_license": "unknown"},
        },
    )
    result = validate_manifest(tmp_manifest)
    assert result.status == ValidationStatus.PASS_WITH_WARNINGS
    assert any("unknown" in m.message for m in result.messages)


def test_sandbox_required_must_be_true(tmp_manifest: Path):
    _write_manifest(
        tmp_manifest,
        {
            "schema_version": "e_urdf.asset.v1",
            "asset": {
                "id": "dexhands/test_hand/right",
                "name": "Test Hand",
                "category": "dexterous_hand",
            },
            "runtime_policy": {"sandbox_required": False},
        },
    )
    result = validate_manifest(tmp_manifest)
    assert result.status == ValidationStatus.FAIL
    assert any("sandbox_required" in m.message for m in result.messages)


def test_manifest_model_round_trip(tmp_manifest: Path):
    data = {
        "schema_version": "e_urdf.asset.v1",
        "asset": {
            "id": "humanoids/unitree/g1/default",
            "name": "Unitree G1",
            "category": "humanoid",
            "vendor": "Unitree",
        },
    }
    manifest = ManifestSchema.model_validate(data)
    assert manifest.asset.id == "humanoids/unitree/g1/default"
    assert manifest.asset.vendor == "Unitree"
    assert manifest.runtime_policy.sandbox_required is True
