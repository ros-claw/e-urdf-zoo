"""Common URDF parsing and mesh handling utilities."""

from __future__ import annotations

import hashlib
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def parse_urdf(path: Path) -> ET.ElementTree:
    """Parse a URDF file into an ElementTree."""
    return ET.parse(str(path))


def collect_mesh_refs(tree: ET.ElementTree) -> list[tuple[ET.Element, str, str]]:
    """Collect all mesh filename references in a URDF tree.

    Returns a list of (element, old_filename, mesh_basename) tuples.
    """
    refs: list[tuple[ET.Element, str, str]] = []
    for elem in tree.iter("mesh"):
        filename = elem.get("filename")
        if not filename:
            continue
        basename = Path(filename).name
        refs.append((elem, filename, basename))
    return refs


def resolve_mesh_path(urdf_path: Path, mesh_ref: str) -> Path | None:
    """Resolve a mesh reference relative to the URDF file."""
    if Path(mesh_ref).is_absolute():
        return Path(mesh_ref)
    candidate = urdf_path.parent / mesh_ref
    if candidate.exists():
        return candidate
    # Some URDFs use package:// paths; try the basename as a fallback.
    candidate = urdf_path.parent / Path(mesh_ref).name
    if candidate.exists():
        return candidate
    return None


def copy_meshes(
    urdf_path: Path,
    tree: ET.ElementTree,
    dest_meshes_dir: Path,
    preserve_structure: bool = True,
) -> dict[str, Path]:
    """Copy referenced meshes into the destination and return a mapping.

    Returns a dict mapping old mesh references to new relative paths from the
    model/model.urdf file.
    """
    copied: dict[str, Path] = {}
    refs = collect_mesh_refs(tree)
    for elem, old_ref, basename in refs:
        source = resolve_mesh_path(urdf_path, old_ref)
        if source is None:
            continue

        if preserve_structure:
            # Preserve relative subdirectories under the original meshes/ folder
            # inside the destination meshes/raw/ tree.
            try:
                rel = source.relative_to(urdf_path.parent)
            except ValueError:
                rel = Path(basename)
            # Strip a leading "meshes" directory to avoid duplicated path segments.
            if rel.parts and rel.parts[0] == "meshes":
                rel = Path(*rel.parts[1:])
            target = dest_meshes_dir / "raw" / rel
        else:
            target = dest_meshes_dir / "raw" / basename

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

        new_rel = Path("..") / "meshes" / target.relative_to(dest_meshes_dir)
        copied[old_ref] = new_rel
    return copied


def rewrite_mesh_paths(
    tree: ET.ElementTree,
    path_map: dict[str, Path],
) -> None:
    """Rewrite mesh filenames in-place using the path map."""
    for elem in tree.iter("mesh"):
        filename = elem.get("filename")
        if filename and filename in path_map:
            elem.set("filename", str(path_map[filename]).replace("\\", "/"))


def write_urdf(tree: ET.ElementTree, path: Path) -> None:
    """Write an ElementTree to a URDF file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(str(path), encoding="utf-8", xml_declaration=True)


def file_checksum(path: Path, algorithm: str = "sha256") -> str:
    """Compute a checksum for a single file."""
    h = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_checksums(base_dir: Path) -> dict[str, Any]:
    """Compute SHA-256 checksums for all files under base_dir."""
    checksums: dict[str, Any] = {
        "algorithm": "sha256",
        "files": {},
    }
    for path in sorted(base_dir.rglob("*")):
        if path.is_file():
            rel = path.relative_to(base_dir).as_posix()
            checksums["files"][rel] = file_checksum(path)
    return checksums
