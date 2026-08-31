# Imported historical snapshot — not current project truth

> This file is preserved from the 2026-08-15 workspace snapshot. Its Stage5D and Phase
> PASS claims are historical evidence only. Use the repository root `PROJECT_STATE.md`
> and current Gate reports before running simulation, training or hardware.

# Sentinel Project State (historical)

Last updated: 2026-08-15 — PHASE I LiDAR + IMU simulation baseline

## Current State

| Item | State |
|---|---|
| Stage5B Static Physics | PASS |
| Stage5C Drive Schema | PASS |
| Stage5C Isolated PhysX | 11/11 PASS |
| Stage5D swerve ground motion | PASS (4/4) |
| Current simulation stage | Stage5D complete |
| ROS2 build | PASS (`colcon build --symlink-install`, 5/5 packages) |
| ROS2 ↔ Isaac Bridge smoke test | PASS (`/clock`) |
| PHASE F ROS2 command chain | PASS (4/4 + watchdog) |
| PHASE G state feedback | PASS (`odom`, 11-joint state, `odom→base_link` TF) |
| PHASE H robot_description / TF tree | PASS (12 links, 11/11 movable joints) |
| PHASE I LiDAR + IMU baseline | PASS (RTX LaserScan, physics IMU, sensor `/tf_static`) |

Stage5D was derived as a separate overlay. Stage5C remains the protected checkpoint.

## Current USD

- Canonical USD: `/home/xkddyl/RoboMaster/Sentinel/sentinelusd/Sentry_IsaacSim_Linux/output/Sentry_stage5c_joint_drives.usda`
- Stage5C SHA256: `ffa8ecbf83a047f05cc1e4aeb3005b1fa8c09da651c273bb4a4d03a62a0dcacc`
- Stage5B SHA256: `83de4aa8f011fef97c07f4753ba22eba58405ff346d7fbb6202973e5211334bb`
- Stage5D USD: `/home/xkddyl/RoboMaster/Sentinel/sentinelusd/Sentry_IsaacSim_Linux/output/Sentry_stage5d_swerve.usda`
- Stage5D runtime report: `/home/xkddyl/RoboMaster/Sentinel/sentinelusd/Sentry_IsaacSim_Linux/output/stage5d_runtime_report.json`

ROS 2 must reference this single asset through `SENTRY_USD_PATH`; it must not copy the USD into the software workspace. Stage 5D must be derived from Stage 5C into a separate file.

## ROS2

- Distribution target: Jazzy
- Host: Ubuntu 24.04.4 LTS (Noble), amd64
- ROS apt source: `ros2-apt-source 1.2.0~noble`
- Workspace: `/home/xkddyl/RoboMaster/Sentinel/SentinelWorkspace/workspace/ros2_ws`
- Middleware target: `rmw_fastrtps_cpp`
- Domain target for the local integration: `ROS_DOMAIN_ID=0`
- Packages: `sentinel_bringup`, `sentinel_core`, `sentinel_description`, `sentinel_interfaces`, `sentinel_navigation`
- Build result: all five packages discovered from `ros2_ws/install`
- ROS-independent checks: PASS, 12/12 tests
- ROS CLI/Fast DDS smoke: PASS (`ros2 daemon start`, node/topic discovery)

`sentinel_interfaces` already owns the custom messages and services. Do not create a duplicate `sentinel_msgs` package. Do not create `sentinel_isaac_bridge` during PHASE B; PHASE D must first assess and reuse the existing integration.

## ROS Dependency State

- `/opt/ros/jazzy/setup.bash`: PASS
- `colcon`: PASS
- `rmw_fastrtps_cpp`: PASS
- `ros2_ws/install/setup.bash`: PASS
- `rosdep check --from-paths ros2_ws/src --ignore-src --rosdistro jazzy`: PASS
- Local rosdistro index: `/home/xkddyl/.ros/rosdistro-local/index-v4.yaml`
- Local rosdep source path: `/home/xkddyl/.ros/rosdep/local_sources`

`sentinel_env.sh` exports `ROSDISTRO_INDEX_URL` and `ROSDEP_SOURCE_PATH` when both local mirror files exist. The invalid `ament_python` rosdep key was removed from `sentinel_core/package.xml`; its required `<build_type>ament_python</build_type>` export remains.

## Current Blockers

- `xkddyl` is not currently listed in the `dialout` group. This does not block simulation, but serial hardware access requires a separately authorized group configuration step.
- `LOGOUT_REQUIRED_FOR_DIALOUT=NO` (the account is not yet configured as a dialout member; this is not merely an unrefreshed session).

