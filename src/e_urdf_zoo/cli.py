#!/usr/bin/env python3
"""CLI for e-URDF-Zoo."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from . import (
    __version__,
    get_robot_info,
    list_robots,
    load_embodiment,
)
from .importers.dex_urdf import DexUrdfImporter
from .index import AssetIndex
from .loader import AssetLoader
from .schemas import ValidationStatus
from .validator import AssetValidator

console = Console()


def _asset_table(summaries: list) -> Table:
    table = Table(title="e-URDF-Zoo Assets")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name")
    table.add_column("Category")
    table.add_column("Version")
    table.add_column("Status")
    table.add_column("Layout")
    for s in summaries:
        layout = "legacy" if s.is_legacy else "manifest"
        table.add_row(s.id, s.name, s.category, s.version, s.status, layout)
    return table


def cmd_list(args: argparse.Namespace) -> int:
    """List available assets."""
    loader = AssetLoader()
    summaries = loader.list_assets(category=args.category)

    if not summaries:
        console.print("No assets found in e-URDF-Zoo.")
        return 1

    if args.format == "json":
        print(
            json.dumps(
                [
                    {
                        "id": s.id,
                        "name": s.name,
                        "category": s.category,
                        "version": s.version,
                        "status": s.status,
                        "is_legacy": s.is_legacy,
                        "path": str(s.path),
                    }
                    for s in summaries
                ],
                indent=2,
            )
        )
    else:
        console.print(_asset_table(summaries))
        console.print(f"\nTotal: {len(summaries)} assets")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Show detailed asset information."""
    try:
        asset = load_embodiment(args.asset_id)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}", stderr=True)
        return 1

    console.print(f"\n[bold]{'='*60}[/bold]")
    console.print(f"  {asset.name}")
    console.print(f"[bold]{'='*60}[/bold]\n")

    console.print(f"ID: {asset.asset_id}")
    console.print(f"Version: {asset.version}")
    console.print(f"Category: {asset.category}")
    console.print(f"Type: {asset.robot_type}")
    console.print(f"DOF: {asset.dof}")
    console.print(f"Status: {asset.status}")
    console.print(f"Layout: {'manifest' if asset.is_manifest else 'legacy'}")

    if asset.is_manifest:
        manifest = asset.manifest
        console.print(f"\nVendor: {manifest.asset.vendor}")
        console.print(f"Model: {manifest.asset.model}")
        console.print(f"Variant: {manifest.asset.variant}")
        console.print(f"Description: {manifest.asset.description or 'N/A'}")
        console.print(
            f"\nSandbox required: {manifest.runtime_policy.sandbox_required}"
        )
        console.print(
            f"Real robot execution allowed: "
            f"{manifest.runtime_policy.real_robot_execution_allowed}"
        )
        if asset.capabilities:
            console.print("\nCapabilities:")
            for cap in asset.capabilities.capabilities:
                console.print(f"  - {cap.name} ({cap.risk})")
            if asset.capabilities.forbidden_capabilities:
                console.print("\nForbidden capabilities:")
                for fc in asset.capabilities.forbidden_capabilities:
                    console.print(f"  - {fc.id}: {fc.description}")
    else:
        config = asset.config
        meta = config.get("meta", {})
        console.print(f"\nManufacturer: {meta.get('manufacturer', 'N/A')}")
        console.print(f"Model: {meta.get('model', 'N/A')}")
        console.print(f"Description: {meta.get('description', 'N/A')}")

    console.print(f"\nAsset Location: {asset.base_path}")

    if args.show_prompts:
        console.print(f"\n[bold]SYSTEM PROMPT (first 500 chars)[/bold]\n")
        console.print(asset.system_prompt[:500] + "...")

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate an asset bundle."""
    target = args.target
    if Path(target).exists() or "/" not in target:
        # If it looks like a file/directory path, validate it directly.
        if Path(target).exists():
            report = AssetValidator().validate_path(Path(target))
        else:
            try:
                report = AssetValidator().validate(target)
            except FileNotFoundError as e:
                console.print(f"[red]Error:[/red] {e}")
                return 1
    else:
        try:
            report = AssetValidator().validate(target)
        except FileNotFoundError as e:
            console.print(f"[red]Error:[/red] {e}")
            return 1

    if args.format == "json":
        print(json.dumps(report.to_dict(), indent=2))
        return 0 if report.overall != ValidationStatus.FAIL.value else 1

    color = {
        ValidationStatus.PASS.value: "green",
        ValidationStatus.PASS_WITH_WARNINGS.value: "yellow",
        ValidationStatus.FAIL.value: "red",
    }.get(report.overall, "white")
    console.print(
        f"\n[bold {color}]Validation: {report.overall}[/bold {color}] "
        f"for {report.asset_id}"
    )

    if report.results:
        table = Table(title="File-level results")
        table.add_column("File")
        table.add_column("Status")
        table.add_column("Messages")
        for filename, result in report.results.items():
            status_color = {
                ValidationStatus.PASS: "green",
                ValidationStatus.PASS_WITH_WARNINGS: "yellow",
                ValidationStatus.FAIL: "red",
            }.get(result.status, "white")
            msg_summary = "\n".join(
                f"{m.level}: {m.message}" for m in result.messages
            )
            table.add_row(
                filename,
                f"[{status_color}]{result.status.value}[/{status_color}]",
                msg_summary or "ok",
            )
        console.print(table)

    if report.messages:
        console.print("\n[bold]Messages:[/bold]")
        for msg in report.messages:
            level_color = "yellow" if msg.get("level") == "warning" else "red"
            console.print(f"  [{level_color}]{msg['level']}:[/{level_color}] {msg['message']}")

    return 0 if report.overall != ValidationStatus.FAIL.value else 1


def cmd_index(args: argparse.Namespace) -> int:
    """Build or query the asset index."""
    if args.index_command == "build":
        index = AssetIndex().build()
        paths = index.save(output_dir=args.output)
        console.print(f"[green]Index built[/green]:")
        console.print(f"  JSON: {paths['json']}")
        console.print(f"  YAML: {paths['yaml']}")
        return 0

    console.print(f"[red]Unknown index command: {args.index_command}[/red]")
    return 1


def cmd_import_urdf(args: argparse.Namespace) -> int:
    """Import a single URDF into the zoo (placeholder for Phase 3)."""
    console.print(
        "[yellow]URDF importer is not yet implemented. "
        "Use 'import dex-urdf' for dexsuite/dex-urdf bulk import.[/yellow]"
    )
    return 1


def cmd_import_dex_urdf(args: argparse.Namespace) -> int:
    """Bulk import dexsuite/dex-urdf assets."""
    importer = DexUrdfImporter(
        source_dir=args.source,
        output_dir=args.output,
        copy_assets=args.copy_assets,
        generate_safety=True,
        generate_prompts=True,
    )
    results = importer.import_all()

    success = [r for r in results if r.status == "success"]
    warned = [r for r in results if r.status == "success_with_warnings"]
    failed = [r for r in results if r.status.startswith("failed")]

    console.print(f"[green]Imported {len(success)} assets[/green]")
    if warned:
        console.print(f"[yellow]{len(warned)} assets imported with warnings[/yellow]")
    if failed:
        console.print(f"[red]{len(failed)} assets failed[/red]")

    for result in results:
        color = {
            "success": "green",
            "success_with_warnings": "yellow",
        }.get(result.status, "red")
        console.print(f"  [{color}]{result.status}[/{color}] {result.asset_id}")
        for msg in result.messages:
            console.print(f"    [yellow]warning: {msg}[/yellow]")

    return 0 if not failed else 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="e-urdf-zoo",
        description="e-URDF-Zoo: The Official Device Driver Hub for ROSClaw",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--zoo-path",
        type=Path,
        help="Path to e-URDF-Zoo robots directory (overrides env var)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List available assets")
    list_parser.add_argument(
        "--category", help="Filter by category (e.g., dexhands, humanoid)"
    )
    list_parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format",
    )
    list_parser.set_defaults(func=cmd_list)

    # Info command
    info_parser = subparsers.add_parser("info", help="Show asset details")
    info_parser.add_argument(
        "asset_id", help="Asset identifier (e.g., dexhands/inspire_hand/right)"
    )
    info_parser.add_argument(
        "--show-prompts", action="store_true", help="Show system prompt preview"
    )
    info_parser.set_defaults(func=cmd_info)

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate", help="Validate an asset bundle"
    )
    validate_parser.add_argument(
        "target",
        help="Asset ID or path to asset directory/e_urdf.json",
    )
    validate_parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format",
    )
    validate_parser.set_defaults(func=cmd_validate)

    # Index command
    index_parser = subparsers.add_parser("index", help="Manage the asset index")
    index_sub = index_parser.add_subparsers(
        dest="index_command", help="Index operations"
    )
    index_build = index_sub.add_parser("build", help="Build the asset index")
    index_build.add_argument(
        "--output",
        type=Path,
        help="Directory to write index.json / index.yaml",
    )
    index_build.set_defaults(func=cmd_index)

    # Import commands (placeholders for Phase 3)
    import_parser = subparsers.add_parser(
        "import", help="Import third-party robot models"
    )
    import_sub = import_parser.add_subparsers(
        dest="import_command", help="Import sources"
    )

    import_urdf = import_sub.add_parser("urdf", help="Import a single URDF")
    import_urdf.add_argument("--urdf", required=True, help="Path to URDF file")
    import_urdf.add_argument("--asset-id", required=True, help="Asset ID")
    import_urdf.add_argument("--category", default="unknown")
    import_urdf.add_argument("--output", type=Path, required=True)
    import_urdf.set_defaults(func=cmd_import_urdf)

    import_dex = import_sub.add_parser(
        "dex-urdf", help="Bulk import dexsuite/dex-urdf"
    )
    import_dex.add_argument(
        "--source", required=True, help="Path to dex-urdf checkout"
    )
    import_dex.add_argument(
        "--output", type=Path, required=True, help="Output directory"
    )
    import_dex.add_argument(
        "--all", action="store_true", help="Import all supported models"
    )
    import_dex.add_argument(
        "--copy-assets", action="store_true", help="Copy meshes into the zoo"
    )
    import_dex.set_defaults(func=cmd_import_dex_urdf)

    args = parser.parse_args()

    if args.zoo_path:
        import os

        os.environ["E_URDF_ZOO_PATH"] = str(args.zoo_path.parent)

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
