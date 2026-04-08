#!/usr/bin/env python3
"""CLI for e-URDF-Zoo."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, get_robot_info, list_robots, load_embodiment


def cmd_list(args: argparse.Namespace) -> int:
    """List available robots."""
    robots = list_robots()

    if not robots:
        print("No robots found in e-URDF-Zoo.")
        return 1

    print(f"\ne-URDF-Zoo v{__version__} - Available Robots:\n")
    print(f"{'ID':<30} {'Name':<35} {'Type':<15} {'DOF':>5}")
    print("-" * 90)

    for robot_id in robots:
        try:
            info = get_robot_info(robot_id)
            print(
                f"{info['id']:<30} "
                f"{info['name'][:34]:<35} "
                f"{info['type']:<15} "
                f"{info['dof']:>5}"
            )
        except Exception as e:
            print(f"{robot_id:<30} (Error loading: {e})")

    print(f"\nTotal: {len(robots)} robots")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Show detailed robot information."""
    try:
        asset = load_embodiment(args.robot_id)
        config = asset.config

        print(f"\n{'='*60}")
        print(f"  {config.get('embodiment_name', args.robot_id)}")
        print(f"{'='*60}\n")

        print(f"ID: {config.get('embodiment_id', 'N/A')}")
        print(f"Version: {config.get('version', 'N/A')}")
        print(f"Type: {asset.robot_type}")
        print(f"DOF: {asset.dof}")

        meta = config.get("meta", {})
        print(f"\nManufacturer: {meta.get('manufacturer', 'N/A')}")
        print(f"Model: {meta.get('model', 'N/A')}")
        print(f"Description: {meta.get('description', 'N/A')}")

        semantics = config.get("semantics", {})
        print(f"\nAffordances:")
        for aff in semantics.get("affordances", []):
            print(f"  - {aff}")

        firewall = config.get("physical_firewall", {})
        print(f"\nSafety Configuration:")
        print(f"  Engine: {firewall.get('engine', 'N/A')}")
        print(f"  Validation: {firewall.get('validation_level', 'N/A')}")
        print(f"  Sim Horizon: {firewall.get('max_simulation_horizon_sec', 'N/A')}s")
        print(f"  Speed Factor: {firewall.get('speed_up_factor', 'N/A')}x")

        constraints = firewall.get("constraints", {})
        print(f"\nEnabled Checks:")
        for check, enabled in constraints.items():
            status = "✓" if enabled else "✗"
            print(f"  [{status}] {check}")

        print(f"\nAsset Location: {asset.base_path}")

        if args.show_prompts:
            print(f"\n{'='*60}")
            print("  SYSTEM PROMPT (first 500 chars)")
            print(f"{'='*60}\n")
            print(asset.system_prompt[:500] + "...")

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate e_urdf.json file."""
    import json

    path = Path(args.config)
    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        return 1

    try:
        with open(path) as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        return 1

    # Required fields
    required = ["embodiment_id", "embodiment_name", "kinematics", "semantics"]
    missing = [f for f in required if f not in config]

    if missing:
        print(f"Error: Missing required fields: {missing}", file=sys.stderr)
        return 1

    print(f"✓ Valid e_urdf.json: {path}")
    print(f"  Robot: {config.get('embodiment_name')}")
    print(f"  ID: {config.get('embodiment_id')}")
    print(f"  Type: {config.get('semantics', {}).get('robot_type', 'unknown')}")

    return 0


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
    list_parser = subparsers.add_parser("list", help="List available robots")
    list_parser.set_defaults(func=cmd_list)

    # Info command
    info_parser = subparsers.add_parser("info", help="Show robot details")
    info_parser.add_argument("robot_id", help="Robot identifier (e.g., universal_robots_ur5e)")
    info_parser.add_argument(
        "--show-prompts", action="store_true", help="Show system prompt preview"
    )
    info_parser.set_defaults(func=cmd_info)

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate e_urdf.json")
    validate_parser.add_argument("config", help="Path to e_urdf.json")
    validate_parser.set_defaults(func=cmd_validate)

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
