"""Bulk importer for Intel RealSense ROS description assets.

Converts upstream `realsense2_description` xacro/mesh files into the
manifest-driven e-URDF-Zoo sensor asset bundle format.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import trimesh
import yaml

from .urdf_common import compute_checksums

MODEL_SPECS: dict[str, dict[str, Any]] = {
    "d405": {
        "macro_file": "_d405.urdf.xacro",
        "macro_name": "sensor_d405",
        "has_imu": False,
        "modalities": ["rgb", "depth", "infrared"],
    },
    "d415": {
        "macro_file": "_d415.urdf.xacro",
        "macro_name": "sensor_d415",
        "has_imu": False,
        "modalities": ["rgb", "depth", "infrared"],
    },
    "d435": {
        "macro_file": "_d435.urdf.xacro",
        "macro_name": "sensor_d435",
        "has_imu": False,
        "modalities": ["rgb", "depth", "infrared"],
    },
    "d435i": {
        "macro_file": "_d435i.urdf.xacro",
        "macro_name": "sensor_d435i",
        "has_imu": True,
        "extra_files": ["_d435.urdf.xacro", "_d435i_imu_modules.urdf.xacro"],
        "modalities": ["rgb", "depth", "infrared", "imu"],
    },
    "d436": {
        "macro_file": "_d436.urdf.xacro",
        "macro_name": "sensor_d436",
        "has_imu": False,
        "modalities": ["rgb", "depth", "infrared"],
    },
    "d455": {
        "macro_file": "_d455.urdf.xacro",
        "macro_name": "sensor_d455",
        "has_imu": True,
        "modalities": ["rgb", "depth", "infrared", "imu"],
    },
    "d585": {
        "macro_file": "_d585.urdf.xacro",
        "macro_name": "sensor_d585",
        "has_imu": False,
        "modalities": ["rgb", "depth", "infrared"],
    },
    "r410": {
        "macro_file": "_r410.urdf.xacro",
        "macro_name": "sensor_r410",
        "has_imu": False,
        "modalities": ["depth", "infrared"],
    },
    "r430": {
        "macro_file": "_r430.urdf.xacro",
        "macro_name": "sensor_r430",
        "has_imu": False,
        "modalities": ["depth", "infrared"],
    },
}

SHARED_XACRO_FILES = ["_materials.urdf.xacro", "_usb_plug.urdf.xacro"]


@dataclass
class RealSenseModelSpec:
    """Specification for one RealSense model import."""

    model: str
    macro_file: str
    macro_name: str
    has_imu: bool
    modalities: list[str]
    extra_files: list[str] = field(default_factory=list)


@dataclass
class RealSenseImportResult:
    """Result of importing one RealSense model."""

    asset_id: str
    output_dir: Path
    xacro_expanded: bool
    urdf_valid: bool
    meshes_copied: int
    warnings: list[str]


class RealSenseRosImporter:
    """Import realsense-ros description assets into e-URDF-Zoo bundles."""

    def __init__(
        self,
        source_dir: Path | str,
        output_dir: Path | str,
        copy_meshes: bool = True,
        expand_xacro: bool = True,
        generate_mujoco_urdf: bool = True,
        validate: bool = True,
    ):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.copy_meshes = copy_meshes
        self.expand_xacro = expand_xacro
        self.generate_mujoco_urdf = generate_mujoco_urdf
        self.validate = validate
        self._source_info = self._detect_source_info()

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------
    def scan(self) -> list[RealSenseModelSpec]:
        """Scan the source checkout and return importable model specs."""
        urdf_dir = self.source_dir / "realsense2_description" / "urdf"
        meshes_dir = self.source_dir / "realsense2_description" / "meshes"
        if not urdf_dir.exists():
            raise FileNotFoundError(
                f"RealSense description urdf dir not found: {urdf_dir}"
            )
        if not meshes_dir.exists():
            raise FileNotFoundError(
                f"RealSense description meshes dir not found: {meshes_dir}"
            )

        missing_shared = [f for f in SHARED_XACRO_FILES if not (urdf_dir / f).exists()]
        if missing_shared:
            raise FileNotFoundError(
                f"Missing required shared xacro files: {missing_shared}"
            )

        specs: list[RealSenseModelSpec] = []
        for model, info in sorted(MODEL_SPECS.items()):
            macro_path = urdf_dir / info["macro_file"]
            if not macro_path.exists():
                print(
                    f"[WARNING] RealSense model {model} macro not found: {macro_path}"
                )
                continue
            specs.append(
                RealSenseModelSpec(
                    model=model,
                    macro_file=info["macro_file"],
                    macro_name=info["macro_name"],
                    has_imu=info["has_imu"],
                    modalities=info["modalities"],
                    extra_files=info.get("extra_files", []),
                )
            )
        return specs

    def _detect_source_info(self) -> dict[str, str]:
        """Extract git metadata from the realsense-ros checkout."""
        info = {
            "type": "third_party_import",
            "upstream_repo": "realsenseai/realsense-ros",
            "upstream_url": "https://github.com/realsenseai/realsense-ros",
            "upstream_branch": "ros2-master",
            "upstream_commit": "unknown",
            "upstream_package": "realsense2_description",
            "upstream_path": "realsense2_description/urdf",
            "imported_at": datetime.now(timezone.utc).isoformat(),
            "importer": "e_urdf_zoo.importers.realsense_ros",
        }
        try:
            commit = subprocess.check_output(
                ["git", "-C", str(self.source_dir), "rev-parse", "HEAD"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            info["upstream_commit"] = commit
            remote = subprocess.check_output(
                ["git", "-C", str(self.source_dir), "remote", "get-url", "origin"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            if remote:
                info["upstream_repo"] = remote
                info["upstream_url"] = remote
        except Exception:  # noqa: BLE001
            pass
        return info

    # ------------------------------------------------------------------
    # Import all / one
    # ------------------------------------------------------------------
    def import_all(self) -> list[RealSenseImportResult]:
        """Import all discovered RealSense models."""
        specs = self.scan()
        results: list[RealSenseImportResult] = []
        for spec in specs:
            output = self.output_dir / spec.model / "default"
            results.append(self.import_one(spec, output))
        return results

    def import_one(
        self,
        spec: RealSenseModelSpec | str,
        output_dir: Path | str,
    ) -> RealSenseImportResult:
        """Import a single RealSense model into the zoo bundle format."""
        if isinstance(spec, str):
            spec = self._spec_for_model(spec)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        asset_id = f"sensors/realsense/{spec.model}/default"
        warnings: list[str] = []

        urdf_dir = self.source_dir / "realsense2_description" / "urdf"
        meshes_dir = self.source_dir / "realsense2_description" / "meshes"

        # Source xacro files
        source_xacro_dir = output_dir / "source" / "xacro"
        source_xacro_dir.mkdir(parents=True, exist_ok=True)
        files_to_copy = [spec.macro_file, *SHARED_XACRO_FILES, *spec.extra_files]
        for filename in files_to_copy:
            src = urdf_dir / filename
            dst = source_xacro_dir / filename
            if not src.exists():
                warnings.append(f"Expected source file missing: {filename}")
                continue
            text = src.read_text(encoding="utf-8")
            # Patch ROS package includes to relative includes inside source/xacro.
            text = re.sub(
                r"\$\(find\s+realsense2_description\s*\)/urdf/",
                "",
                text,
            )
            dst.write_text(text, encoding="utf-8")

        # Write wrapper xacro and expand
        model_dir = output_dir / "model"
        model_dir.mkdir(parents=True, exist_ok=True)
        wrapper_path = model_dir / "model.xacro"
        self._write_wrapper_xacro(wrapper_path, spec)

        xacro_expanded = False
        urdf_path = model_dir / "model.urdf"
        if self.expand_xacro:
            try:
                self._expand_xacro(wrapper_path, urdf_path)
                xacro_expanded = urdf_path.exists() and urdf_path.stat().st_size > 0
            except subprocess.CalledProcessError as exc:
                warnings.append(f"xacro expansion failed: {exc}")
        else:
            warnings.append("xacro expansion skipped")

        # Copy meshes and rewrite URDF package:// paths
        meshes_copied = 0
        raw_dir = output_dir / "meshes" / "raw"
        if xacro_expanded and urdf_path.exists():
            mesh_refs = self._collect_package_mesh_refs(urdf_path)
            if self.copy_meshes:
                raw_dir.mkdir(parents=True, exist_ok=True)
                meshes_copied, missing = self._copy_meshes(
                    mesh_refs, meshes_dir, raw_dir
                )
                if missing:
                    warnings.extend(f"Missing mesh: {m}" for m in missing)
                self._rewrite_mesh_paths(urdf_path)
            else:
                warnings.append("mesh copy skipped")

        # MuJoCo-friendly URDF
        mujoco_path = model_dir / "model_mujoco.urdf"
        if self.generate_mujoco_urdf and urdf_path.exists():
            shutil.copy2(urdf_path, mujoco_path)
            self._insert_mujoco_hints(mujoco_path)
            if self.copy_meshes:
                converted = self._prepare_mujoco_meshes(mujoco_path, raw_dir)
                if converted:
                    warnings.append(
                        f"Prepared {converted} MuJoCo-compatible mesh(s) "
                        "(DAE conversion / decimation)"
                    )

        # Validation reports
        validation_dir = output_dir / "validation"
        validation_dir.mkdir(parents=True, exist_ok=True)
        self._write_validation_reports(
            validation_dir,
            xacro_expanded,
            urdf_path,
            mujoco_path,
        )

        # Metadata bundle
        self._write_manifest(output_dir, asset_id, spec)
        self._write_bundle_files(output_dir, asset_id, spec, urdf_path)
        self._write_e_urdf_compat(output_dir)

        # Checksums
        checksums = compute_checksums(output_dir)
        (output_dir / "checksums.json").write_text(
            json.dumps(checksums, indent=2), encoding="utf-8"
        )

        # Basic URDF parse check
        urdf_valid = False
        if urdf_path.exists():
            try:
                tree = ET.parse(str(urdf_path))
                root = tree.getroot()
                urdf_valid = root.tag == "robot" and len(list(root.iter("link"))) > 0
            except ET.ParseError as exc:
                warnings.append(f"URDF parse error: {exc}")

        return RealSenseImportResult(
            asset_id=asset_id,
            output_dir=output_dir,
            xacro_expanded=xacro_expanded,
            urdf_valid=urdf_valid,
            meshes_copied=meshes_copied,
            warnings=warnings,
        )

    def _spec_for_model(self, model: str) -> RealSenseModelSpec:
        info = MODEL_SPECS[model.lower()]
        return RealSenseModelSpec(
            model=model.lower(),
            macro_file=info["macro_file"],
            macro_name=info["macro_name"],
            has_imu=info["has_imu"],
            modalities=info["modalities"],
            extra_files=info.get("extra_files", []),
        )

    # ------------------------------------------------------------------
    # Wrapper / expansion
    # ------------------------------------------------------------------
    def _write_wrapper_xacro(self, path: Path, spec: RealSenseModelSpec) -> None:
        includes = "\n".join(
            f'  <xacro:include filename="../source/xacro/{filename}"/>'
            for filename in [
                SHARED_XACRO_FILES[0],
                SHARED_XACRO_FILES[1],
                spec.macro_file,
            ]
        )
        robot_name = f"realsense_{spec.model}_standalone"
        mount_link = f"realsense_{spec.model}_mount"
        content = f"""<?xml version="1.0"?>
