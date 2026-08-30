# Sentinel repository instructions

## Current objective

Continue the existing Sentinel / Isaac Sim project. Do not redesign completed phases.

Current order:

1. Restore and inspect the migrated project.
2. Validate Isaac Sim GUI and Stage5D on the RTX 4090 host.
3. Diagnose RTF and command latency.
4. Implement a minimal safe simulation-estop enable flow only after the baseline.
5. Evaluate Small Point-LIO with the `livox_pointcloud2` adapter.

Do not start terrain, Nav2, behavior-tree, or tactical-RL work yet.

## Protected state

- Never overwrite `Sentry_stage5c_joint_drives.usda`.
- Required SHA256: `ffa8ecbf83a047f05cc1e4aeb3005b1fa8c09da651c273bb4a4d03a62a0dcacc`.
- Stage5D already passed straight, lateral, diagonal, and rotate tests.
- Do not retune swerve IK, friction, joint gains, or Stage5D physics before latency/RTF diagnosis.
- Do not retry global `set_physics_dt(1/200)`; it previously caused RTX LiDAR device-lost and segmentation faults.

## TF and topic ownership

- Isaac owns `odom -> base_link`.
- `robot_state_publisher` owns `base_link -> robot links`.
- LIO must not publish a duplicate `odom -> base_link`.
- Keep `/sentry/odom` as Isaac ground truth.
- Use `/sentry/lio/odom` for estimated odometry.

## Sensor contract

- LiDAR: `/sentry/lidar/points`, `PointCloud2`, frame `lidar_link`.
- Fields: `x y z intensity time`; time unit is seconds and varies per point.
- IMU: `/sentry/imu`, frame `imu_link`.
- Current simulation is a geometric Mid-360 baseline, not sensor ground truth.

## Environment

- Project baseline: Ubuntu 24.04, ROS 2 Jazzy, Isaac Sim 6.0.1.
- Current cloud host: Ubuntu 22.04, RTX 4090.
- Inspect the Ubuntu 22.04/Jazzy Docker or source-build compatibility path before building.
- Preserve `ROS_DOMAIN_ID=0` and baseline `RMW_IMPLEMENTATION=rmw_fastrtps_cpp` unless an explicit compatibility experiment is documented.
- Preserve the project spelling `issac-sim` where the existing project expects it.

## Git and workspace protection

Do not automatically run:

- `git reset`
- `git restore`
- `git clean`
- `git checkout --`
- `git stash`
- `git commit`
- `git push`

Do not discard dirty-worktree changes. Protect user changes in:

- `tools/ubuntu/bootstrap_jazzy.sh`
- `tools/ubuntu/build.sh`

## First-turn rule

Before modifying code:

1. Read the project docs and integration scripts.
2. Report actual paths, OS/ROS/Isaac compatibility, Git state, Stage5C hash, Stage5D presence, teleop `nonlocal active` status, hardcoded old paths, and available launch commands.
3. Produce a minimal proposed change list.
4. Wait for explicit authorization before code changes.
