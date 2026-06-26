"""Bulk importer for dexsuite/dex-urdf assets."""

from __future__ import annotations

import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .calibration_template import default_calibration_defaults
from .capability_template import default_capabilities
from .prompt_templates import default_prompts
from .provider_template import default_providers
from .safety_template import default_safety
from .sandbox_template import default_sandbox
from .semantic_infer import infer_semantics
from .urdf_common import (
    compute_checksums,
    copy_meshes,
    parse_urdf,
    rewrite_mesh_paths,
    write_urdf,
)


FAMILY_CATEGORY_MAP: dict[str, str] = {
    "allegro_hand": "dexhands",
    "shadow_hand": "dexhands",
    "schunk_hand": "dexhands",
    "ability_hand": "dexhands",
    "leap_hand": "dexhands",
    "dclaw_gripper": "dexhands",
    "barrett_hand": "dexhands",
    "inspire_hand": "dexhands",
    "panda_gripper": "grippers",
}

FAMILY_MODEL_MAP: dict[str, str] = {
    "allegro_hand": "allegro_hand",
    "shadow_hand": "shadow_hand",
    "schunk_hand": "schunk_svh",
    "ability_hand": "ability_hand",
    "leap_hand": "leap_hand",
    "dclaw_gripper": "dclaw",
    "barrett_hand": "barrett_hand",
    "inspire_hand": "inspire_hand",
    "panda_gripper": "panda",
}

FAMILY_VENDOR_MAP: dict[str, str] = {
    "allegro_hand": "SimLab / Wonik Robotics",
    "shadow_hand": "Shadow Robot Company",
    "schunk_hand": "SCHUNK",
    "ability_hand": "Psyonic",
    "leap_hand": "Leap Motion / Ultraleap",
    "dclaw_gripper": "Google Robotics",
    "barrett_hand": "Barrett Technology",
    "inspire_hand": "Inspire Robots",
    "panda_gripper": "Franka Emika",
}


@dataclass
class ImportedAsset:
    """Result of importing one dex-urdf asset."""

    asset_id: str
    source_urdf: Path
    output_path: Path
    status: str = "success"
    messages: list[str] = field(default_factory=list)


