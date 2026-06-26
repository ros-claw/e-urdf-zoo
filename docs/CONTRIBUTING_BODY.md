# Contributing a New Robot Body

This guide describes how to add a new robot model to `e-urdf-zoo`.

## Quick path: import an existing URDF

```bash
e-urdf-zoo import urdf \
  --urdf ./robot.urdf \
  --asset-id arms/my_vendor/my_arm/default \
  --category arms \
  --vendor MyVendor \
  --model MyArm \
  --variant default \
  --copy-meshes \
  --generate-safety \
  --validate
```

## Manual path

1. Create the directory:

```bash
mkdir -p robots/<category>/<vendor>/<model>/<variant>/{model,meshes/{visual,collision,raw},prompts,licenses}
```

2. Copy the URDF to `model/model.urdf` and meshes to `meshes/raw/`.
3. Rewrite mesh paths in the URDF to be relative to `model/model.urdf`:

```xml
<mesh filename="../meshes/raw/my_mesh.stl"/>
```

4. Write `manifest.yaml`, `semantic.yaml`, `capabilities.yaml`, `safety.yaml`, `providers.yaml`, `sandbox.yaml`, `calibration_defaults.yaml`.
5. Write `prompts/system.md`, `prompts/tools_usage.md`, `prompts/safety.md`.
6. Write `licenses/NOTICE` and `licenses/THIRD_PARTY.yaml`.
7. Run validation:

```bash
e-urdf-zoo validate <category>/<vendor>/<model>/<variant>
e-urdf-zoo index build
```

## Safety requirements

- `real_robot_execution_allowed: false` by default.
- `sandbox_required: true` for all manipulation/gesture capabilities.
- Declare `forbidden_capabilities` for any high-risk action.
- Document first-real-robot protocol in `safety.yaml`.

## Status values

- `experimental` — default for new assets.
- `validated` — only after parser, mesh, safety, and sandbox checks pass.
- `deprecated` — no longer recommended.
- `blocked` — known safety blocker.

## See also

- `docs/ASSET_SPEC.md`
- `docs/THIRD_PARTY_ASSETS.md`
