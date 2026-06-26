"""Tests for dex-urdf importer discovery."""

from __future__ import annotations

from pathlib import Path

from e_urdf_zoo.importers.dex_urdf import DexUrdfImporter


FIXTURE = Path(__file__).parent.parent / "fixtures" / "dex_urdf_minimal"


def test_find_supported_models_discovers_inspire_hand(tmp_path: Path):
    importer = DexUrdfImporter(
        source_dir=FIXTURE,
        output_dir=tmp_path / "out",
    )
    models = importer.find_supported_models()
    ids = {m["asset_id"] for m in models}
    assert "dexhands/inspire_hand/right" in ids


def test_default_families_map_to_default_variant(tmp_path: Path):
    # Create a fake dclaw family to verify default variant mapping.
    source = tmp_path / "source"
    family_dir = source / "robots" / "hands" / "dclaw_gripper"
    family_dir.mkdir(parents=True)
    (family_dir / "dclaw_gripper.urdf").write_text(
        '<?xml version="1.0"?><robot name="dclaw">'
        '<link name="base"/></robot>',
        encoding="utf-8",
    )
    importer = DexUrdfImporter(source_dir=source, output_dir=tmp_path / "out")
    models = importer.find_supported_models()
    assert len(models) == 1
    assert models[0]["variant"] == "default"
    assert models[0]["asset_id"] == "dexhands/dclaw/default"
