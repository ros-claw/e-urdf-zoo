"""Tests for bulk dex-urdf import."""

from __future__ import annotations

from pathlib import Path

from e_urdf_zoo.importers.dex_urdf import DexUrdfImporter


FIXTURE = Path(__file__).parent.parent / "fixtures" / "dex_urdf_minimal"


def test_import_all_imports_discovered_models(tmp_path: Path):
    importer = DexUrdfImporter(
        source_dir=FIXTURE,
        output_dir=tmp_path,
        copy_assets=True,
    )
    results = importer.import_all()
    assert len(results) >= 1
    assert any(r.asset_id == "dexhands/inspire_hand/right" for r in results)
    for result in results:
        assert result.status in {"success", "success_with_warnings"}
        assert (result.output_path / "manifest.yaml").exists()
