# e-URDF-Zoo Asset Spec

This document defines the asset bundle format for robot models in `e-urdf-zoo`.

## Asset ID

```text
<category>/<vendor_or_family>/<model>/<variant>
```

Examples:

- `dexhands/inspire_hand/right`
- `humanoids/unitree/g1/default`
- `grippers/panda/default`

## Directory layout

```text
robots/
  <category>/
    <vendor_or_family>/
      <model>/
        <variant>/
          manifest.yaml
          model/
            model.urdf
          meshes/
            visual/
            collision/
            raw/
          semantic.yaml
          capabilities.yaml
          safety.yaml
          providers.yaml
          sandbox.yaml
          calibration_defaults.yaml
          prompts/
            system.md
            tools_usage.md
            safety.md
            skill_notes.md
          licenses/
            NOTICE
            THIRD_PARTY.yaml
            UPSTREAM_LICENSE.txt
          checksums.json
          README.md
```

## Core files

### `manifest.yaml`

Top-level identity and metadata. Required fields:

- `schema_version`
- `asset.id`
- `asset.name`
- `asset.category`

See `src/e_urdf_zoo/schemas/manifest.py` for the full schema.

### `semantic.yaml`

Semantic groupings of links and joints (fingers, palm, arm, etc.), contact surfaces, mounting info.

### `capabilities.yaml`

Declared capabilities and forbidden capabilities. Every high-risk capability must set `sandbox_required: true`. Dexterous hands must forbid forceful grasp and fast full close.

### `safety.yaml`

Mandatory. Defines global policy, limits, runtime monitors, blocked actions, and first-real-robot protocol. `safety.yaml` missing is a validation failure.

### `providers.yaml`

Provider interface definitions for runtime diagnosis.

### `sandbox.yaml`

Per-engine simulation support and required validation checks.

### `checksums.json`

SHA-256 checksums of all bundle files.

## Validation rules

| Check | Severity |
|---|---|
| Missing `manifest.yaml` | FAIL |
| Missing `safety.yaml` | FAIL |
| Missing `capabilities.yaml` | FAIL |
| Missing `semantic.yaml` | FAIL |
| Missing license metadata | WARN |
| Missing source metadata | WARN |
| `sandbox_required: false` | FAIL |
| `real_robot_execution_allowed: true` | WARN |
| Missing `forbidden_capabilities` | FAIL |

## Legacy compatibility

Assets that still use the old `e_urdf.json` + `model.xml` layout remain loadable via backward-compatible fallback.
