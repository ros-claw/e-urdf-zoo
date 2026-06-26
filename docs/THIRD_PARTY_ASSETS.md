# Third-Party Assets

`e-urdf-zoo` contains original ROSClaw code and metadata as well as converted third-party robot model assets.

## License policy

- The top-level `LICENSE` applies to ROSClaw original code and metadata.
- Third-party URDFs, meshes, CAD-derived models, and conversion results retain their upstream source information.
- Each asset directory records its source and license metadata in:
  - `manifest.yaml` → `source` and `license` sections
  - `licenses/NOTICE`
  - `licenses/THIRD_PARTY.yaml`

## Import strategy

During active development:

- License metadata is preserved and displayed as warnings when unknown.
- Missing license information does **not** block import.
- Missing source information does **not** block import.
- Missing safety metadata **does** block import.

Before any commercial release, all third-party assets should be reviewed against their upstream licenses.

## Detected upstream sources

| Asset family | Upstream repo |
|---|---|
| Allegro Hand | https://github.com/dexsuite/dex-urdf |
| Shadow Hand | https://github.com/dexsuite/dex-urdf |
| SCHUNK SVH Hand | https://github.com/dexsuite/dex-urdf |
| Ability Hand | https://github.com/dexsuite/dex-urdf |
| Leap Hand | https://github.com/dexsuite/dex-urdf |
| DClaw Gripper | https://github.com/dexsuite/dex-urdf |
| Barrett Hand | https://github.com/dexsuite/dex-urdf |
| Inspire Hand | https://github.com/dexsuite/dex-urdf |
| Panda Gripper | https://github.com/dexsuite/dex-urdf |

## Asset status

All imported third-party assets default to:

- `status: experimental`
- `real_robot_execution_allowed: false`
- `sandbox_required: true`

They may only be promoted to `validated` after completing the full validation protocol.
