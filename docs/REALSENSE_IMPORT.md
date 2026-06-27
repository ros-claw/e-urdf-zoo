# Intel RealSense ROS Import

This document describes the bulk import of RealSense D400-series sensor
descriptions from `realsenseai/realsense-ros` into `e-urdf-zoo`.

## Imported models

| Asset ID | Model | IMU | Notes |
| --- | --- | --- | --- |
| `sensors/realsense/d405/default` | D405 | no | compact short-range camera |
| `sensors/realsense/d415/default` | D415 | no | standard RGB-D module |
| `sensors/realsense/d435/default` | D435 | no | wide FOV depth module |
| `sensors/realsense/d435i/default` | D435i | yes | includes IMU module |
| `sensors/realsense/d436/default` | D436 | no | industrial variant |
| `sensors/realsense/d455/default` | D455 | yes | integrated IMU |
| `sensors/realsense/d585/default` | D585 | no | high-resolution module |
| `sensors/realsense/r410/default` | R410 | no | legacy module, no mesh reference |
| `sensors/realsense/r430/default` | R430 | no | legacy module, no mesh reference |

## Source

- Repository: `realsenseai/realsense-ros`
- Branch: `ros2-master`
- Package: `realsense2_description`
- Commit at import: `775b167c0dbcfe00a012e248c66a7c8379ef9fbb`

## Import command

```bash
pip install -e ".[dev]"

e-urdf-zoo import realsense-ros \
  --source /home/ubuntu/rosclaw/rosclaw/realsense-ros \
  --output robots/sensors/realsense \
  --copy-meshes \
  --expand-xacro \
  --generate-mujoco-urdf \
  --validate
```

To import a single model:

```bash
e-urdf-zoo import realsense-ros \
  --source /home/ubuntu/rosclaw/rosclaw/realsense-ros \
  --output robots/sensors/realsense/d455/default \
  --model d455 \
  --copy-meshes --expand-xacro --generate-mujoco-urdf --validate
```

## Generated bundle

Each asset contains:

```text
sensors/realsense/<model>/default/
  manifest.yaml
  semantic.yaml
  capabilities.yaml
  safety.yaml
  providers.yaml
  sandbox.yaml
  calibration_defaults.yaml
  e_urdf.json              # legacy-loader compatibility
  model/
    model.xacro            # e-urdf-zoo wrapper
    model.urdf             # canonical expanded URDF
    model_mujoco.urdf      # MuJoCo-friendly URDF
  source/
    upstream_commit.txt
    upstream_files.yaml
    xacro/                 # patched upstream xacro source
  meshes/
    raw/                   # meshes copied from upstream
    mujoco/                # converted / decimated meshes for MuJoCo
  prompts/
    system.md
    tools_usage.md
    safety.md
  licenses/
    NOTICE
    THIRD_PARTY.yaml
  validation/
    xacro_expand_report.json
    urdf_parse_report.json
    mesh_report.json
    mujoco_report.json
  README.md
```

## Design decisions

1. **Xacro is preserved, not consumed at runtime.**
   Upstream `_dxxx.urdf.xacro` files are macros, not standalone robots.
   The importer generates a `model.xacro` wrapper that instantiates the macro
   on a `realsense_<model>_mount` link, then expands it to `model.urdf`.

2. **Package paths are rewritten.**
   All `package://realsense2_description/meshes/...` URIs are replaced with
   relative `../meshes/raw/...` paths so the bundle is self-contained.

3. **MuJoCo gets its own mesh directory.**
   `model_mujoco.urdf` references `../meshes/mujoco/...`.
   DAE meshes are converted to binary STL and high-face-count meshes are
   decimated so MuJoCo can load them.

4. **Safety defaults are fail-closed.**
   All assets default to `status: experimental`,
   `real_robot_execution_allowed: false`, and
   `sandbox_required: true` for visual navigation / depth safety.
   `depth_collision_avoidance_without_calibration` and
   `visual_servo_without_hand_eye_calibration` are explicitly forbidden.

## Known limitations

- Isaac Sim USD assets are not provided; marked as unsupported in `sandbox.yaml`.
- RGB-D rendering inside MuJoCo requires engine-specific sensor configuration;
  the URDF only provides geometry and fixed frames.
- R410 and R430 upstream xacro files do not reference a mesh file, so their
  bundles contain no geometry meshes.

## Tests

```bash
pytest tests/importers/test_realsense_ros.py -q
```

## Aliases

The rebuilt `index.json` / `index.yaml` expose short aliases such as:

- `realsense-d455` -> `sensors/realsense/d455/default`
- `realsense-d435i` -> `sensors/realsense/d435i/default`