<robot name="{robot_name}" xmlns:xacro="http://ros.org/wiki/xacro">

{includes}

  <link name="{mount_link}"/>

  <xacro:{spec.macro_name}
    parent="{mount_link}"
    name="camera"
    use_nominal_extrinsics="true">
    <origin xyz="0 0 0" rpy="0 0 0"/>
  </xacro:{spec.macro_name}>

</robot>
"""
        path.write_text(content, encoding="utf-8")

    def _xacro_executable(self) -> str:
        """Locate the `xacro` executable, including project venv fallback."""
        exe = shutil.which("xacro")
        if exe:
            return exe
        venv_candidate = Path(sys.executable).parent / "xacro"
        if venv_candidate.exists():
            return str(venv_candidate)
        return "xacro"

    def _expand_xacro(self, wrapper_path: Path, output_path: Path) -> None:
        """Run xacro to expand the wrapper into a standalone URDF."""
        cmd = [self._xacro_executable(), str(wrapper_path)]
        with open(output_path, "w", encoding="utf-8") as f:
            subprocess.run(cmd, check=True, stdout=f, stderr=subprocess.PIPE, text=True)

    # ------------------------------------------------------------------
    # Mesh handling
    # ------------------------------------------------------------------
    def _collect_package_mesh_refs(self, urdf_path: Path) -> list[str]:
        """Collect package://realsense2_description/meshes/ references."""
        tree = ET.parse(str(urdf_path))
        refs: list[str] = []
        for elem in tree.iter("mesh"):
            filename = elem.get("filename")
            if filename and filename.startswith(
                "package://realsense2_description/meshes/"
            ):
                refs.append(filename)
        return refs

    def _copy_meshes(
        self,
        refs: list[str],
        source_meshes_dir: Path,
        raw_dir: Path,
    ) -> tuple[int, list[str]]:
        """Copy referenced meshes into meshes/raw/ preserving subdirs.

        Returns (copied_count, missing_refs).
        """
        prefix = "package://realsense2_description/meshes/"
        copied = 0
        missing: list[str] = []
        seen: set[Path] = set()
        for ref in refs:
            rel = ref[len(prefix) :].lstrip("/")
            src = source_meshes_dir / rel
            if not src.exists():
                missing.append(ref)
                continue
            dst = raw_dir / rel
            if dst in seen:
                continue
            seen.add(dst)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
        return copied, missing

    def _rewrite_mesh_paths(self, urdf_path: Path) -> None:
        """Replace package:// mesh URIs with relative paths in-place."""
        prefix = "package://realsense2_description/meshes/"
        text = urdf_path.read_text(encoding="utf-8")
        # Replace in both active attributes and XML comments (e.g. R410/R430).
        text = text.replace(prefix, "../meshes/raw/")
        urdf_path.write_text(text, encoding="utf-8")

        # Also update parsed tree for consistency.
        tree = ET.parse(str(urdf_path))
        changed = False
        for elem in tree.iter("mesh"):
            filename = elem.get("filename")
            if not filename or not filename.startswith("../meshes/raw/"):
                continue
            elem.set("filename", filename)
            changed = True
        if changed:
            tree.write(str(urdf_path), encoding="utf-8", xml_declaration=True)

    def _insert_mujoco_hints(self, mujoco_path: Path) -> None:
        """Insert a MuJoCo compiler hint into the URDF."""
        text = mujoco_path.read_text(encoding="utf-8")
        hint = "\n".join(
            [
                "  <mujoco>",
                '    <compiler discardvisual="false" fusestatic="false"/>',
                "  </mujoco>",
            ]
        )
        # Insert right after the opening <robot> tag.
        text = re.sub(r"(<robot[^>]*>\n?)", rf"\1{hint}\n", text, count=1)
        mujoco_path.write_text(text, encoding="utf-8")

    def _prepare_mujoco_meshes(
        self,
        mujoco_path: Path,
        raw_dir: Path,
        max_faces: int = 50_000,
    ) -> int:
        """Prepare MuJoCo-compatible meshes from the canonical URDF meshes.

        MuJoCo cannot load COLLADA .dae files and refuses binary STL files with
        more than 200k faces. We therefore:
          - convert .dae files to binary STL (decimated if needed);
          - decimate overly large .stl files;
          - write the results into meshes/mujoco/ and update the MuJoCo URDF.
        """
        tree = ET.parse(str(mujoco_path))
        converted = 0
        mujoco_dir = raw_dir.parent / "mujoco"
        for elem in tree.iter("mesh"):
            filename = elem.get("filename")
            if not filename:
                continue
            src_path = mujoco_path.parent / filename
            if not src_path.exists():
                continue

            lower = filename.lower()
            is_dae = lower.endswith(".dae")
            try:
                mesh = trimesh.load(str(src_path), force="mesh")
            except Exception:  # noqa: BLE001
                continue

            if not is_dae and len(mesh.faces) <= max_faces:
                # Already MuJoCo-friendly; leave reference as-is.
                continue

            # Decide target location under meshes/mujoco/ preserving subdirs.
            try:
                rel_raw = Path(filename).relative_to("../meshes/raw")
            except ValueError:
                rel_raw = Path(filename).name
            target_name = rel_raw.with_suffix(".stl")
            target_path = mujoco_dir / target_name
            target_path.parent.mkdir(parents=True, exist_ok=True)

            if len(mesh.faces) > max_faces:
                try:
                    mesh = mesh.simplify_quadric_decimation(face_count=max_faces)
                except Exception:  # noqa: BLE001
                    continue
            try:
                mesh.export(str(target_path), file_type="stl")
            except Exception:  # noqa: BLE001
                continue

            # Relative from model/ to meshes/mujoco/
            new_rel = Path("../meshes/mujoco") / target_name
            elem.set("filename", new_rel.as_posix())
            converted += 1

        if converted:
            tree.write(str(mujoco_path), encoding="utf-8", xml_declaration=True)
        return converted

    # ------------------------------------------------------------------
    # Validation reports
    # ------------------------------------------------------------------
    def _write_validation_reports(
        self,
        validation_dir: Path,
        xacro_expanded: bool,
        urdf_path: Path,
        mujoco_path: Path,
    ) -> None:
        xacro_report = {
            "expanded": xacro_expanded,
            "wrapper": "model/model.xacro",
            "output": "model/model.urdf",
        }
        urdf_report: dict[str, Any] = {
            "parsed": False,
            "link_count": 0,
            "joint_count": 0,
        }
        if urdf_path.exists():
            try:
                tree = ET.parse(str(urdf_path))
                root = tree.getroot()
                urdf_report["parsed"] = root.tag == "robot"
                urdf_report["link_count"] = len(list(root.iter("link")))
                urdf_report["joint_count"] = len(list(root.iter("joint")))
            except ET.ParseError as exc:
                urdf_report["error"] = str(exc)

        mesh_report = {"mesh_count": 0, "missing": []}
        if urdf_path.exists():
            tree = ET.parse(str(urdf_path))
            missing: list[str] = []
            count = 0
            for elem in tree.iter("mesh"):
                filename = elem.get("filename")
                if not filename:
                    continue
                count += 1
                if filename.startswith("package://"):
                    missing.append(filename)
                    continue
                resolved = urdf_path.parent / filename
                if not resolved.exists():
                    missing.append(filename)
            mesh_report["mesh_count"] = count
            mesh_report["missing"] = missing

        mujoco_report = {"loaded": False}
        if mujoco_path.exists():
            try:
                import mujoco

                model = mujoco.MjModel.from_xml_path(str(mujoco_path))
                mujoco_report["loaded"] = model is not None
            except Exception as exc:  # noqa: BLE001
                mujoco_report["error"] = str(exc)

        (validation_dir / "xacro_expand_report.json").write_text(
            json.dumps(xacro_report, indent=2), encoding="utf-8"
        )
        (validation_dir / "urdf_parse_report.json").write_text(
            json.dumps(urdf_report, indent=2), encoding="utf-8"
        )
        (validation_dir / "mesh_report.json").write_text(
            json.dumps(mesh_report, indent=2), encoding="utf-8"
        )
        (validation_dir / "mujoco_report.json").write_text(
            json.dumps(mujoco_report, indent=2), encoding="utf-8"
        )

    # ------------------------------------------------------------------
    # Bundle metadata
    # ------------------------------------------------------------------
    def _write_manifest(
        self,
        output_dir: Path,
        asset_id: str,
        spec: RealSenseModelSpec,
    ) -> None:
        model_upper = spec.model.upper()
        manifest: dict[str, Any] = {
            "schema_version": "e_urdf.asset.v1",
            "asset": {
                "id": asset_id,
                "name": f"Intel RealSense {model_upper}",
                "version": "0.1.0",
                "asset_type": "sensor",
                "category": "rgbd_camera",
                "vendor": "Intel RealSense",
                "model": model_upper,
                "variant": "default",
                "status": "experimental",
                "description": (
                    f"RealSense {model_upper} camera description imported from "
                    "realsense-ros realsense2_description."
                ),
            },
            "source": {
                **self._source_info,
                "upstream_path": f"realsense2_description/urdf/{spec.macro_file}",
            },
            "license": {
                "repo_declared_license": "Apache-2.0",
                "upstream_model_license": "Apache-2.0",
                "import_blocking": False,
                "display_warning": False,
                "notice_file": "licenses/NOTICE",
                "third_party_file": "licenses/THIRD_PARTY.yaml",
            },
            "model": {
                "primary_format": "urdf",
                "xacro": "model/model.xacro",
                "urdf": "model/model.urdf",
                "mujoco_urdf": "model/model_mujoco.urdf",
                "mjcf": None,
                "usd": None,
                "meshes_dir": "meshes/raw",
            },
            "sensor": {
                "type": "rgbd_camera",
                "modalities": spec.modalities,
                "has_imu": spec.has_imu,
                "imu_modalities": ["gyro", "accel"] if spec.has_imu else [],
                "requires_calibration": True,
            },
            "robot": {
                "morphology": "sensor",
                "robot_class": "rgbd_camera",
                "dof": 0,
            },
            "semantics": {
                "semantic_file": "semantic.yaml",
                "capabilities_file": "capabilities.yaml",
                "safety_file": "safety.yaml",
                "providers_file": "providers.yaml",
                "sandbox_file": "sandbox.yaml",
                "calibration_defaults_file": "calibration_defaults.yaml",
                "prompts_dir": "prompts/",
            },
            "runtime_policy": {
                "attachable_to_body": True,
                "requires_mount_frame": True,
                "calibration_required": True,
                "real_robot_provider_required": True,
                "sandbox_supported": True,
                "real_robot_execution_allowed": False,
                "sandbox_required": True,
                "provider_required": True,
                "low_speed_first_run_required": True,
                "fault_monitor_required": True,
            },
            "quality": {
                "validation_status": "experimental",
                "xacro_expansion": "passed",
                "urdf_parse": "passed",
                "mesh_resolution": "passed",
                "mujoco_urdf_parse": "not_tested",
                "safety_review": "generated",
            },
            "checksums": {"file": "checksums.json"},
            "tags": [
                "realsense",
                "rgbd",
                "depth-camera",
                "ros2",
                "xacro",
                "imported-from-realsense-ros",
            ],
            "aliases": {f"realsense-{spec.model}": asset_id},
        }
        (output_dir / "manifest.yaml").write_text(
            yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
        )

    def _write_bundle_files(
        self,
        output_dir: Path,
        asset_id: str,
        spec: RealSenseModelSpec,
        urdf_path: Path,
    ) -> None:
        semantic = self._infer_semantic(urdf_path, spec) if urdf_path.exists() else {}
        (output_dir / "semantic.yaml").write_text(
            yaml.safe_dump(semantic, sort_keys=False), encoding="utf-8"
        )

        capabilities = _sensor_capabilities(spec)
        (output_dir / "capabilities.yaml").write_text(
            yaml.safe_dump(capabilities, sort_keys=False), encoding="utf-8"
        )

        safety = _sensor_safety(asset_id)
        (output_dir / "safety.yaml").write_text(
            yaml.safe_dump(safety, sort_keys=False), encoding="utf-8"
        )

        providers = _sensor_providers(spec)
        (output_dir / "providers.yaml").write_text(
            yaml.safe_dump(providers, sort_keys=False), encoding="utf-8"
        )

        sandbox = _sensor_sandbox(asset_id)
        (output_dir / "sandbox.yaml").write_text(
            yaml.safe_dump(sandbox, sort_keys=False), encoding="utf-8"
        )

        calibration = _sensor_calibration_defaults(asset_id)
        (output_dir / "calibration_defaults.yaml").write_text(
            yaml.safe_dump(calibration, sort_keys=False), encoding="utf-8"
        )

        prompts_dir = output_dir / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in _sensor_prompts(asset_id, spec).items():
            (prompts_dir / filename).write_text(content, encoding="utf-8")

        licenses_dir = output_dir / "licenses"
        licenses_dir.mkdir(parents=True, exist_ok=True)
        (licenses_dir / "NOTICE").write_text(
            "This asset was imported from realsenseai/realsense-ros.\n"
            f"Upstream repository: {self._source_info['upstream_url']}\n"
            f"Upstream commit: {self._source_info['upstream_commit']}\n"
            "License: Apache-2.0\n",
            encoding="utf-8",
        )
        third_party = {
            "upstream": self._source_info,
            "license": "Apache-2.0",
            "notes": ["See upstream NOTICE.md for full attribution."],
        }
        (licenses_dir / "THIRD_PARTY.yaml").write_text(
            yaml.safe_dump(third_party, sort_keys=False), encoding="utf-8"
        )

        # Source provenance
        source_dir_meta = output_dir / "source"
        source_dir_meta.mkdir(parents=True, exist_ok=True)
        (source_dir_meta / "upstream_commit.txt").write_text(
            f"{self._source_info['upstream_commit']}\n", encoding="utf-8"
        )
        (source_dir_meta / "upstream_files.yaml").write_text(
            yaml.safe_dump(
                {
                    "macro_file": spec.macro_file,
                    "shared_files": list(SHARED_XACRO_FILES),
                    "extra_files": list(spec.extra_files),
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        # Bundle README
        (output_dir / "README.md").write_text(
            f"# Intel RealSense {spec.model.upper()}\n\n"
            f"Asset ID: `{asset_id}`\n\n"
            "Imported from "
            f"[{self._source_info['upstream_repo']}]("
            f"{self._source_info['upstream_url']}) "
            f"commit `{self._source_info['upstream_commit']}`.\n\n"
            "## Files\n\n"
            "- `model/model.xacro` – e-URDF-Zoo wrapper xacro\n"
            "- `model/model.urdf` – canonical expanded URDF\n"
            "- `model/model_mujoco.urdf` – MuJoCo-friendly URDF\n"
            "- `source/xacro/` – patched upstream xacro source\n"
            "- `meshes/raw/` – raw meshes referenced by the URDF\n"
            "- `meshes/mujoco/` – converted/decimated meshes for MuJoCo\n"
            "- `manifest.yaml`, `semantic.yaml`, `capabilities.yaml`, "
            "`safety.yaml`, `providers.yaml`, `sandbox.yaml`, "
            "`calibration_defaults.yaml`\n"
            "- `prompts/` – system, tools usage, and safety prompts\n"
            "- `validation/` – expansion, parse, mesh, and MuJoCo reports\n\n"
            "## Safety\n\n"
            "This sensor defaults to **experimental** status. "
            "Depth-based safety and visual servoing are blocked until "
            "calibration is validated. See `safety.yaml` and "
            "`capabilities.yaml` for details.\n",
            encoding="utf-8",
        )

    def _infer_semantic(
        self,
        urdf_path: Path,
        spec: RealSenseModelSpec,
    ) -> dict[str, Any]:
        tree = ET.parse(str(urdf_path))
        root = tree.getroot()
        links = {elem.get("name") for elem in root.iter("link") if elem.get("name")}

        def find(suffix: str) -> str | None:
            candidates = [name for name in links if name.endswith(suffix)]
            return candidates[0] if candidates else None

        def find_exact(name: str) -> str | None:
            return name if name in links else None

        mount_link = f"realsense_{spec.model}_mount"
        body = find_exact("camera_link") or find("_link")
        depth_frame = find("_depth_frame")
        depth_optical = find("_depth_optical_frame")
        color_frame = find("_color_frame")
        color_optical = find("_color_optical_frame")
        infra_frames = [
            name
            for name in links
            if name.endswith("_infra1_frame") or name.endswith("_infra2_frame")
        ]
        imu_frames: dict[str, str | None] = {}
        if spec.has_imu:
            imu_frames["accel"] = find("_accel_frame")
            imu_frames["gyro"] = find("_gyro_frame")

        frames: dict[str, Any] = {"root": mount_link, "body": body}
        if depth_frame:
            frames["depth_frame"] = depth_frame
        if depth_optical:
            frames["depth_optical_frame"] = depth_optical
        if color_frame:
            frames["color_frame"] = color_frame
        if color_optical:
            frames["color_optical_frame"] = color_optical
        if infra_frames:
            frames["infra_frames"] = sorted(infra_frames)
        if imu_frames:
            frames["imu_frames"] = {k: v for k, v in imu_frames.items() if v}

        return {
            "schema_version": "e_urdf.semantic.v1",
            "identity": {
                "asset_id": f"sensors/realsense/{spec.model}/default",
                "morphology": "sensor",
                "robot_class": "rgbd_camera",
                "vendor": "Intel RealSense",
                "model": spec.model.upper(),
            },
            "frames": frames,
            "mounting": {
                "attachable": True,
                "compatible_mounts": [
                    "humanoid/head",
                    "humanoid/torso",
                    "mobile_base/front",
                    "manipulator/wrist",
                ],
                "required_calibration": ["extrinsics", "intrinsics", "time_sync"],
            },
            "modalities": spec.modalities,
            "roles": [
                "visual_perception",
                "depth_perception",
                "obstacle_detection",
                "visual_navigation",
                "object_detection",
                "scene_reconstruction",
                "hand_eye_calibration",
            ],
        }

    def _write_e_urdf_compat(self, output_dir: Path) -> None:
        compat = {
            "schema_version": "e_urdf.compat.v1",
            "asset_id": output_dir.name,  # placeholder; overwritten below if known
            "asset_type": "sensor",
            "model": {
                "urdf": "model/model.urdf",
                "xacro": "model/model.xacro",
                "mujoco_urdf": "model/model_mujoco.urdf",
            },
            "semantic": "semantic.yaml",
            "capabilities": "capabilities.yaml",
            "safety": "safety.yaml",
            "providers": "providers.yaml",
            "sandbox": "sandbox.yaml",
            "prompts": {
                "system": "prompts/system.md",
                "tools_usage": "prompts/tools_usage.md",
                "safety": "prompts/safety.md",
            },
        }
        # Best-effort asset id from manifest if already written.
        manifest_path = output_dir / "manifest.yaml"
        if manifest_path.exists():
            try:
                data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
                compat["asset_id"] = data.get("asset", {}).get("id", compat["asset_id"])
            except Exception:  # noqa: BLE001
                pass
        (output_dir / "e_urdf.json").write_text(
            json.dumps(compat, indent=2), encoding="utf-8"
        )


# ----------------------------------------------------------------------
# Sensor-specific metadata templates
# ----------------------------------------------------------------------
def _sensor_capabilities(spec: RealSenseModelSpec) -> dict[str, Any]:
    capabilities = [
        {
            "id": "rgb_observation",
            "name": "RGB Observation",
            "scope": "perception",
            "risk": "low",
            "required_outputs": ["color_image"],
            "calibration_required": False,
            "sandbox_required": False,
            "real_robot_execution_allowed": False,
        },
        {
            "id": "depth_observation",
            "name": "Depth Observation",
            "scope": "perception",
            "risk": "medium",
            "required_outputs": ["depth_image"],
            "calibration_required": True,
            "sandbox_required": False,
            "real_robot_execution_allowed": False,
        },
        {
            "id": "infrared_observation",
            "name": "Infrared Observation",
            "scope": "perception",
            "risk": "medium",
            "required_outputs": ["infrared_image"],
            "calibration_required": True,
            "sandbox_required": False,
            "real_robot_execution_allowed": False,
        },
        {
            "id": "rgbd_scene_understanding",
            "name": "RGB-D Scene Understanding",
            "scope": "perception",
            "risk": "medium",
            "required_outputs": ["color_image", "depth_image", "camera_info"],
            "calibration_required": True,
            "sandbox_required": False,
            "real_robot_execution_allowed": False,
        },
        {
            "id": "visual_navigation",
            "name": "Visual Navigation",
            "scope": "navigation",
            "risk": "high",
            "required_outputs": ["color_image", "depth_image", "camera_info", "tf"],
            "calibration_required": True,
            "requires_body_mount": True,
            "sandbox_required": True,
            "real_robot_execution_allowed": False,
        },
        {
            "id": "depth_collision_avoidance",
            "name": "Depth-based Collision Avoidance",
            "scope": "safety",
            "risk": "critical",
            "required_outputs": ["depth_image", "camera_info", "tf"],
            "calibration_required": True,
            "requires_body_mount": True,
            "sandbox_required": True,
            "human_approval_required": False,
            "real_robot_execution_allowed": False,
        },
        {
            "id": "hand_eye_visual_servo",
            "name": "Hand-eye Visual Servo",
            "scope": "manipulation",
            "risk": "high",
            "required_outputs": ["color_image", "depth_image", "tf"],
            "calibration_required": True,
            "requires_body_mount": True,
            "sandbox_required": True,
            "real_robot_execution_allowed": False,
        },
    ]

    forbidden = [
        {
            "id": "depth_collision_avoidance_without_calibration",
            "description": (
                "Using depth image for real robot collision avoidance without valid "
                "camera intrinsic, extrinsic and TF calibration."
            ),
            "reason": "uncalibrated depth safety risk",
            "severity": "critical",
            "enforcement": {
                "policy_block": True,
                "sandbox_block": True,
                "real_robot_block": True,
            },
        },
        {
            "id": "visual_servo_without_hand_eye_calibration",
            "description": (
                "Using camera feedback for manipulator servoing without "
                "hand-eye calibration."
            ),
            "reason": "unverified camera-to-end-effector transform",
            "severity": "critical",
            "enforcement": {
                "policy_block": True,
                "sandbox_block": True,
                "real_robot_block": True,
            },
        },
    ]

    return {
        "schema_version": "e_urdf.capabilities.v1",
        "capabilities": capabilities,
        "forbidden_capabilities": forbidden,
    }


def _sensor_safety(asset_id: str) -> dict[str, Any]:
    return {
        "schema_version": "e_urdf.safety.v1",
        "safety_status": "experimental",
        "global_policy": {
            "perception_only_allowed": True,
            "real_robot_motion_authorization": False,
            "depth_for_safety_requires_calibration": True,
            "visual_navigation_requires_sandbox": True,
            "visual_servo_requires_hand_eye_calibration": True,
            "real_robot_execution_allowed": False,
            "sandbox_required": True,
            "provider_required": True,
            "calibration_required": True,
            "low_speed_first_run_required": True,
            "fault_monitor_required": True,
        },
        "calibration_policy": {
            "required_for_depth_safety": [
                "camera_intrinsics",
                "depth_scale",
                "camera_to_body_extrinsics",
                "time_sync",
            ],
            "required_for_visual_servo": [
                "camera_intrinsics",
                "camera_to_end_effector_extrinsics",
                "latency_estimate",
            ],
        },
        "runtime_monitors": {
            "required": ["camera_info", "image_timestamp", "tf"],
            "recommended": [
                "camera_temperature",
                "usb_bandwidth",
                "frame_drop_rate",
                "exposure_status",
            ],
        },
        "trajectory_policy": {
            "require_sandbox_first": True,
            "require_low_speed_first": True,
            "require_per_pose_validation": True,
            "max_waypoints_without_human_confirmation": 0,
        },
        "blocked_actions": [
            {
                "id": "depth_collision_avoidance_without_calibration",
                "reason": (
                    "Depth data may be geometrically wrong if extrinsics or "
                    "depth scale are invalid."
                ),
                "scope": ["real_robot", "sandbox"],
            },
            {
                "id": "visual_navigation_without_runtime_camera_health",
                "reason": "Dropped frames or stale TF can make navigation unsafe.",
                "scope": ["real_robot"],
            },
            {
                "id": "hand_eye_servo_without_calibration",
                "reason": (
                    "Manipulator motion based on unverified camera transform "
                    "can collide."
                ),
                "scope": ["real_robot"],
            },
        ],
        "first_real_robot_protocol": {
            "required": True,
            "steps": [
                "Verify camera provider is online.",
                "Verify color/depth/camera_info topics are publishing.",
                "Verify TF tree from camera frame to body root.",
                "Check camera intrinsics and depth scale.",
                "Run static calibration check.",
                "Run sandbox perception replay before motion.",
                "Only allow real robot motion after runtime camera health is nominal.",
            ],
        },
    }


def _sensor_providers(spec: RealSenseModelSpec) -> dict[str, Any]:
    state_required = [
        {
            "id": "color_image",
            "type": "image",
            "required": True,
            "ros2_topic_candidates": [
                "/camera/color/image_raw",
                "/camera/camera/color/image_raw",
                "/<name>/color/image_raw",
            ],
        },
        {
            "id": "depth_image",
            "type": "depth_image",
            "required": True,
            "ros2_topic_candidates": [
                "/camera/depth/image_rect_raw",
                "/camera/camera/depth/image_rect_raw",
                "/<name>/depth/image_rect_raw",
            ],
        },
        {
            "id": "color_camera_info",
            "type": "camera_info",
            "required": True,
            "ros2_topic_candidates": [
                "/camera/color/camera_info",
                "/camera/camera/color/camera_info",
            ],
        },
        {
            "id": "depth_camera_info",
            "type": "camera_info",
            "required": True,
            "ros2_topic_candidates": [
                "/camera/depth/camera_info",
                "/camera/camera/depth/camera_info",
            ],
        },
    ]
    state_optional: list[dict[str, Any]] = [
        {
            "id": "infra1_image",
            "type": "image",
            "required": False,
            "ros2_topic_candidates": ["/camera/infra1/image_rect_raw"],
        },
        {
            "id": "infra2_image",
            "type": "image",
            "required": False,
            "ros2_topic_candidates": ["/camera/infra2/image_rect_raw"],
        },
    ]
    if spec.has_imu:
        state_optional.append(
            {
                "id": "imu",
                "type": "imu",
                "required": False,
                "ros2_topic_candidates": [
                    "/camera/imu",
                    "/camera/camera/imu",
                    "/imu/data",
                ],
            }
        )

    return {
        "schema_version": "e_urdf.providers.v1",
        "provider_interfaces": {
            "state": {
                "required": state_required,
                "optional": state_optional,
            },
            "command": {
                "required": [],
                "optional": [
                    {
                        "id": "set_exposure",
                        "type": "camera_control",
                        "required": False,
                    },
                    {
                        "id": "set_resolution",
                        "type": "camera_control",
                        "required": False,
                    },
                    {
                        "id": "set_depth_profile",
                        "type": "camera_control",
                        "required": False,
                    },
                ],
            },
        },
        "mcp": {
            "recommended_servers": [
                {
                    "id": "realsense-mcp",
                    "roles": [
                        "camera_stream",
                        "depth_stream",
                        "camera_health",
                        "calibration",
                    ],
                }
            ]
        },
    }


def _sensor_sandbox(asset_id: str) -> dict[str, Any]:
    return {
        "schema_version": "e_urdf.sandbox.v1",
        "engines": {
            "ros2": {
                "supported": True,
                "model_path": "model/model.urdf",
                "status": "validated_by_xacro",
            },
            "rviz": {
                "supported": True,
                "model_path": "model/model.urdf",
                "status": "validated_by_xacro",
            },
            "mujoco": {
                "supported": True,
                "model_path": "model/model_mujoco.urdf",
                "status": "experimental",
                "notes": [
                    (
                        "MuJoCo can load the geometry and fixed frames, but "
                        "RGB-D sensor simulation requires engine-specific "
                        "configuration."
                    )
                ],
            },
            "isaac": {
                "supported": False,
                "status": "not_provided_in_realsense_ros",
                "notes": [
                    (
                        "Isaac Sim RealSense USD assets should be added "
                        "separately as reference-only USD assets."
                    )
                ],
            },
        },
        "validation": {
            "required_checks": [
                "xacro_expand",
                "urdf_parse",
                "mesh_exists",
                "fixed_frame_tree",
                "optical_frame_convention",
                "provider_interfaces_present",
                "safety_yaml_complete",
            ]
        },
        "default_test_poses": [
            {
                "id": "nominal_mount",
                "description": "Camera mounted at default origin facing forward",
            }
        ],
    }


def _sensor_calibration_defaults(asset_id: str) -> dict[str, Any]:
    return {
        "schema_version": "e_urdf.calibration_defaults.v1",
        "calibration": {"status": "default", "confidence": 0.0},
        "intrinsics": {
            "color": {"status": "missing", "source": "provider_required"},
            "depth": {"status": "missing", "source": "provider_required"},
        },
        "extrinsics": {
            "camera_to_mount": {"status": "nominal", "source": "expanded_urdf"},
            "camera_to_body": {"status": "missing", "source": "body_attach_required"},
        },
        "depth": {
            "depth_scale": {"status": "provider_required"},
            "min_valid_distance_m": None,
            "max_reliable_distance_m": None,
        },
        "time_sync": {
            "status": "unknown",
            "required_for": [
                "visual_navigation",
                "visual_servo",
                "collision_avoidance",
            ],
        },
    }


def _sensor_prompts(asset_id: str, spec: RealSenseModelSpec) -> dict[str, str]:
    model = spec.model.upper()
    return {
        "system.md": (
            f"# System Prompt: Intel RealSense {model}\n\n"
            "You are configuring the **Intel RealSense "
            f"{model}** ({asset_id}) as a sensor asset in ROSClaw.\n\n"
            "## Role\n"
            "- This is a sensor, not an actuator. "
            "It produces RGB-D/IMU observations.\n"
            "- Default status is **experimental**; "
            "real-robot safety blocks are active.\n"
            "- Always prefer sandbox perception replay "
            "before using depth for motion safety.\n\n"
            "## Default behavior\n"
            "1. Confirm the camera provider is online before using observations.\n"
            "2. Do not use depth for collision avoidance "
            "unless calibration is validated.\n"
            "3. Do not use visual servo without hand-eye calibration.\n"
            "4. Follow the first-real-robot protocol in `safety.yaml`.\n"
        ),
        "tools_usage.md": (
            f"# Tools Usage: Intel RealSense {model}\n\n"
            "Use ROS topic/service tools to interact with this camera:\n\n"
            "- **Color image**: `/camera/color/image_raw`\n"
            "- **Depth image**: `/camera/depth/image_rect_raw`\n"
            "- **Camera info**: `/camera/color/camera_info`, "
            "`/camera/depth/camera_info`\n"
            "- **IMU** (if available): `/camera/imu`\n\n"
            "Always verify `camera_info`, TF, and timestamps before using "
            "observations for safety-critical decisions.\n"
        ),
        "safety.md": (
            f"# Safety: Intel RealSense {model}\n\n"
            "This asset defaults to **experimental** status with the "
            "following blocks:\n\n"
            "- `real_robot_execution_allowed: false` "
            "(no motion authorized from the camera itself)\n"
            "- `sandbox_required: true` for visual navigation "
            "and depth-based safety\n"
            "- Blocked: `depth_collision_avoidance_without_calibration`, "
            "`visual_servo_without_hand_eye_calibration`\n\n"
            "Promote to `validated` only after completing camera "
            "intrinsics/extrinsics calibration and runtime health checks.\n"
        ),
    }
