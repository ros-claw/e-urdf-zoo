# dexsuite/dex-urdf Import

This document records the bulk import of dexterous-hand and gripper models from
[dexsuite/dex-urdf](https://github.com/dexsuite/dex-urdf) into `e-urdf-zoo`.

## Command used

```bash
e-urdf-zoo import dex-urdf \
  --source /home/ubuntu/rosclaw/rosclaw/dex-urdf \
  --output robots \
  --all \
  --copy-assets
```

## Imported families

| Family | Asset ID(s) | Category |
|---|---|---|
| Allegro Hand | `dexhands/allegro_hand/left`, `dexhands/allegro_hand/right` | dexterous hand |
| Shadow Hand | `dexhands/shadow_hand/left`, `dexhands/shadow_hand/right`, `dexhands/shadow_hand/unspecified` | dexterous hand |
| SCHUNK SVH Hand | `dexhands/schunk_svh/left`, `dexhands/schunk_svh/right` | dexterous hand |
| Ability Hand | `dexhands/ability_hand/left`, `dexhands/ability_hand/right` | dexterous hand |
| Leap Hand | `dexhands/leap_hand/left`, `dexhands/leap_hand/right` | dexterous hand |
| DClaw Gripper | `dexhands/dclaw/default` | dexterous hand / gripper |
| Barrett Hand | `dexhands/barrett_hand/unspecified` | dexterous hand |
| Inspire Hand | `dexhands/inspire_hand/left`, `dexhands/inspire_hand/right` | dexterous hand |
| Panda Gripper | `grippers/panda/default` | gripper |

## Transformations applied

- URDF copied to `model/model.urdf`.
- Mesh paths rewritten to `../meshes/raw/<subdir>/<file>` relative to `model/model.urdf`.
- Meshes copied into `meshes/raw/` preserving `visual/` and `collision/` subdirectories.
- `manifest.yaml`, `semantic.yaml`, `capabilities.yaml`, `safety.yaml`, `providers.yaml`, `sandbox.yaml`, `calibration_defaults.yaml` generated.
- `prompts/system.md`, `prompts/tools_usage.md`, `prompts/safety.md`, `prompts/skill_notes.md` generated.
- `licenses/NOTICE` and `licenses/THIRD_PARTY.yaml` created with upstream source metadata.
- `checksums.json` generated.

## Safety stance

All imported assets are **experimental**:

- Real robot execution is disabled.
- Sandbox validation is required.
- Forceful grasp and fast full close are forbidden.
- Calibration is required before any real-hardware motion.

## Validation

Run validation for any imported asset:

```bash
e-urdf-zoo validate dexhands/inspire_hand/right
```

Current aggregate result: **PASS_WITH_WARNINGS** for all 16 assets due to unknown upstream model licenses.

## Reports

- `reports/dex_urdf_import_summary.json`
- `reports/dex_urdf_import_report.md`
