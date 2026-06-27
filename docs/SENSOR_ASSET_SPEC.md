# Sensor Asset Specification

This document defines the bundle file conventions for **sensor** assets in
`e-urdf-zoo`. It is used by the RealSense importer and any future sensor
importers (e.g., LiDAR, tactile skin, force/torque sensors).

## Scope

A sensor asset describes a device that produces observations but does not
actuate the robot. Examples:

- RGB-D cameras
- LiDARs
- IMUs
- Tactile sensors
- Force/torque sensors

Sensor assets are **attachable** to a robot body via a mount frame.

## Asset identity

- `asset_type`: `"sensor"`
- `category`: e.g. `"rgbd_camera"`, `"lidar"`, `"imu"`
- `id`: `sensors/<vendor>/<model>/<variant>`
- `status`: starts as `"experimental"` for all third-party imports

## Required bundle files

### `manifest.yaml`

Top-level manifest following `e_urdf.asset.v1`:

- `asset`: identity, vendor, model, status
- `source`: upstream repo, commit, importer
- `license`: Apache-2.0 or upstream declared license
- `model`: paths to xacro, URDF, MuJoCo URDF, MJCF (if any)
- `sensor`: modalities, `has_imu`, `requires_calibration`
- `runtime_policy`: attachable, requires mount frame, sandbox supported
- `quality`: validation status for each check

### `semantic.yaml`

Follows `e_urdf.semantic.v1`:

- `identity`: asset_id, morphology (`"sensor"`), robot_class, vendor, model
- `frames`: `root`, `body`, `depth_frame`, `depth_optical_frame`,
  `color_frame`, `color_optical_frame`, `infra_frames`, `imu_frames`
- `mounting`: attachable flag, compatible mounts, required calibration
- `modalities`: list of observation modalities
- `roles`: semantic roles such as `visual_perception`, `obstacle_detection`

### `capabilities.yaml`

Follows `e_urdf.capabilities.v1`:

- `capabilities`: allowed capabilities with `risk`, `required_outputs`,
  `calibration_required`, `sandbox_required`
- `forbidden_capabilities`: explicitly blocked capabilities with reason and
  severity

Sensor capabilities commonly include:

- `rgb_observation` (low risk)
- `depth_observation` (medium risk, calibration required)
- `rgbd_scene_understanding`
- `visual_navigation` (high risk, sandbox required)
- `depth_collision_avoidance` (critical risk, calibration + sandbox required)
- `hand_eye_visual_servo`

Forbidden defaults for RGB-D cameras:

- `depth_collision_avoidance_without_calibration`
- `visual_servo_without_hand_eye_calibration`

### `safety.yaml`

Follows `e_urdf.safety.v1`:

- `safety_status`: `"experimental"`
- `global_policy`: perception-only allowed, depth safety requires calibration,
  visual navigation requires sandbox, visual servo requires hand-eye calibration
- `calibration_policy`: lists required calibrations for depth safety and
  visual servo
- `runtime_monitors`: required/recommended topic and health checks
- `blocked_actions`: IDs and reasons
- `first_real_robot_protocol`: ordered checklist before first real-robot use

### `providers.yaml`

Follows `e_urdf.providers.v1`:

- `provider_interfaces.state.required/optional`: observations such as
  `color_image`, `depth_image`, `camera_info`, `infra1_image`, `infra2_image`,
  `imu`
- `provider_interfaces.command.optional`: camera controls such as
  `set_exposure`, `set_resolution`, `set_depth_profile`
- `mcp.recommended_servers`: optional MCP server suggestions

### `sandbox.yaml`

Follows `e_urdf.sandbox.v1`:

- Supported engines: `ros2`, `rviz`, `mujoco`, `isaac`
- Per-engine `model_path` and status
- Validation checklist
- Default mount hints

### `calibration_defaults.yaml`

Follows `e_urdf.calibration_defaults.v1`:

- `calibration.status`: `"default"`, confidence `0.0`
- `intrinsics.color/depth`: `"missing"`, `source: provider_required`
- `extrinsics.camera_to_mount`: `"nominal"`, `source: expanded_urdf`
- `extrinsics.camera_to_body`: `"missing"`, `source: body_attach_required`
- `depth.depth_scale`: `"provider_required"`
- `time_sync.status`: `"unknown"`

## Model files

- `model/model.xacro`: wrapper xacro that produces a standalone robot
- `model/model.urdf`: canonical expanded URDF with relative mesh paths
- `model/model_mujoco.urdf`: MuJoCo-friendly URDF with compiler hints and
  converted/decimated meshes

## Path conventions

- Expanded URDFs must **not** contain `package://realsense2_description`.
- Mesh paths are relative to `model/model.urdf`:
  - `../meshes/raw/<file>` for canonical URDF
  - `../meshes/mujoco/<file>` for MuJoCo URDF

## Safety invariant

A sensor asset may never authorize real-robot motion on its own.
Any capability that uses sensor data for safety-critical decisions must require
validated calibration and, where appropriate, sandbox validation first.
