# Xacro Import Policy

`e-urdf-zoo` imports upstream `.xacro` files from ROS description packages.
This policy clarifies how xacro is treated, stored, and consumed.

## Xacro is a source format

- Upstream `.xacro` files are **preserved** under `source/xacro/`.
- They are **not** the runtime asset.
- They may depend on ROS package paths such as `$(find pkg)/urdf/...`;
  the importer patches these to relative paths inside the bundle.

## Canonical runtime format is expanded URDF

- The importer generates a `model/model.xacro` **wrapper** that instantiates
  upstream macros on a root mount link.
- The wrapper is expanded to `model/model.urdf` using the Python `xacro`
  package.
- `model.urdf` is the canonical artifact consumed by loaders, validators,
  and ROS runtime.

## MuJoCo does not consume xacro

- MuJoCo loads URDF or MJCF, not xacro.
- The importer generates `model/model_mujoco.urdf` for MuJoCo.
- If an MJCF is later generated, it is derived from the expanded URDF,
  not from xacro directly.

## Regenerability

Every generated URDF must be reproducible from the committed source xacro
and wrapper by running:

```bash
cd robots/sensors/realsense/d455/default
xacro model/model.xacro > model/model.urdf
```

(assuming the `xacro` package is installed and mesh paths are relative).

## Package path rewrite

Inside the bundle, the following substitutions are applied to copied xacro
files and expanded URDFs:

- `$(find realsense2_description)/urdf/` -> relative include path
- `package://realsense2_description/meshes/` -> `../meshes/raw/`

This makes the bundle self-contained and independent of the ROS package index.

## Test requirement

A valid import must satisfy:

- `model/model.urdf` exists and parses as a `<robot>` element.
- No `$(find ...)` or `package://realsense2_description` residue remains.
- No xacro tags remain in the expanded URDF.
- Mesh paths resolve relative to the bundle.

## Do not

- Delete upstream xacro and keep only URDF.
- Feed xacro directly to MuJoCo or to a non-ROS runtime.
- Reference upstream package paths inside generated URDFs.
- Treat `test_*camera*.urdf.xacro` files as canonical models.
