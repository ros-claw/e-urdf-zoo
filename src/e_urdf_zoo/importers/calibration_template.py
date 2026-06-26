"""Default calibration_defaults.yaml content for imported dex-urdf assets."""

from __future__ import annotations

from typing import Any


def default_calibration_defaults(asset_name: str) -> dict[str, Any]:
    return {
        "schema_version": "e_urdf.calibration.v1",
        "note": "These defaults are placeholders; real hardware requires measured calibration.",
        "joint_offsets_rad": {},
        "joint_signs": {},
        "current_limits_a": {},
        "position_limits_rad": {},
        "force_calibration": {
            "sensor_zero_n": 0.0,
            "contact_threshold_n": 0.5,
        },
        "finger_clearance_mm": {},
    }
