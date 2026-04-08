"""e-URDF-Zoo: The Official Device Driver Hub for ROSClaw.

This package provides semantic robot model definitions for AI agents,
combining physical models (MuJoCo) with safety configurations and LLM prompts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

__version__ = "0.1.0"
__all__ = ["load_embodiment", "list_robots", "EmbodimentAsset"]


class EmbodimentAsset:
    """Represents a complete robot embodiment asset bundle."""

    def __init__(self, robot_id: str, base_path: Path):
        self.robot_id = robot_id
        self.base_path = base_path
        self._config: dict[str, Any] | None = None

    @property
    def config(self) -> dict[str, Any]:
        """Load and return e_urdf.json configuration."""
        if self._config is None:
            config_path = self.base_path / "e_urdf.json"
            with open(config_path) as f:
                self._config = json.load(f)
        return self._config

    @property
    def model_xml(self) -> Path:
        """Return path to model.xml."""
        return self.base_path / "model.xml"

    @property
    def system_prompt(self) -> str:
        """Load and return system prompt."""
        prompt_path = self.base_path / "prompts" / "system.md"
        with open(prompt_path) as f:
            return f.read()

    @property
    def tools_usage(self) -> str:
        """Load and return tools usage guide."""
        guide_path = self.base_path / "prompts" / "tools_usage.md"
        with open(guide_path) as f:
            return f.read()

    @property
    def name(self) -> str:
        """Return embodiment name."""
        return self.config.get("embodiment_name", self.robot_id)

    @property
    def robot_type(self) -> str:
        """Return robot type."""
        return self.config.get("semantics", {}).get("robot_type", "unknown")

    @property
    def dof(self) -> int:
        """Return degrees of freedom."""
        return self.config.get("kinematics", {}).get("dof", 0)

    def __repr__(self) -> str:
        return f"EmbodimentAsset({self.robot_id}: {self.name}, {self.dof} DOF)"


def get_zoo_path() -> Path:
    """Get the path to the e-URDF-Zoo robots directory."""
    # Check environment variable first
    import os

    if path := os.environ.get("E_URDF_ZOO_PATH"):
        return Path(path) / "robots"

    # Default to package location
    package_dir = Path(__file__).parent.parent.parent
    return package_dir / "robots"


def list_robots() -> list[str]:
    """List all available robot embodiments in the zoo.

    Returns:
        List of robot IDs (directory names).
    """
    zoo_path = get_zoo_path()

    if not zoo_path.exists():
        return []

    return sorted(
        [
            d.name
            for d in zoo_path.iterdir()
            if d.is_dir() and (d / "e_urdf.json").exists()
        ]
    )


def load_embodiment(robot_id: str) -> EmbodimentAsset:
    """Load a robot embodiment asset bundle.

    Args:
        robot_id: The robot identifier (e.g., "universal_robots_ur5e", "unitree_g1")

    Returns:
        EmbodimentAsset object with full configuration

    Raises:
        FileNotFoundError: If robot_id doesn't exist in the zoo
        ValueError: If e_urdf.json is missing or invalid

    Example:
        >>> ur5e = load_embodiment("universal_robots_ur5e")
        >>> print(ur5e.name)
        'UR5e Collaborative Robotic Arm'
        >>> print(ur5e.dof)
        6
        >>> print(ur5e.system_prompt[:100])
        '# System Prompt: UR5e Collaborative Arm...'
    """
    zoo_path = get_zoo_path()
    robot_path = zoo_path / robot_id

    if not robot_path.exists():
        available = list_robots()
        available_str = "\n  - ".join([""] + available) if available else "\n  (none found)"
        raise FileNotFoundError(
            f"Robot '{robot_id}' not found in e-URDF-Zoo.\n"
            f"Available robots:{available_str}\n"
            f"Zoo path: {zoo_path}"
        )

    config_path = robot_path / "e_urdf.json"
    if not config_path.exists():
        raise ValueError(f"Invalid asset bundle: missing e_urdf.json in {robot_path}")

    return EmbodimentAsset(robot_id, robot_path)


def get_robot_info(robot_id: str) -> dict[str, Any]:
    """Get quick information about a robot without loading full asset.

    Args:
        robot_id: The robot identifier

    Returns:
        Dictionary with basic robot info
    """
    asset = load_embodiment(robot_id)
    return {
        "id": robot_id,
        "name": asset.name,
        "type": asset.robot_type,
        "dof": asset.dof,
        "path": str(asset.base_path),
    }