## Existing Isaac Integration

- `isaac_sim/README.md`
- `isaac_sim/topic_contract.yaml`
- `isaac_sim/scripts/launch_stage.py`

The project launcher `isaac_sim/scripts/launch_stage.py` uses `SimulationApp`, enables `isaacsim.ros2.bridge` and `isaacsim.ros2.nodes`, opens the canonical USD, creates an environment-driven ROS2 Context and `/clock` graph, and plays the timeline. It does not own a conflicting domain fallback; `sentinel_env.sh` provides `ROS_DOMAIN_ID=0`.

Installed Isaac Sim: `6.0.1-rc.7+release.42383.32955d8d.gl` at `/home/xkddyl/issac-sim/isaac-sim`.

## Existing ROS2 / Isaac Interface Contract

- Sim → ROS: `/clock`, `/sentry/odom`, `/sentry/tf`, `/sentry/tf_static`, `/sentry/scan`, `/sentry/camera/image_raw`
- ROS → Sim plant command: `/sentry/cmd_vel_safe`
- Frames: `map → odom → base_link`, with sensor frames below `base_link`
- `sentinel_bringup/launch/sim.launch.py` starts the ROS simulation stack with simulated time, but currently does not accept `SENTRY_USD_PATH` or launch Isaac Sim.

PHASE D verified the project launcher and canonical Stage5C together over Fast DDS:

- `ROS_DOMAIN_ID=0`
- `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`
- Topic: `/clock`
- Type: `rosgraph_msgs/msg/Clock`
- Discovery: PASS
- Message received: PASS
- Launcher: `isaac_sim/scripts/launch_stage.py`
- Log: `logs/phase_d_isaac.log`

## Important Design Decisions

- The software repository and USD asset project remain separate and are joined by environment/configuration paths.
- Stage 5C is immutable as a validated checkpoint.
- Use local Fast DDS on one Ubuntu host first; do not introduce Docker, Zenoh, or CycloneDDS yet.
- Reuse the installed Isaac Sim 6.0.1 bridge extension and examples instead of guessing APIs.
- Validation output and process exit status must match the actual report result.
- Existing user modifications in `tools/ubuntu/bootstrap_jazzy.sh` and `tools/ubuntu/build.sh` are protected.
- Stage5D extracts module geometry and wheel radius from the composed USD and Stage5B report, calibrates steer/drive direction at runtime, and reloads a clean Stage5D for every motion case.
- Stage5D diagnostic material (`static friction 0.20`, `dynamic friction 0.15`, restitution `0`) and drive gains are low-speed validation baselines only. They are not measured tire properties, RL ground truth, or real M3508/GM6020 controller parameters.

## Stage5D Validation

- Straight: PASS (`dx=0.4780 m`, `dy=0.0008 m`, `dYaw=0.02 deg`)
- Lateral: PASS (`dx=0.0024 m`, `dy=0.4773 m`, `dYaw=-0.16 deg`)
- Diagonal: PASS (`dx=0.3583 m`, `dy=0.3552 m`, `dYaw=-0.08 deg`)
- Rotate: PASS (`dx=0.0263 m`, `dy=-0.0451 m`, `dYaw=78.16 deg`)
- Normal gravity: PASS
- Ground collision: PASS
- Runtime JSON gate: PASS (`pass_count=4`, `expected_count=4`, `runtime_validation_all_pass=true`)

## PHASE F Command Integration

- Command chain: `/cmd_vel` → `sentinel_core/safety_supervisor` → `/sentry/cmd_vel_safe` → Isaac Stage5D → four steer/four drive joints
- Message type: `geometry_msgs/msg/Twist`
- Body command semantics: `linear.x=vx`, `linear.y=vy`, `angular.z=wz`
- Safety limits: `|vx|≤0.20 m/s`, `|vy|≤0.20 m/s`, `|wz|≤0.60 rad/s`
- Non-finite command rejection: enabled
- Command timeout: `0.5 s`
- Watchdog automatic wheel stop: PASS
- ROS-driven Straight: PASS (`dx=0.2441 m`, `dy=-0.0019 m`, `dYaw=-3.74 deg`)
- ROS-driven Lateral: PASS (`dx=0.0014 m`, `dy=0.2368 m`, `dYaw=0.45 deg`)
- ROS-driven Diagonal: PASS (`dx=0.2086 m`, `dy=0.2056 m`, `dYaw=-7.20 deg`)
- ROS-driven Rotate: PASS (`dx=0.0169 m`, `dy=-0.0258 m`, `dYaw=48.23 deg`)
- Report: `isaac_sim/output/phase_f_runtime_report.json`
- Test evidence: `isaac_sim/output/phase_f_topic_evidence.json` (real ROS subscriptions, no synthesized PASS fields)
- PHASE F1 evidence snapshot: 127 raw ROS messages, 4000 safe ROS messages, 593 nonzero Isaac control ticks
- PHASE F1 `/clock` evidence and safe topic type evidence: PASS
- Isaac log: `logs/phase_f_isaac.log`

