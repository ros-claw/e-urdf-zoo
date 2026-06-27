# Safety: Intel RealSense D415

This asset defaults to **experimental** status with the following blocks:

- `real_robot_execution_allowed: false` (no motion authorized from the camera itself)
- `sandbox_required: true` for visual navigation and depth-based safety
- Blocked: `depth_collision_avoidance_without_calibration`, `visual_servo_without_hand_eye_calibration`

Promote to `validated` only after completing camera intrinsics/extrinsics calibration and runtime health checks.
