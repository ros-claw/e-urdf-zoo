# Intel RealSense D455

Asset ID: `sensors/realsense/d455/default`

Imported from [https://github.com/realsenseai/realsense-ros](https://github.com/realsenseai/realsense-ros) commit `775b167c0dbcfe00a012e248c66a7c8379ef9fbb`.

## Files

- `model/model.xacro` – e-URDF-Zoo wrapper xacro
- `model/model.urdf` – canonical expanded URDF
- `model/model_mujoco.urdf` – MuJoCo-friendly URDF
- `source/xacro/` – patched upstream xacro source
- `meshes/raw/` – raw meshes referenced by the URDF
- `meshes/mujoco/` – converted/decimated meshes for MuJoCo
- `manifest.yaml`, `semantic.yaml`, `capabilities.yaml`, `safety.yaml`, `providers.yaml`, `sandbox.yaml`, `calibration_defaults.yaml`
- `prompts/` – system, tools usage, and safety prompts
- `validation/` – expansion, parse, mesh, and MuJoCo reports

## Safety

This sensor defaults to **experimental** status. Depth-based safety and visual servoing are blocked until calibration is validated. See `safety.yaml` and `capabilities.yaml` for details.
