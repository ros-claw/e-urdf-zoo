# dex-urdf Bulk Import Report

## Summary

| Metric | Count |
|---|---|
| Total imported assets | 16 |
| PASS | 0 |
| PASS_WITH_WARNINGS | 16 |
| FAIL | 0 |

All imported assets pass bundle validation with license warnings because upstream model licenses are marked `unknown` pending review.

## Imported assets

| Asset ID | Category | Variant | Status |
|---|---|---|---|
| dexhands/ability_hand/left | dexhands | left | experimental |
| dexhands/ability_hand/right | dexhands | right | experimental |
| dexhands/allegro_hand/left | dexhands | left | experimental |
| dexhands/allegro_hand/right | dexhands | right | experimental |
| dexhands/barrett_hand/unspecified | dexhands | unspecified | experimental |
| dexhands/dclaw/default | dexhands | default | experimental |
| dexhands/inspire_hand/left | dexhands | left | experimental |
| dexhands/inspire_hand/right | dexhands | right | experimental |
| dexhands/leap_hand/left | dexhands | left | experimental |
| dexhands/leap_hand/right | dexhands | right | experimental |
| dexhands/schunk_svh/left | dexhands | left | experimental |
| dexhands/schunk_svh/right | dexhands | right | experimental |
| dexhands/shadow_hand/left | dexhands | left | experimental |
| dexhands/shadow_hand/right | dexhands | right | experimental |
| dexhands/shadow_hand/unspecified | dexhands | unspecified | experimental |
| grippers/panda/default | grippers | default | experimental |

## Safety defaults

Every imported asset is configured with:

- `status: experimental`
- `real_robot_execution_allowed: false`
- `sandbox_required: true`
- Blocked actions: fast full close, forceful grasp without current limit, uncalibrated real execution.
- Forbidden capabilities: forceful grasp without current limit, fast full close.

## Known issues

- `dexhands/shadow_hand/unspecified` (from `bimanual.urdf`) references DAE meshes that are not present in the upstream checkout. The asset was imported with warnings; mesh paths remain unresolved.
- All assets require upstream license review before any commercial use.

## Next steps

1. Review upstream licenses and update `licenses/THIRD_PARTY.yaml` for each family.
2. Complete sandbox-only validation in MuJoCo.
3. Add measured calibration data to `calibration_defaults.yaml`.
4. Promote assets to `validated` only after passing the full validation protocol.
