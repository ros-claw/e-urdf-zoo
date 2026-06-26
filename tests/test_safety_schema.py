"""Tests for safety.yaml schema validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from e_urdf_zoo.schemas import (
    SafetySchema,
    ValidationStatus,
    validate_safety,
)


@pytest.fixture
def tmp_safety(tmp_path: Path) -> Path:
    return tmp_path / "safety.yaml"


def _write_safety(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def test_minimal_valid_safety_passes(tmp_safety: Path):
    _write_safety(
        tmp_safety,
        {
            "schema_version": "e_urdf.safety.v1",
            "safety_status": "experimental",
            "global_policy": {
                "real_robot_execution_allowed": False,
                "sandbox_required": True,
            },
            "blocked_actions": [
                {"id": "fast_full_close", "reason": "overload risk"}
            ],
        },
    )
    result = validate_safety(tmp_safety)
    assert result.status == ValidationStatus.PASS


def test_missing_safety_file_fails(tmp_path: Path):
    result = validate_safety(tmp_path / "safety.yaml")
    assert result.status == ValidationStatus.FAIL


def test_real_robot_allowed_warns(tmp_safety: Path):
    _write_safety(
        tmp_safety,
        {
            "schema_version": "e_urdf.safety.v1",
            "global_policy": {
                "real_robot_execution_allowed": True,
                "sandbox_required": True,
            },
        },
    )
    result = validate_safety(tmp_safety)
    assert result.status == ValidationStatus.PASS_WITH_WARNINGS


def test_sandbox_required_must_be_true(tmp_safety: Path):
    _write_safety(
        tmp_safety,
        {
            "schema_version": "e_urdf.safety.v1",
            "global_policy": {
                "real_robot_execution_allowed": False,
                "sandbox_required": False,
            },
        },
    )
    result = validate_safety(tmp_safety)
    assert result.status == ValidationStatus.FAIL


def test_safety_model_round_trip(tmp_safety: Path):
    data = {
        "schema_version": "e_urdf.safety.v1",
        "safety_status": "experimental",
        "blocked_actions": [
            {"id": "forceful_grasp", "reason": "no current limit"}
        ],
    }
    safety = SafetySchema.model_validate(data)
    assert safety.safety_status == "experimental"
    assert safety.blocked_actions[0].id == "forceful_grasp"
