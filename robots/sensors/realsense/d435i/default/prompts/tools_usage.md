# Tools Usage: Intel RealSense D435I

Use ROS topic/service tools to interact with this camera:

- **Color image**: `/camera/color/image_raw`
- **Depth image**: `/camera/depth/image_rect_raw`
- **Camera info**: `/camera/color/camera_info`, `/camera/depth/camera_info`
- **IMU** (if available): `/camera/imu`

Always verify `camera_info`, TF, and timestamps before using observations for safety-critical decisions.