## PHASE G State Feedback

- `/sentry/odom`: PASS, `nav_msgs/msg/Odometry`
- `/joint_states`: PASS, `sensor_msgs/msg/JointState`, 11 actual articulation DOFs
- `/tf`: PASS, dynamic `odom → base_link`
- `/tf_static`: not required in PHASE G; the current interface URDF would create a conflicting `base_footprint → base_link` parent and is deferred to PHASE H
- State publish rate: `50 Hz` simulation-time cadence
- Odom origin: recorded after normal ground-contact settling; initial pose is zero-relative
- TF and odom are generated from the same actual PhysX transform
- Feedback evidence: 654 odom, 654 joint-state and 654 matching TF messages
- Stationary, Straight, Lateral and Rotate gates: PASS
- TF/Odom translation error: `0 m`; yaw error: `0 rad`
- Report: `isaac_sim/output/phase_g_runtime_report.json`
- Evidence: `isaac_sim/output/phase_g_topic_evidence.json`
- Contract correction: tf2 topics are standard global `/tf` and `/tf_static`, not namespaced `/sentry/tf*`

## PHASE H Robot Description and TF Ownership

- Generated semantic URDF root: `base_link`; `base_footprint` removed to prevent a second parent
- URDF topology matches Stage5D: four `steer → drive` branches and `yaw_big → yaw_small → pitch`
- 12 links, 11 continuous joints; joint names match Isaac `/joint_states` 11/11
- Joint origins and axes derive from Stage4 USD joint frames using `metersPerUnit=0.001`
- Mapping report: `isaac_sim/output/phase_h_usd_to_urdf_mapping.json`
- Physical joint limits are not calibrated; no fictional limits are authored
- TF ownership: Isaac publishes `odom → base_link`; robot_state_publisher publishes `base_link → robot links`
- TF root: `odom`; cycle: none; duplicate parent: none; missing physical links: none
- Joint TF motion: PASS for all four steer and drive branches
- `/tf_static` remains absent because this Stage5D semantic tree currently has no fixed joints
- Runtime report: `isaac_sim/output/phase_h_runtime_report.json`

## PHASE I LiDAR + IMU Simulation Baseline

- Status: COMPLETE
- LiDAR source: Isaac Sim 6.0.1 experimental RTX `Example_Rotary_2D`, published as real ray-derived `sensor_msgs/msg/LaserScan`
- LiDAR pose source: diagnostic placeholder, confidence `HISTORICAL_PLACEHOLDER`; `xyz=(0,0,0.80 m)`, `NOT HARDWARE CALIBRATED`
- IMU source: Isaac Sim 6.0.1 experimental physics `IMU/IMUSensor`
- IMU physical simulation pose is composed from the diagnostic base-to-LiDAR mount and Mid-360 internal geometry; the robot mount remains `NOT HARDWARE CALIBRATED`
- Sensor pose warning: sensor pose is diagnostic placeholder; must be replaced with measured real-robot extrinsics before Sim2Real.
- LiDAR parameters: `SIMULATION_BASELINE_ONLY`; 15 Hz, 360 deg FOV, 0.16875 deg angular resolution, 0.2–30.0 m
- LiDAR obstacle gate: PASS; runtime-only front box expected `1.75 m`, measured `1.6645 m`, absolute error `0.0855 m`
- IMU acceleration semantics: `get_data(read_gravity=True)` is a specific-force-style reading including support against gravity. On this millimeter Stage5D backend raw acceleration scales by `1/metersPerUnit^2`; the publisher converts it to ROS SI `m/s^2`.
- IMU stationary: PASS (`|angular velocity| max=0.0123 rad/s`, acceleration magnitude `9.8100 m/s^2`)
- IMU rotate response: PASS (`angular_velocity.z=0.3645 rad/s`, positive odom yaw `0.2846 rad`)
- IMU straight sanity: PASS (response `0.00410 m/s^2` > noise-derived threshold `0.00335 m/s^2`, odom `dx=0.0848 m`)
- `/tf_static`: PASS; `base_link→lidar_link→imu_link` observed from robot_state_publisher
- TF graph: sensor links reachable from `odom`, no cycle, no duplicate parent
- URDF: 14 links, 11 movable joints unchanged, 2 fixed sensor joints
- Reports: `isaac_sim/output/phase_i_runtime_report.json`, `isaac_sim/output/phase_i_topic_evidence.json`
- Regressions: PHASE H PASS, PHASE G PASS, PHASE F PASS, PHASE D PASS, Stage5D 4/4 PASS
- All sensor extrinsics and LiDAR parameters above are simulation baselines, not measured hardware truth.

