"""Tests for the realsense-ros importer."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from e_urdf_zoo.importers.realsense_ros import RealSenseRosImporter

REalsense_SOURCE = Path("/home/ubuntu/rosclaw/rosclaw/realsense-ros")


@pytest.fixture
def source_dir():
    """Return the RealSense ROS source directory."""
    if not REalsense_SOURCE.exists():
        pytest.skip("realsense-ros source checkout not found")
    return REalsense_SOURCE


def test_scan_discovers_all_models(source_dir: Path, tmp_path: Path) -> None:
    """Scan discovers all supported RealSense models."""
    importer = RealSenseRosImporter(source_dir, tmp_path)
    specs = importer.scan()
    models = {spec.model for spec in specs}
    expected = {"d405", "d415", "d435", "d435i", "d436", "d455", "d585", "r410", "r430"}
    assert models == expected


def test_import_d455_structure(source_dir: Path, tmp_path: Path) -> None:
    """D455 import produces the expected bundle structure."""
    importer = RealSenseRosImporter(source_dir, tmp_path)
    result = importer.import_one("d455", tmp_path / "d455" / "default")
    assert result.xacro_expanded
    assert result.urdf_valid
    assert result.meshes_copied >= 1

    out = result.output_dir
    assert (out / "manifest.yaml").exists()
    assert (out / "semantic.yaml").exists()
    assert (out / "capabilities.yaml").exists()
    assert (out / "safety.yaml").exists()
    assert (out / "providers.yaml").exists()
    assert (out / "sandbox.yaml").exists()
    assert (out / "model/model.xacro").exists()
    assert (out / "model/model.urdf").exists()
    assert (out / "model/model_mujoco.urdf").exists()

    urdf_text = (out / "model/model.urdf").read_text(encoding="utf-8")
    assert "package://realsense2_description" not in urdf_text
    assert "$(find realsense2_description)" not in urdf_text
    assert "realsense_d455_mount" in urdf_text
    assert "camera_link" in urdf_text
    assert "camera_depth_optical_frame" in urdf_text


def test_import_d435i_has_imu(source_dir: Path, tmp_path: Path) -> None:
    """D435i expanded URDF contains IMU frames."""
    importer = RealSenseRosImporter(source_dir, tmp_path)
    result = importer.import_one("d435i", tmp_path / "d435i" / "default")
    assert result.urdf_valid

    urdf_text = (result.output_dir / "model/model.urdf").read_text(encoding="utf-8")
    assert "camera_accel_frame" in urdf_text
    assert "camera_gyro_frame" in urdf_text


def test_mujoco_urdf_loads(source_dir: Path, tmp_path: Path) -> None:
    """MuJoCo can load the generated MuJoCo-friendly URDF."""
    mujoco = pytest.importorskip("mujoco")
    importer = RealSenseRosImporter(source_dir, tmp_path)
    result = importer.import_one("d455", tmp_path / "d455" / "default")
    model = mujoco.MjModel.from_xml_path(
        str(result.output_dir / "model/model_mujoco.urdf")
    )
    assert model.nbody > 0


def test_capabilities_declare_forbidden_depth_safety(
    source_dir: Path, tmp_path: Path
) -> None:
    """Capabilities mark uncalibrated depth safety as forbidden."""
    import yaml

    importer = RealSenseRosImporter(source_dir, tmp_path)
    result = importer.import_one("d455", tmp_path / "d455" / "default")
    cap_data = yaml.safe_load(
        (result.output_dir / "capabilities.yaml").read_text(encoding="utf-8")
    )
    forbidden_ids = {fc["id"] for fc in cap_data["forbidden_capabilities"]}
    assert "depth_collision_avoidance_without_calibration" in forbidden_ids


def test_safety_blocks_uncalibrated_depth(source_dir: Path, tmp_path: Path) -> None:
    """Safety policy blocks depth-based safety without calibration."""
    import yaml

    importer = RealSenseRosImporter(source_dir, tmp_path)
    result = importer.import_one("d455", tmp_path / "d455" / "default")
    safety = yaml.safe_load(
        (result.output_dir / "safety.yaml").read_text(encoding="utf-8")
    )
    assert safety["global_policy"]["depth_for_safety_requires_calibration"] is True
    blocked = {action["id"] for action in safety["blocked_actions"]}
    assert "depth_collision_avoidance_without_calibration" in blocked


def test_all_models_import_and_validate(source_dir: Path, tmp_path: Path) -> None:
    """All RealSense models import, expand, and validate."""
    importer = RealSenseRosImporter(source_dir, tmp_path)
    results = importer.import_all()
    assert len(results) == 9
    for result in results:
        assert result.xacro_expanded, result.asset_id
        assert result.urdf_valid, result.asset_id
        # No package:// residue in expanded URDF.
        urdf_text = (result.output_dir / "model/model.urdf").read_text(encoding="utf-8")
        assert "package://realsense2_description" not in urdf_text
        # Basic tree sanity.
        tree = ET.parse(str(result.output_dir / "model/model.urdf"))
        root = tree.getroot()
        assert root.tag == "robot"
        assert len(list(root.iter("link"))) > 0
