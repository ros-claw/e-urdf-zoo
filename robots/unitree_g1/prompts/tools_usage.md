# Unitree G1 MCP Tool Usage Guide

## Overview

This guide explains how to use the MCP tools available for controlling the Unitree G1 humanoid robot.

**CRITICAL DIFFERENCE**: Unlike arm robots, G1 requires **balance checking** in addition to collision checking.

## Tool: `verify_action_safety`

**Purpose**: Validate a planned trajectory before execution (collision + joint limits).

### When to Use
- BEFORE every motion command
- For arm movements while standing
- For whole-body motions

### Parameters

```python
{
  "current_joints": [float] * 23,
  # Current joint positions in radians
  # Order: [left_leg_6, right_leg_6, waist_3, left_arm_5, right_arm_5, head_2]

  "target_joints": [float] * 23,
  # Target joint positions in radians (same order)

  "duration_sec": float  # Optional, default: 3.0 for humanoids
  # Simulation duration - longer for balance checks
}
```

### Return Values

**If SAFE**:
```
✅ [SAFE] Physics simulation passed!
   - No collisions detected
   - All joint limits respected
   - No self-collision
   You may proceed with balance checking.
```

**If UNSAFE**:
```
❌ [DANGER] Physical simulation failed!
   🔴 COLLISIONS DETECTED:
     - left_forearm_link collided with torso_link at t=0.5s

   ⚠️ ACTION BLOCKED
```

---

## Tool: `check_balance_stability`

**Purpose**: Humanoid-specific balance validation (ZMP, foot contact, fall risk).

### When to Use
- **ALWAYS** after `verify_action_safety` for G1
- For any standing or walking motion
- Before foot liftoff

### Parameters

```python
{
  "proposed_joints": [float] * 23,
  # Target joint configuration

  "support_phase": str,  # "double_support", "left_single", "right_single"
  # Which feet are in contact with ground

  "expected_com_height_m": float,  # Optional, default: 0.6
  # Expected center of mass height
}
```

### Return Values

**If STABLE**:
```
✅ [BALANCE OK] ZMP stability check passed!
   - ZMP within support polygon: x=0.02m, y=0.01m
   - Both feet in contact: Left=150N, Right=145N
   - Pelvis height: 0.62m (OK > 0.4m threshold)
   - Body tilt: 5° (OK < 15° threshold)
   Safe to execute.
```

**If UNSTABLE**:
```
❌ [BALANCE FAIL] Fall risk detected!
   🟡 ZMP outside support polygon!
      ZMP: x=0.15m (limit: 0.08m)
   🟡 High fall probability: 78%

   ⚠️ ACTION BLOCKED - Balance cannot be maintained
   Suggestion: Widen stance or reduce arm extension
```

### Example Usage

```python
# User wants to wave while standing
result_safety = verify_action_safety(
    current_joints=current,
    target_joints=wave_pose,
    duration_sec=3.0
)

if "[SAFE]" in result_safety:
    result_balance = check_balance_stability(
        proposed_joints=wave_pose,
        support_phase="double_support",
        expected_com_height_m=0.6
    )

    if "[BALANCE OK]" in result_balance:
        # Execute on real robot
        g1.execute(wave_pose)
    else:
        print("Balance concern:", result_balance)
else:
    print("Safety concern:", result_safety)
```

---

## Tool: `check_fall_risk`

**Purpose**: Predict fall probability for a sequence of motions.

### When to Use
- For walking trajectories
- For multi-step actions
- Before dynamic movements

### Parameters

```python
{
  "trajectory_points": [[float] * 23],  # List of joint configurations
  # Sequence of poses over time

  "time_step_sec": float,  # Time between trajectory points
}
```

### Return Value
```json
{
  "fall_probability": 0.15,
  "max_tilt_angle_deg": 12.0,
  "min_pelvis_height_m": 0.58,
  "critical_timestep": null,
  "is_safe": true
}
```

### Example Usage