## PHASE I2 Mid-360-compatible Sensor Contract

- Status: COMPLETE
- Hardware target: Livox Mid-360; fidelity `MID360_GEOMETRIC_BASELINE`
- Primary LiDAR data: `/sentry/lidar/points`, `sensor_msgs/msg/PointCloud2`, frame `lidar_link`
- Auxiliary 2D data: `/sentry/scan`, `sensor_msgs/msg/LaserScan`; not a Point-LIO input
- Point fields: `x`, `y`, `z`, `intensity`, `time`
- Per-point time: native Isaac RTX `timeOffsetNs`, normalized to frame-relative `time` in seconds; source `NATIVE_ISAAC`; Point-LIO `timestamp_unit=SEC`
- Point timing gate: PASS; within-frame span `0.0999967 s`, finite and monotonic during stationary, rotate and straight tests
- 3D cloud evidence: 40 messages, 2,619,392 finite XYZ points, 65,484.8 points/frame; z span `1.0261 m`
- Runtime-only front/left/elevated diagnostic geometry: PASS; no obstacle is persisted to Stage5D
- Hardware target profile: 360 deg horizontal, -7..+52 deg vertical, 0.1 m blind zone, 200,000 points/s, 10 Hz, ICM40609 IMU at 200 Hz
- Actual simulation profile: Isaac RTX `Example_Rotary`, 360 deg horizontal, -15..+10 deg vertical, mechanical rotary pattern, measured `231,804.6 points/s` and `3.451 Hz`
- Simulation performance difference: actual frame and IMU publish rates are not presented as hardware-equivalent; measured IMU rate `30.973 Hz` versus 200 Hz hardware target
- Exact Livox non-repetitive scan pattern: NO; the simulation is not `MID360_SENSOR_GROUND_TRUTH`
- Axis semantics: Livox/ROS use x-forward, y-left, z-up. RTX GMO spherical azimuth/elevation/distance is explicitly converted with the installed Isaac Cartesian convention; no hidden axis swap
- Base-to-LiDAR: diagnostic placeholder, confidence `HISTORICAL_PLACEHOLDER`, `NOT HARDWARE CALIBRATED`
- Mid-360 LiDAR-to-IMU TF: `[+0.01100,+0.02329,-0.04412] m`, identity rotation, source Mid-360 hardware internal geometry; IMU axes aligned with point-cloud axes
- Future Point-LIO direction: LiDAR pose in IMU body frame; aligned-axis `extrinsic_T=[-0.01100,-0.02329,+0.04412] m`
- IMU acceleration regression: raw millimetre-stage scale converted by `metersPerUnit^2=1e-6` to ROS `m/s^2`; stationary/rotate/straight PASS
- TF: `odom→base_link→lidar_link→imu_link`, `/tf_static` PASS, no cycle, no duplicate parent
- Contract document: `docs/MID360_SIM_CONTRACT.md`
- Reports: `isaac_sim/output/phase_i2_runtime_report.json`, `isaac_sim/output/phase_i2_topic_evidence.json`
- Regressions: legacy PHASE I PASS, PHASE H PASS, PHASE G PASS, PHASE F PASS, PHASE D PASS, Stage5D 4/4 PASS
- Sim2Real boundary: SIM uses Isaac RTX PointCloud2 + per-point timing; REAL uses Mid-360 through `livox_ros_driver2` CustomMsg; a future Point-LIO adapter is the convergence layer.

## Next Phases

## PHASE J Point-LIO Functional Integration

