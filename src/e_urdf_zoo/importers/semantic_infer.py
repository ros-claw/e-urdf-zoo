"""Heuristic semantic inference from URDF link/joint names."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path


FINGER_KEYWORDS = {
    "thumb": {"type": "finger", "side": None, "role": ["opposable"]},
    "index": {"type": "finger", "side": None, "role": ["index_finger"]},
    "middle": {"type": "finger", "side": None, "role": ["middle_finger"]},
    "ring": {"type": "finger", "side": None, "role": ["ring_finger"]},
    "pinky": {"type": "finger", "side": None, "role": ["pinky_finger"]},
    "little": {"type": "finger", "side": None, "role": ["pinky_finger"]},
}

PALM_KEYWORDS = ["palm", "base", "hand_base", "hand_root", "wrist"]

SIDE_HINTS = {
    "_l": "left",
    "_r": "right",
    "_left": "left",
    "_right": "right",
    "left_": "left",
    "right_": "right",
}


def _infer_side(name: str) -> str | None:
    lower = name.lower()
    for hint, side in SIDE_HINTS.items():
        if hint in lower:
            return side
    return None


def infer_hand_semantics(urdf_path: Path, tree: ET.ElementTree) -> dict:
    """Infer semantic groups for a dexterous hand URDF."""
    links = [elem.get("name", "") for elem in tree.iter("link")]
    joints = [elem.get("name", "") for elem in tree.iter("joint")]

    groups: dict[str, dict] = {}
    used_links: set[str] = set()

    # Palm group
    palm_links = [
        link
        for link in links
        if any(kw in link.lower() for kw in PALM_KEYWORDS)
    ]
    if palm_links:
        groups["palm"] = {
            "type": "palm",
            "links": palm_links,
            "joints": [],
            "side": _infer_side(urdf_path.name),
            "source": "heuristic",
            "confidence": 0.7,
        }
        used_links.update(palm_links)

    # Finger groups
    for keyword, info in FINGER_KEYWORDS.items():
        finger_links = [link for link in links if keyword in link.lower()]
        if not finger_links:
            continue
        finger_joints = [
            joint for joint in joints if keyword in joint.lower()
        ]
        groups[keyword] = {
            "type": info["type"],
            "links": finger_links,
            "joints": finger_joints,
            "side": _infer_side(urdf_path.name),
            "roles": info["role"],
            "source": "heuristic",
            "confidence": 0.6,
        }
        used_links.update(finger_links)

    # Catch-all group for any remaining links
    other_links = [link for link in links if link not in used_links]
    if other_links:
        groups["other"] = {
            "type": "other",
            "links": other_links,
            "joints": [],
            "source": "heuristic",
            "confidence": 0.5,
        }

    return {
        "schema_version": "e_urdf.semantic.v1",
        "identity": {
            "source_urdf": urdf_path.name,
            "inferred": "true",
        },
        "frames": {
            "root": links[0] if links else None,
        },
        "groups": groups,
        "notes": ["Semantic groups were inferred from URDF link names."],
    }


def infer_gripper_semantics(urdf_path: Path, tree: ET.ElementTree) -> dict:
    """Infer semantic groups for a simple gripper URDF."""
    links = [elem.get("name", "") for elem in tree.iter("link")]
    joints = [elem.get("name", "") for elem in tree.iter("joint")]

    groups: dict[str, dict] = {
        "base": {
            "type": "base",
            "links": [link for link in links if "base" in link.lower()],
            "joints": [],
            "source": "heuristic",
            "confidence": 0.7,
        },
        "finger_left": {
            "type": "finger",
            "links": [link for link in links if "left" in link.lower() or "finger_l" in link.lower()],
            "joints": [joint for joint in joints if "left" in joint.lower()],
            "source": "heuristic",
            "confidence": 0.6,
        },
        "finger_right": {
            "type": "finger",
            "links": [link for link in links if "right" in link.lower() or "finger_r" in link.lower()],
            "joints": [joint for joint in joints if "right" in joint.lower()],
            "source": "heuristic",
            "confidence": 0.6,
        },
    }
    return {
        "schema_version": "e_urdf.semantic.v1",
        "identity": {"source_urdf": urdf_path.name, "inferred": "true"},
        "frames": {"root": links[0] if links else None},
        "groups": groups,
        "notes": ["Semantic groups were inferred from URDF link names."],
    }


def infer_semantics(urdf_path: Path, tree: ET.ElementTree, category: str) -> dict:
    """Infer semantics based on asset category."""
    if category in {"dexterous_hand", "hand", "dexhands"}:
        return infer_hand_semantics(urdf_path, tree)
    return infer_gripper_semantics(urdf_path, tree)
