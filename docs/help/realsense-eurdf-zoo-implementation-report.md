# RealSense e-URDF-Zoo Implementation Report

## Overview

This report documents the import of Intel RealSense D400-series sensor assets
from `realsenseai/realsense-ros` into `e-urdf-zoo`.

## Imported models

| Model | Asset ID | IMU | Links | Joints | Meshes |
| --- | --- | --- | --- | --- | --- |
| D405 | `sensors/realsense/d405/default` | no | 11 | 10 | 1 |
| D415 | `sensors/realsense/d415/default` | no | 11 | 10 | 1 |
| D435 | `sensors/realsense/d435/default` | no | 11 | 10 | 1 |
| D435i | `sensors/realsense/d435i/default` | yes | 15 | 14 | 1 |
| D436 | `sensors/realsense/d436/default` | no | 15 | 14 | 1 |
| D455 | `sensors/realsense/d455/default` | yes | 16 | 15 | 1 |
| D585 | `sensors/realsense/d585/default` | no | 20 | 19 | 1 |
| R410 | `sensors/realsense/r410/default` | no | 8 | 7 | 0 |
| R430 | `sensors/realsense/r430/default` | no | 8 | 7 | 0 |

## Xacro expansion results

All nine models expanded successfully from the generated wrapper xacro:

- Wrapper defines a root mount link (`realsense_<model>_mount`).
- Wrapper includes patched upstream `_materials.urdf.xacro`,
  `_usb_plug.urdf.xacro`, and the model-specific macro file.
- D435i additionally includes `_d435i_imu_modules.urdf.xacro`.
- Expansion produced a clean `<robot>` root with no xacro tags and no
  `$(find realsense2_description)` or `package://realsense2_description` residue.

## Mesh processing results

- Upstream mesh references were copied to `meshes/raw/`.
- DAE meshes were converted to binary STL.
- Meshes exceeding 50k faces were decimated.
- All referenced meshes resolve correctly in the expanded URDF.
- R410 and R430 do not reference a mesh in their upstream macro.

## URDF parse results

`xml.etree.ElementTree` and `yourdfpy` successfully parse every
`model/model.urdf`. Link/joint counts are listed above.

## MuJoCo-friendly URDF status

`model/model_mujoco.urdf` loads in MuJoCo for all nine models:

```python
import mujoco
model = mujoco.MjModel.from_xml_path(
    "robots/sensors/realsense/d455/default/model/model_mujoco.urdf"
)
```

MuJoCo-specific mesh processing:

- DAE -> binary STL conversion where needed.
- Decimation of high-resolution meshes.
- Insertion of MuJoCo compiler hints (`discardvisual="false"`,
  `fusestatic="false"`).

## ROSClaw attach-sensor status

ROSClaw-side integration (`rosclaw eurdf pull`,
`rosclaw body attach-sensor`) is **not yet implemented** and is tracked as
follow-up work. The assets are produced in the bundle format expected by the
planned integration:

- `manifest.yaml` declares `asset_type: sensor` and
  `attachable_to_body: true`.
- `semantic.yaml` defines root/body/optical frames and required calibration.
- `capabilities.yaml` blocks uncalibrated depth safety and visual servo.
- `providers.yaml` lists color/depth/camera_info topic candidates.

## Safety defaults

All RealSense assets default to fail-closed:

- `status: experimental`
- `real_robot_execution_allowed: false`
- `sandbox_required: true` for visual navigation / depth safety
- Blocked until calibration:
  - `depth_collision_avoidance_without_calibration`
  - `visual_servo_without_hand_eye_calibration`

## Known limitations

- Isaac Sim USD assets are not provided.
- MuJoCo URDF provides geometry and frames only; RGB-D/IMU simulation requires
  engine-specific configuration.
- R410/R430 bundles have no visual meshes.
- ROSClaw pull/attach-sensor integration remains future work.

## Next steps

1. Implement `rosclaw eurdf search/pull/info` for sensor assets.
2. Implement `rosclaw body attach-sensor <asset_id> --mount <frame>`.
3. Add safety query tests that verify depth collision avoidance is blocked
   until calibration.
4. Consider generating MJCF with explicit camera/IMU sensor elements.

## Reproduction

To regenerate the assets:

```bash
cd /home/ubuntu/rosclaw/rosclaw/e-urdf-zoo
.venv/bin/e-urdf-zoo import realsense-ros \
  --source /home/ubuntu/rosclaw/rosclaw/realsense-ros \
  --output robots/sensors/realsense \
  --copy-meshes --expand-xacro --generate-mujoco-urdf --validate
.venv/bin/e-urdf-zoo index build --output .
```
