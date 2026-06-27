# RealSense ROS Import Report

**Generated:** 2026-06-28
**Importer:** `e_urdf_zoo.importers.realsense_ros`
**Upstream:** `realsenseai/realsense-ros` @ `775b167c0dbcfe00a012e248c66a7c8379ef9fbb`
**Branch:** `ros2-master`
**Package:** `realsense2_description`

## Summary

| Metric | Value |
| --- | --- |
| Models discovered | 9 |
| Models imported | 9 |
| Xacro expansion success | 100% (9/9) |
| URDF parse success | 100% (9/9) |
| Mesh resolution success | 100% (7/7 models with meshes) |
| MuJoCo smoke pass | 100% (9/9) |
| Validation pass | 100% (9/9) |

## Per-model results

| Asset ID | Links | Joints | Meshes | MuJoCo load | Validation |
| --- | --- | --- | --- | --- | --- |
| `sensors/realsense/d405/default` | 11 | 10 | 1 | pass | pass |
| `sensors/realsense/d415/default` | 11 | 10 | 1 | pass | pass |
| `sensors/realsense/d435/default` | 11 | 10 | 1 | pass | pass |
| `sensors/realsense/d435i/default` | 15 | 14 | 1 | pass | pass |
| `sensors/realsense/d436/default` | 15 | 14 | 1 | pass | pass |
| `sensors/realsense/d455/default` | 16 | 15 | 1 | pass | pass |
| `sensors/realsense/d585/default` | 20 | 19 | 1 | pass | pass |
| `sensors/realsense/r410/default` | 8 | 7 | 0 | pass | pass |
| `sensors/realsense/r430/default` | 8 | 7 | 0 | pass | pass |

## Mesh processing

- DAE meshes were converted to binary STL where present.
- High-face-count meshes were decimated to keep MuJoCo loading stable.
- R410 and R430 upstream xacro files do not declare a mesh filename, so no
  meshes were copied for those models.

## Safety defaults

All assets were generated with:

- `status: experimental`
- `real_robot_execution_allowed: false`
- `sandbox_required: true` for visual navigation and depth-based safety
- Forbidden capabilities:
  - `depth_collision_avoidance_without_calibration`
  - `visual_servo_without_hand_eye_calibration`

## Validation command output

```bash
e-urdf-zoo validate sensors/realsense/d405/default
e-urdf-zoo validate sensors/realsense/d415/default
e-urdf-zoo validate sensors/realsense/d435/default
e-urdf-zoo validate sensors/realsense/d435i/default
e-urdf-zoo validate sensors/realsense/d436/default
e-urdf-zoo validate sensors/realsense/d455/default
e-urdf-zoo validate sensors/realsense/d585/default
e-urdf-zoo validate sensors/realsense/r410/default
e-urdf-zoo validate sensors/realsense/r430/default
```

All returned exit code `0`.

## Known limitations

- Isaac Sim USD is not provided; marked unsupported in `sandbox.yaml`.
- RGB-D sensor rendering in MuJoCo requires additional engine-specific setup.
- R410/R430 bundles contain no visual meshes because upstream xacro does not
  reference one.

## Next steps

- ROSClaw `rosclaw eurdf pull` integration for sensor assets.
- `rosclaw body attach-sensor` implementation and safety query tests.
- Optional MJCF generation with explicit MuJoCo camera/IMU sensor elements.
