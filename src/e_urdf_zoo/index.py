"""Index builder and search for the e-URDF-Zoo asset library."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .loader import AssetLoader
from .models import AssetSummary


class AssetIndex:
    """Persistent index of all assets in the zoo."""

    DEFAULT_NAME = "index"

    def __init__(self, zoo_path: Path | str | None = None):
        self.loader = AssetLoader(zoo_path)
        self.entries: list[AssetSummary] = []
        self.aliases: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Build / save / load
    # ------------------------------------------------------------------
    def build(self) -> "AssetIndex":
        """Discover all assets and build the in-memory index."""
        self.entries = self.loader.list_assets()
        self.aliases = {}
        for entry in self.entries:
            for alias in entry.aliases:
                self.aliases[alias] = entry.id
        return self

    def save(
        self,
        output_dir: Path | str | None = None,
        name: str = DEFAULT_NAME,
    ) -> dict[str, Path]:
        """Save the index as JSON and YAML."""
        if output_dir is None:
            output_dir = self.loader.zoo_path.parent
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        data = self.to_dict()
        json_path = output_dir / f"{name}.json"
        yaml_path = output_dir / f"{name}.yaml"

        json_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        yaml_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

        return {"json": json_path, "yaml": yaml_path}

    def load(self, index_path: Path | str) -> "AssetIndex":
        """Load an existing index file (JSON or YAML)."""
        path = Path(index_path)
        text = path.read_text(encoding="utf-8")
        if path.suffix in {".yaml", ".yml"}:
            data = yaml.safe_load(text) or {}
        else:
            data = json.loads(text)

        self.entries = [AssetSummary(**entry) for entry in data.get("entries", [])]
        self.aliases = data.get("aliases", {})
        for entry in self.entries:
            entry.path = Path(entry.path)
        return self

    def to_dict(self) -> dict[str, Any]:
        """Serialize the index as a dictionary."""
        return {
            "schema_version": "e_urdf.index.v1",
            "zoo_path": str(self.loader.zoo_path),
            "count": len(self.entries),
            "entries": [
                {
                    "id": entry.id,
                    "name": entry.name,
                    "category": entry.category,
                    "path": str(entry.path),
                    "status": entry.status,
                    "version": entry.version,
                    "is_legacy": entry.is_legacy,
                    "aliases": entry.aliases,
                }
                for entry in self.entries
            ],
            "aliases": self.aliases,
        }

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def lookup(self, asset_id_or_alias: str) -> AssetSummary | None:
        """Look up an entry by exact ID or alias."""
        for entry in self.entries:
            if entry.id == asset_id_or_alias:
                return entry
        canonical = self.aliases.get(asset_id_or_alias)
        if canonical:
            for entry in self.entries:
                if entry.id == canonical:
                    return entry
        return None

    def by_category(self, category: str) -> list[AssetSummary]:
        return [e for e in self.entries if e.category == category]

    def search(self, query: str) -> list[AssetSummary]:
        query_lower = query.lower()
        return [
            e
            for e in self.entries
            if query_lower in e.id.lower()
            or query_lower in e.name.lower()
            or query_lower in e.category.lower()
            or any(query_lower in a.lower() for a in e.aliases)
        ]
