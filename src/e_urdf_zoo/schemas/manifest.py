"""Schema for manifest.yaml."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AssetInfo(BaseModel):
    """Identity of an asset."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    version: str = "0.1.0"
    status: str = "experimental"
    category: str
    vendor: str = "unknown"
    model: str = "unknown"
    variant: str = "default"
    description: str = ""


class SourceInfo(BaseModel):
    """Where this asset came from."""

    model_config = ConfigDict(extra="allow")

    type: str = "third_party_import"
    upstream_repo: str = "unknown"
    upstream_url: str = ""
    upstream_commit: str = "unknown"
    upstream_path: str = ""
    imported_at: str = ""
    importer: str = ""


class LicenseInfo(BaseModel):
    """License metadata for an asset."""

    model_config = ConfigDict(extra="allow")

    repo_declared_license: str = "Apache-2.0"
    upstream_model_license: str = ""
    source_url: str = ""
    source_commit: str = "unknown"
    notice_file: str = "licenses/NOTICE"
    third_party_file: str = "licenses/THIRD_PARTY.yaml"
    import_blocking: bool = False
    display_warning: bool = True
    commercial_review_recommended: bool = True
    notes: list[str] = Field(default_factory=list)


class ModelInfo(BaseModel):
    """Model file locations."""

    model_config = ConfigDict(extra="allow")

    primary_format: str = "urdf"
    urdf: str | None = "model/model.urdf"
    mjcf: str | None = None
    xml: str | None = None
    meshes_dir: str = "meshes/"
    visual_meshes_dir: str = "meshes/visual/"
    collision_meshes_dir: str = "meshes/collision/"


class RobotInfo(BaseModel):
    """Robot-level metadata."""

    model_config = ConfigDict(extra="allow")

    morphology: str = "unknown"
    robot_class: str = "unknown"
    side: str | None = None
    root_frame: str | None = None
    mounting_frame: str | None = None
    tcp_frame: str | None = None
    dof: int | None = None


class SemanticsRef(BaseModel):
    """Pointers to semantic files."""

    model_config = ConfigDict(extra="allow")

    semantic_file: str = "semantic.yaml"
    capabilities_file: str = "capabilities.yaml"
    safety_file: str = "safety.yaml"
    providers_file: str = "providers.yaml"
    sandbox_file: str = "sandbox.yaml"
    calibration_defaults_file: str = "calibration_defaults.yaml"
    prompts_dir: str = "prompts/"


class QualityInfo(BaseModel):
    """Validation quality tracking."""

    model_config = ConfigDict(extra="allow")

    validation_status: str = "experimental"
    parser_validation: dict[str, str] = Field(default_factory=dict)
    simulation_validation: dict[str, str] = Field(default_factory=dict)
    mesh_validation: dict[str, str] = Field(default_factory=dict)
    safety_review: str = "pending"


class RuntimePolicy(BaseModel):
    """Runtime execution policy."""

    model_config = ConfigDict(extra="allow")

    real_robot_execution_allowed: bool = False
    sandbox_required: bool = True
    provider_required: bool = True
    calibration_required: bool = True
    low_speed_first_run_required: bool = True
    fault_monitor_required: bool = True


class ChecksumsRef(BaseModel):
    """Reference to checksums file."""

    model_config = ConfigDict(extra="allow")

    file: str = "checksums.json"


class ManifestSchema(BaseModel):
    """Top-level manifest.yaml schema."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "e_urdf.asset.v1"
    asset: AssetInfo
    source: SourceInfo = Field(default_factory=SourceInfo)
    license: LicenseInfo = Field(default_factory=LicenseInfo)
    model: ModelInfo = Field(default_factory=ModelInfo)
    robot: RobotInfo = Field(default_factory=RobotInfo)
    semantics: SemanticsRef = Field(default_factory=SemanticsRef)
    quality: QualityInfo = Field(default_factory=QualityInfo)
    runtime_policy: RuntimePolicy = Field(default_factory=RuntimePolicy)
    checksums: ChecksumsRef = Field(default_factory=ChecksumsRef)
    tags: list[str] = Field(default_factory=list)
    aliases: dict[str, str] = Field(default_factory=dict)