- Status: BLOCKED; Point-LIO has not been started and is not marked COMPLETE.
- Point-LIO source: branch `RM2025_SMBU_auto_sentry`, commit `e85e79558cf746f6699888a54285fe48b3b0ac71`, package `point_lio`, executable `pointlio_mapping`.
- Verified simulation parser: generic PointCloud2 `lidar_type=2`; fields `x,y,z,intensity,time`; integer `timestamp_unit=0` for seconds; internal time is milliseconds. A fake `ring=0` field is not added.
- Verified extrinsic definition: LiDAR pose in IMU body frame; `T=[-0.01100,-0.02329,+0.04412] m`, identity rotation.
- J0.6 publishes only distinct experimental IMU backend readings from the official post-physics-step callback without changing physics dt. Measured unique IMU cadence is `60.000 Hz`, with zero duplicate timestamps.
- Functional J-only RTX profile: 30 Hz simulation rotary scan setting, measured primary cloud cadence `7.692 Hz`; legacy I2 10 Hz configuration remains unchanged.
- Functional simulation rate gate: PASS (`LiDAR>=7 Hz`, unique IMU `>=25 Hz`).
- Hardware target: LiDAR 10 Hz, IMU 200 Hz. `HARDWARE_FIDELITY_RATE=DEGRADED`; this is `SIMULATION_RATE_DEGRADED` and is NOT MID360 HARDWARE RATE EQUIVALENT.
- Official dependencies prepared: `Livox-SDK2` commit `08f523c930b2f0ba1e98a6afaa8d7476bf479908`; `livox_ros_driver2` branch `master`, commit `4a1def929e5b59c7a8122d19fce6efba581ce9f7`.
- Blocker: `ros-jazzy-pcl-ros` is missing. Installation was authorized but local sudo requires an interactive password, so Jazzy build and Point-LIO runtime gates remain unexecuted.
- Point-LIO output topics and motion metrics are therefore NOT VALIDATED. GUI `--with-lio` rejects startup until a truthful report contains `FUNCTIONAL_POINT_LIO_PASS=true`.

## PHASE J1 Isaac GUI Interactive Baseline

- Status: COMPLETE (Point-LIO disabled by default).
- Entry: `./tools/integration/run_sentinel_gui.sh`; diagnostic entry: `./tools/integration/run_sentinel_gui.sh --diagnostic`.
- Reuses `isaac_sim/scripts/launch_stage.py`; starts Stage5D swerve control, state publishers, sensors, robot_state_publisher and safety_supervisor.
- Diagnostic geometry is runtime-only and asymmetric. Isaac 6.0.1 official RTX `draw-point-cloud` writer provides viewport visualization; no ROS-derived fake draw and no Stage5D save.
- Keyboard control publishes only `/cmd_vel`, has inactivity zeroing and sends zero on exit.
- GUI readiness checks actual `/clock`, `/sentry/odom`, `/sentry/lidar/points`, `/sentry/imu` messages and the safe-command subscriber chain.
- `phase_j1_gui_preflight.sh`: PASS. Manual checklist: `docs/ISAAC_GUI_VALIDATION.md`.
- Regressions after J1: PHASE I2 PASS, PHASE I PASS, PHASE H PASS, PHASE G PASS, PHASE F PASS, PHASE D PASS, Stage5D 4/4 PASS.

- PHASE B: unified project entry — COMPLETE
- PHASE C: ROS2 Jazzy dependencies and first build — COMPLETE
- PHASE D: ROS2 ↔ Isaac Sim `/clock` smoke test — COMPLETE
- PHASE E: Stage5D four-module swerve control — COMPLETE
- PHASE F: ROS2 `/cmd_vel` → swerve controller — COMPLETE
- PHASE G: odom + joint_states + tf — COMPLETE
- PHASE H: robot_description + complete ROS2 TF tree — COMPLETE
- PHASE I: simulation sensors, LiDAR + IMU baseline — COMPLETE
- PHASE I2: Mid-360-compatible 3D PointCloud + per-point timing contract — COMPLETE
- PHASE J: Point-LIO functional integration — BLOCKED by missing system dependency; not COMPLETE
- PHASE J1: Isaac GUI interactive baseline — COMPLETE

## Verification Commands

```bash
bash -n tools/integration/sentinel_env.sh
bash -n tools/integration/check_environment.sh
bash -n tools/integration/build_ros2.sh
bash -n tools/integration/run_isaac.sh
bash -n tools/integration/ros2_isaac_smoke_test.sh
source tools/integration/sentinel_env.sh
./tools/integration/check_environment.sh
./tools/integration/ros2_isaac_smoke_test.sh
./tools/integration/phase_f_cmd_vel_test.sh
sha256sum "$SENTRY_USD_PATH"
cd /home/xkddyl/RoboMaster/Sentinel/sentinelusd/Sentry_IsaacSim_Linux
./run_stage5d.sh --dry-run
./run_stage5d.sh
```
