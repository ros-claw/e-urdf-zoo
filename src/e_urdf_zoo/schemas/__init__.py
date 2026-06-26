"""Shared schema utilities and validation result type."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .capabilities import CapabilitiesSchema, Capability, ForbiddenCapability
from .checksums import ChecksumsSchema
from .manifest import ManifestSchema
from .providers import ProvidersSchema
from .safety import SafetySchema
from .sandbox import SandboxSchema
from .semantic import SemanticSchema

__all__ = [
    "CapabilitiesSchema",
    "Capability",
    "ChecksumsSchema",
    "ForbiddenCapability",
    "ManifestSchema",
    "ProvidersSchema",
    "SafetySchema",
    "SandboxSchema",
    "SemanticSchema",
    "ValidationMessage",
    "ValidationResult",
    "ValidationStatus",
    "validate_manifest",
    "validate_safety",
]


class ValidationStatus(str, Enum):
    """Validation outcome for an asset or file."""

    PASS = "PASS"
    PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
    FAIL = "FAIL"


@dataclass
class ValidationMessage:
    """A single validation message."""

    level: str
    message: str
    path: str = ""


@dataclass
class ValidationResult:
    """Result of validating one or more asset files."""

    status: ValidationStatus
    messages: list[ValidationMessage]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "messages": [
                {"level": m.level, "message": m.message, "path": m.path}
                for m in self.messages
            ],
        }


def _warn(msg: str, path: str = "") -> ValidationMessage:
    return ValidationMessage(level="warning", message=msg, path=path)


def _error(msg: str, path: str = "") -> ValidationMessage:
    return ValidationMessage(level="error", message=msg, path=path)


def _info(msg: str, path: str = "") -> ValidationMessage:
    return ValidationMessage(level="info", message=msg, path=path)


def validate_manifest(path: Path | str) -> ValidationResult:
    """Validate a manifest.yaml file."""
    p = Path(path)
    messages: list[ValidationMessage] = []
    if not p.exists():
        return ValidationResult(
            status=ValidationStatus.FAIL,
            messages=[_error("manifest.yaml not found", str(p))],
        )
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001
        return ValidationResult(
            status=ValidationStatus.FAIL,
            messages=[_error(f"Failed to read manifest: {exc}", str(p))],
        )
    try:
        manifest = ManifestSchema.model_validate(data)
    except ValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(x) for x in err.get("loc", []))
            messages.append(_error(f"{loc}: {err['msg']}", str(p)))
        return ValidationResult(status=ValidationStatus.FAIL, messages=messages)

    if manifest.license.upstream_model_license == "unknown" and manifest.license.display_warning:
        messages.append(
            _warn(
                "upstream_model_license is unknown; commercial review recommended",
                str(p),
            )
        )
    if not manifest.runtime_policy.sandbox_required:
        messages.append(_error("sandbox_required must be true", str(p)))
    if manifest.runtime_policy.real_robot_execution_allowed:
        messages.append(_warn("real_robot_execution_allowed is true", str(p)))

    has_error = any(m.level == "error" for m in messages)
    status = (
        ValidationStatus.FAIL
        if has_error
        else (
            ValidationStatus.PASS_WITH_WARNINGS
            if messages
            else ValidationStatus.PASS
        )
    )
    return ValidationResult(status=status, messages=messages)


def validate_safety(path: Path | str) -> ValidationResult:
    """Validate a safety.yaml file."""
    p = Path(path)
    messages: list[ValidationMessage] = []
    if not p.exists():
        return ValidationResult(
            status=ValidationStatus.FAIL,
            messages=[_error("safety.yaml not found", str(p))],
        )
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001
        return ValidationResult(
            status=ValidationStatus.FAIL,
            messages=[_error(f"Failed to read safety: {exc}", str(p))],
        )
    try:
        safety = SafetySchema.model_validate(data)
    except ValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(x) for x in err.get("loc", []))
            messages.append(_error(f"{loc}: {err['msg']}", str(p)))
        return ValidationResult(status=ValidationStatus.FAIL, messages=messages)

    if safety.global_policy.real_robot_execution_allowed:
        messages.append(_warn("real_robot_execution_allowed is true", str(p)))
    if not safety.global_policy.sandbox_required:
        messages.append(_error("sandbox_required must be true", str(p)))

    has_error = any(m.level == "error" for m in messages)
    status = (
        ValidationStatus.FAIL
        if has_error
        else (
            ValidationStatus.PASS_WITH_WARNINGS
            if messages
            else ValidationStatus.PASS
        )
    )
    return ValidationResult(status=status, messages=messages)
