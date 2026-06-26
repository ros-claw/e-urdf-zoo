# Tools Usage: dexhands/allegro_hand/right

Use ROS topic/service tools to interact with this hand:

- **Read state**: `/joint_states`
- **Command joints**: publish to `/hand/joint_cmd` (or equivalent) after confirming mode.
- **Diagnostics**: `/diagnostics`

Always set `sandbox_only=True` unless the asset explicitly allows real execution.
