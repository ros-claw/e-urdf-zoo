"""Tests for importing a single dex-urdf asset."""

from __future__ import annotations

from pathlib import Path

import yaml

from e_urdf_zoo.importers.dex_urdf import DexUrdfImporter


FIXTURE = Path(__file__).parent.parent / "fixtures" / "dex_urdf_minimal"


def test_import_one_creates_bundle(tmp_path: Path):
    importer = DexUrdfImporter(
        source_dir=FIXTURE,
        output_dir=tmp_path,
        copy_assets=True,
        generate_safety=True,
        generate_prompts=True,
    )
    result = importer.import_one(
        asset_id="dexhands/inspire_hand/right",
        urdf_path=FIXTURE / "robots" / "hands" / "inspire_hand" / "inspire_hand_right.urdf",
        category="dexhands",
        model="inspire_hand",
        variant="right",
    )
    assert result.status == "success"
    out = result.output_path
    assert (out / "manifest.yaml").exists()
    assert (out / "safety.yaml").exists()
    assert (out / "capabilities.yaml").exists()
    assert (out / "semantic.yaml").exists()
    assert (out / "providers.yaml").exists()
    assert (out / "sandbox.yaml").exists()
    assert (out / "calibration_defaults.yaml").exists()
    assert (out / "prompts" / "system.md").exists()
    assert (out / "model" / "model.urdf").exists()
    assert (out / "checksums.json").exists()


def test_import_one_rewrites_mesh_paths(tmp_path: Path):
    importer = DexUrdfImporter(
        source_dir=FIXTURE,
        output_dir=tmp_path,
        copy_assets=True,
    )
    result = importer.import_one(
        asset_id="dexhands/inspire_hand/right",
        urdf_path=FIXTURE / "robots" / "hands" / "inspire_hand" / "inspire_hand_right.urdf",
        category="dexhands",
        model="inspire_hand",
        variant="right",
    )
    urdf_text = (result.output_path / "model" / "model.urdf").read_text(
        encoding="utf-8"
    )
    assert "../meshes/raw/visual/base_link.glb" in urdf_text
    assert "../meshes/raw/collision/base_link.obj" in urdf_text
    assert (result.output_path / "meshes" / "raw" / "visual" / "base_link.glb").exists()


def test_import_one_manifest_has_safety_blocks(tmp_path: Path):
    importer = DexUrdfImporter(
        source_dir=FIXTURE,
        output_dir=tmp_path,
        copy_assets=True,
        generate_safety=True,
    )
    result = importer.import_one(
        asset_id="dexhands/inspire_hand/right",
        urdf_path=FIXTURE / "robots" / "hands" / "inspire_hand" / "inspire_hand_right.urdf",
        category="dexhands",
        model="inspire_hand",
        variant="right",
    )
    manifest = yaml.safe_load(
        (result.output_path / "manifest.yaml").read_text(encoding="utf-8")
    )
    assert manifest["asset"]["status"] == "experimental"
    assert manifest["runtime_policy"]["real_robot_execution_allowed"] is False
    assert manifest["runtime_policy"]["sandbox_required"] is True

    safety = yaml.safe_load(
        (result.output_path / "safety.yaml").read_text(encoding="utf-8")
    )
    blocked_ids = {b["id"] for b in safety["blocked_actions"]}
    assert "fast_full_close" in blocked_ids
    assert "forceful_grasp_without_current_limit" in blocked_ids
