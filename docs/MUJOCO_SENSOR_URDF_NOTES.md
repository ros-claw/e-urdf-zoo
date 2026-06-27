# MuJoCo Sensor URDF Notes

RealSense and other sensor URDFs are imported into `e-urdf-zoo` primarily for
geometry, frame definitions, and collision placeholders. This document
explains how the MuJoCo-friendly URDF is generated and what remains for
engine-specific configuration.

## What `model_mujoco.urdf` provides

- Fixed base / mount link
- Visual geometry from upstream STL/DAE meshes (converted as needed)
- Collision bodies
- Camera optical and IMU frames
- A MuJoCo compiler hint:

```xml
<mujoco>
  <compiler discardvisual="false" fusestatic="false"/>
</mujoco>
```

## Mesh compatibility fixes

MuJoCo has the following constraints:

- Does not load `.dae` (COLLADA) meshes.
- Binary STL face count should stay below ~200k faces for stable loading.

The importer therefore performs:

1. **DAE to STL conversion**: any `.dae` reference is converted to a binary
   STL in `meshes/mujoco/`.
2. **Decimation**: any mesh with more than 50k faces is reduced using
   quadric decimation (`trimesh` + `fast-simplification`) before STL export.

## What is not simulated

The URDF does **not** configure:

- RGB/depth camera sensors (pixel output, intrinsics, exposure)
- IMU noise models
- USB/power constraints
- Thermal throttling
- Real-time synchronization

These are provided at runtime by ROS 2 camera driver nodes and mapped through
`providers.yaml`.

## Loading in MuJoCo

```python
import mujoco
model = mujoco.MjModel.from_xml_path(
    "robots/sensors/realsense/d455/default/model/model_mujoco.urdf"
)
```

All nine imported RealSense models pass this smoke test.

## Known limitations

- Sensor URDFs contain many fixed links. MuJoCo can load them, but simulation
  performance is best when visual-only geometry is kept minimal.
- R410 and R430 upstream xacro files do not reference a mesh, so their
  MuJoCo URDFs contain only frames and no visual geometry.
- RGB-D rendering requires either an off-screen ROS bridge or a MuJoCo
  renderable camera added by the application; it is not automatic.

## Future work

- Generate `model/model.xml` (MJCF) with explicit MuJoCo camera and IMU
  sensor elements.
- Add per-model resolution hints to `sandbox.yaml`.