```python
# Check a 5-step walking sequence
result = check_fall_risk(
    trajectory_points=walking_sequence,
    time_step_sec=0.5
)

if result["fall_probability"] < 0.3:  # 30% threshold
    print("Safe to walk")
else:
    print(f"Fall risk: {result['fall_probability']*100:.0f}%")
    print(f"Critical at timestep: {result['critical_timestep']}")
```

---

## Humanoid Safety Checklist

### For Static Actions (Standing, Reaching, Waving)
- [ ] Called `verify_action_safety` for collision check
- [ ] Called `check_balance_stability` with "double_support"
- [ ] Result shows `[SAFE]` and `[BALANCE OK]`
- [ ] ZMP within support polygon
- [ ] Both feet in contact

### For Dynamic Actions (Walking, Stepping)
- [ ] Generated full trajectory with foot placements
- [ ] Called `verify_action_safety` on keyframes
- [ ] Called `check_fall_risk` on entire trajectory
- [ ] Fall probability < 30%
- [ ] Emergency stop plan ready

### Emergency Protocols
If any check fails:
1. **STOP** - Do not execute
2. **ANALYZE** - Read the specific failure reason
3. **ADJUST** - Modify trajectory or suggest alternative
4. **RE-VALIDATE** - Run checks again
5. **EXECUTE** - Only if all checks pass

---

## Common Patterns

### Pattern 1: Safe Waving
```python
# Standing wave with right arm
wave_pose = current.copy()
wave_pose[right_shoulder_pitch_idx] = -1.57  # Raise arm
wave_pose[right_elbow_idx] = -1.57  # Bend elbow

# Double check
safety = verify_action_safety(current, wave_pose)
balance = check_balance_stability(wave_pose, "double_support")

if "[SAFE]" in safety and "[BALANCE OK]" in balance:
    execute(wave_pose)
```

### Pattern 2: Single Step
```python
# Step forward with left foot
step_sequence = [
    current,              # Start
    weight_shift_right,   # Shift to right foot
    left_foot_liftoff,    # Lift left foot
    left_foot_forward,    # Move forward
    left_foot_contact,    # Contact ground
    weight_center         # Center weight
]

# Check fall risk for whole sequence
fall_check = check_fall_risk(step_sequence, 0.2)
if fall_check["fall_probability"] < 0.3:
    execute_sequence(step_sequence)
```

### Pattern 3: Bimanual Grasp
```python
# Grasp object with both hands
grasp_pose = compute_ik(target_object)

# Check both safety and balance
safety = verify_action_safety(current, grasp_pose)
balance = check_balance_stability(grasp_pose, "double_support")

if safety.is_safe and balance.is_stable:
    move_to(grasp_pose)
    close_grippers()
```

---

## Error Interpretation

### Balance Errors

**ZMP Outside Support Polygon**
- Cause: Center of mass too far from feet
- Fix: Bend knees, widen stance, or reduce arm extension

**Foot Contact Lost**
- Cause: Leg lifted without planning
- Fix: Ensure other foot has contact before liftoff

**Pelvis Height Too Low**
- Cause: Crouching too much or falling
- Fix: Straighten legs or emergency sit

**Excessive Tilt**
- Cause: Reaching too far or unstable pose
- Fix: Reduce reach distance or use both hands

### Safety Errors

**Self-Collision**
- Common: Arm hitting leg or torso
- Fix: Adjust arm trajectory

**Joint Limit**
- Knee/elbow: Remember these are 0 to -2.5 rad only
- Fix: Check sign of joint commands

---

## Key Differences from Arm Robots

| Aspect | UR5e (Arm) | G1 (Humanoid) |
|--------|------------|---------------|
| Base | Fixed | Floating (pelvis) |
| Critical Check | Collision | Balance + Collision |
| Simulation Time | 2s | 3s (longer for balance) |
| Emergency | Stop motion | Emergency pose/sit |
| Workspace | Fixed | Changes with stance |

Remember: You are not just controlling joints - you are maintaining dynamic balance while moving. Every action must respect the physics of bipedal locomotion.
