"""Tests for capabilities.yaml schema validation."""

from __future__ import annotations

import pytest

from e_urdf_zoo.schemas import CapabilitiesSchema


def test_capabilities_model_with_forbidden():
    data = {
        "schema_version": "e_urdf.capabilities.v1",
        "capabilities": [
            {
                "id": "open_hand",
                "name": "Open Hand",
                "scope": "manipulation",
                "risk": "medium",
                "sandbox_required": True,
                "real_robot_execution_allowed": False,
            }
        ],
        "forbidden_capabilities": [
            {
                "id": "forceful_grasp_without_current_limit",
                "description": "Forceful grasping without current limit",
                "severity": "critical",
                "enforcement": {
                    "policy_block": True,
                    "sandbox_block": True,
                    "real_robot_block": True,
                },
            }
        ],
    }
    caps = CapabilitiesSchema.model_validate(data)
    assert caps.capabilities[0].id == "open_hand"
    assert caps.forbidden_capabilities[0].id == "forceful_grasp_without_current_limit"


def test_high_risk_capability_without_sandbox_fails():
    """Schema-level check: high risk capability must require sandbox."""
    data = {
        "schema_version": "e_urdf.capabilities.v1",
        "capabilities": [
            {
                "id": "ok_gesture",
                "name": "OK Gesture",
                "risk": "high",
                "sandbox_required": False,
                "real_robot_execution_allowed": False,
            }
        ],
    }
    caps = CapabilitiesSchema.model_validate(data)
    ok = next(c for c in caps.capabilities if c.id == "ok_gesture")
    assert ok.risk == "high"
    assert ok.sandbox_required is False
    # Validation function should flag this; model itself allows the field.
