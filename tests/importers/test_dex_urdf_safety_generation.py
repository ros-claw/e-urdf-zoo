"""Tests for safety generation during dex-urdf import."""

from __future__ import annotations

from pathlib import Path

import yaml

from e_urdf_zoo.importers.capability_template import default_capabilities
from e_urdf_zoo.importers.safety_template import default_safety


def test_default_safety_blocks_real_robot():
    safety = default_safety("test_hand")
    assert safety["global_policy"]["real_robot_execution_allowed"] is False
    assert safety["global_policy"]["sandbox_required"] is True
    blocked = {b["id"] for b in safety["blocked_actions"]}
    assert "fast_full_close" in blocked
    assert "forceful_grasp_without_current_limit" in blocked


def test_default_capabilities_for_hand_forbid_forceful_grasp():
    caps = default_capabilities("dexterous_hand")
    cap_ids = {c["id"] for c in caps["capabilities"]}
    assert "ok_gesture" in cap_ids
    forbidden = {f["id"] for f in caps["forbidden_capabilities"]}
    assert "forceful_grasp_without_current_limit" in forbidden
    assert "fast_full_close" in forbidden


def test_imported_safety_and_capabilities_are_consistent(tmp_path: Path):
    from e_urdf_zoo.importers.dex_urdf import DexUrdfImporter

    fixture = Path(__file__).parent.parent / "fixtures" / "dex_urdf_minimal"
    importer = DexUrdfImporter(
        source_dir=fixture,
        output_dir=tmp_path,
        copy_assets=True,
        generate_safety=True,
        generate_prompts=True,
    )
    result = importer.import_one(
        asset_id="dexhands/inspire_hand/right",
        urdf_path=fixture
        / "robots"
        / "hands"
        / "inspire_hand"
        / "inspire_hand_right.urdf",
        category="dexhands",
        model="inspire_hand",
        variant="right",
    )
    caps = yaml.safe_load(
        (result.output_path / "capabilities.yaml").read_text(encoding="utf-8")
    )
    safety = yaml.safe_load(
        (result.output_path / "safety.yaml").read_text(encoding="utf-8")
    )
    assert all(c["real_robot_execution_allowed"] is False for c in caps["capabilities"])
    assert safety["global_policy"]["real_robot_execution_allowed"] is False