class DexUrdfImporter:
    """Import dexsuite/dex-urdf models into the e-urdf-zoo bundle format."""

    def __init__(
        self,
        source_dir: Path | str,
        output_dir: Path | str,
        copy_assets: bool = True,
        generate_safety: bool = True,
        generate_prompts: bool = True,
    ):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.copy_assets = copy_assets
        self.generate_safety = generate_safety
        self.generate_prompts = generate_prompts
        self._source_info = self._detect_source_info()

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------
    def _detect_source_info(self) -> dict[str, str]:
        """Try to extract git metadata from the dex-urdf checkout."""
        info = {
            "type": "third_party_import",
            "upstream_repo": "https://github.com/dexsuite/dex-urdf",
            "upstream_url": "https://github.com/dexsuite/dex-urdf",
            "upstream_commit": "unknown",
            "upstream_path": str(self.source_dir),
            "imported_at": "",
            "importer": "e_urdf_zoo.importers.dex_urdf",
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

    def find_supported_models(self) -> list[dict[str, Any]]:
        """Find supported model families under robots/hands."""
        hands_dir = self.source_dir / "robots" / "hands"
        if not hands_dir.exists():
            return []

        models: list[dict[str, Any]] = []
        for family_dir in sorted(hands_dir.iterdir()):
            if not family_dir.is_dir():
                continue
            family = family_dir.name
            if family not in FAMILY_CATEGORY_MAP:
                continue
            urdfs = self._select_urdfs(family_dir)
            for urdf_path, side, variant in urdfs:
                category = FAMILY_CATEGORY_MAP[family]
                model = FAMILY_MODEL_MAP[family]
                asset_id = f"{category}/{model}/{variant}"
                models.append(
                    {
                        "asset_id": asset_id,
                        "family": family,
                        "category": category,
                        "model": model,
                        "variant": variant,
                        "side": side,
                        "urdf_path": urdf_path,
                    }
                )
        return models

    def _select_urdfs(self, family_dir: Path) -> list[tuple[Path, str, str]]:
        """Select the canonical URDF files for a model family.

        Prefers plain ``.urdf`` over ``*_glb.urdf`` and skips xacro unless
        explicitly handled later.
        """
        candidates: list[tuple[Path, str, str]] = []
        for urdf_path in sorted(family_dir.rglob("*.urdf")):
            name = urdf_path.stem
            # Skip glb variants in favor of plain URDFs.
            if name.endswith("_glb"):
                # Only use glb if no plain variant exists for this side.
                plain_name = name[:-4]
                plain_path = urdf_path.with_name(plain_name + ".urdf")
                if plain_path.exists():
                    continue
                side, variant = self._parse_variant(plain_name)
            else:
                side, variant = self._parse_variant(name)

            candidates.append((urdf_path, side, variant))

        # De-duplicate by side/variant, preferring plain URDFs.
        seen: dict[tuple[str, str], Path] = {}
        for urdf_path, side, variant in candidates:
            key = (side, variant)
            if key not in seen:
                seen[key] = urdf_path
        return [(path, side, variant) for (side, variant), path in seen.items()]

    def _parse_variant(self, name: str) -> tuple[str, str]:
        """Infer side (left/right) and variant from a URDF basename."""
        lower = name.lower()
        if "left" in lower:
            side = "left"
        elif "right" in lower:
            side = "right"
        else:
            side = "unspecified"

        # Some families have a default/no-side model; treat as default variant.
        if self._is_default_family(name):
            return (side, "default")
        return (side, side)

    def _is_default_family(self, name: str) -> bool:
        lower = name.lower()
        return "dclaw" in lower or "barrett" in lower or "panda" in lower

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------
    def import_all(self) -> list[ImportedAsset]:
        """Import all supported models."""
        results: list[ImportedAsset] = []
        for model in self.find_supported_models():
            result = self.import_one(
                model["asset_id"],
                model["urdf_path"],
                model["category"],
                model["model"],
                model["variant"],
            )
            results.append(result)
        return results

    def import_one(
        self,
        asset_id: str,
        urdf_path: Path | str,
        category: str,
        model: str,
        variant: str,
    ) -> ImportedAsset:
        """Import a single URDF into the zoo bundle format."""
        urdf_path = Path(urdf_path)
        output_path = self.output_dir / asset_id
        output_path.mkdir(parents=True, exist_ok=True)

        messages: list[str] = []

        # Model directory
        model_dir = output_path / "model"
        model_dir.mkdir(parents=True, exist_ok=True)

        # Parse and copy meshes
        tree = parse_urdf(urdf_path)
        mesh_refs = self._collect_mesh_refs(tree)
        missing: list[str] = []
        if self.copy_assets:
            meshes_dir = output_path / "meshes"
            meshes_dir.mkdir(parents=True, exist_ok=True)
            path_map = copy_meshes(urdf_path, tree, meshes_dir, preserve_structure=True)
            rewrite_mesh_paths(tree, path_map)
            missing = [old for old in mesh_refs if old not in path_map]
            if missing:
                messages.append(f"Missing meshes: {missing}")

        # Write rewritten URDF
        dest_urdf = model_dir / "model.urdf"
        write_urdf(tree, dest_urdf)

        # Manifest and bundle files
        self._write_manifest(
            output_path,
            asset_id,
            urdf_path,
            category,
            model,
            variant,
        )
        self._write_bundle_files(output_path, asset_id, category, urdf_path, tree)

        # Checksums
        checksums = compute_checksums(output_path)
        (output_path / "checksums.json").write_text(
            json.dumps(checksums, indent=2), encoding="utf-8"
        )

        return ImportedAsset(
            asset_id=asset_id,
            source_urdf=urdf_path,
            output_path=output_path,
            status="success" if not missing else "success_with_warnings",
            messages=messages,
        )

    def _collect_mesh_refs(self, tree: ET.ElementTree) -> list[str]:
        return [
            elem.get("filename")
            for elem in tree.iter("mesh")
            if elem.get("filename")
        ]

    def _write_manifest(
        self,
        output_path: Path,
        asset_id: str,
        urdf_path: Path,
        category: str,
        model: str,
        variant: str,
    ) -> None:
        family = next(
            (k for k, v in FAMILY_MODEL_MAP.items() if v == model),
            model,
        )
        manifest: dict[str, Any] = {
            "schema_version": "e_urdf.asset.v1",
            "asset": {
                "id": asset_id,
                "name": self._display_name(family, variant),
                "version": "0.1.0",
                "status": "experimental",
                "category": category,
                "vendor": FAMILY_VENDOR_MAP.get(family, "unknown"),
                "model": model,
                "variant": variant,
                "description": f"Imported {family} from dexsuite/dex-urdf",
            },
            "source": self._source_info,
            "license": {
                "repo_declared_license": "MIT",
                "upstream_model_license": "unknown",
                "source_url": self._source_info["upstream_url"],
                "source_commit": self._source_info["upstream_commit"],
                "import_blocking": False,
                "display_warning": True,
                "commercial_review_recommended": True,
                "notes": ["License metadata should be reviewed against upstream before commercial use."],
            },
            "model": {
                "primary_format": "urdf",
                "urdf": "model/model.urdf",
                "meshes_dir": "meshes/",
            },
            "robot": {
                "morphology": "end_effector",
                "robot_class": "hand" if category == "dexhands" else "gripper",
                "side": variant if variant in {"left", "right"} else None,
            },
            "runtime_policy": {
                "real_robot_execution_allowed": False,
                "sandbox_required": True,
                "provider_required": True,
                "calibration_required": True,
                "low_speed_first_run_required": True,
                "fault_monitor_required": True,
            },
        }
        (output_path / "manifest.yaml").write_text(
            yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
        )

    def _display_name(self, family: str, variant: str) -> str:
        base = " ".join(word.capitalize() for word in family.split("_"))
        if variant == "default":
            return base
        return f"{base} ({variant.capitalize()})"

    def _write_bundle_files(
        self,
        output_path: Path,
        asset_id: str,
        category: str,
        urdf_path: Path,
        tree: ET.ElementTree,
    ) -> None:
        # Semantic
        semantic = infer_semantics(urdf_path, tree, category)
        (output_path / "semantic.yaml").write_text(
            yaml.safe_dump(semantic, sort_keys=False), encoding="utf-8"
        )

        # Capabilities
        capabilities = default_capabilities(category)
        (output_path / "capabilities.yaml").write_text(
            yaml.safe_dump(capabilities, sort_keys=False), encoding="utf-8"
        )

        # Safety
        if self.generate_safety:
            safety = default_safety(asset_id)
            (output_path / "safety.yaml").write_text(
                yaml.safe_dump(safety, sort_keys=False), encoding="utf-8"
            )

        # Providers
        providers = default_providers(asset_id)
        (output_path / "providers.yaml").write_text(
            yaml.safe_dump(providers, sort_keys=False), encoding="utf-8"
        )

        # Sandbox
        sandbox = default_sandbox(asset_id)
        (output_path / "sandbox.yaml").write_text(
            yaml.safe_dump(sandbox, sort_keys=False), encoding="utf-8"
        )

        # Calibration defaults
        calibration = default_calibration_defaults(asset_id)
        (output_path / "calibration_defaults.yaml").write_text(
            yaml.safe_dump(calibration, sort_keys=False), encoding="utf-8"
        )

        # Prompts
        if self.generate_prompts:
            prompts_dir = output_path / "prompts"
            prompts_dir.mkdir(parents=True, exist_ok=True)
            prompts = default_prompts(asset_id, asset_id)
            for filename, content in prompts.items():
                (prompts_dir / filename).write_text(content, encoding="utf-8")

        # License stubs
        licenses_dir = output_path / "licenses"
        licenses_dir.mkdir(parents=True, exist_ok=True)
        (licenses_dir / "NOTICE").write_text(
            f"This asset was imported from dexsuite/dex-urdf.\n"
            f"Upstream repository: {self._source_info['upstream_url']}\n"
            f"Upstream commit: {self._source_info['upstream_commit']}\n",
            encoding="utf-8",
        )
        third_party = {
            "upstream": self._source_info,
            "license": "unknown",
            "notes": ["Review upstream license before commercial use."],
        }
        (licenses_dir / "THIRD_PARTY.yaml").write_text(
            yaml.safe_dump(third_party, sort_keys=False), encoding="utf-8"
        )
