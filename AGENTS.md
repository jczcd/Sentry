# Sentinel repository instructions

## Read first

Before changing code, read:

1. `PROJECT_STATE.md`
2. `HARNESS_RMUL_SENTRY_MASTER_FRAMEWORK.md`
3. the document for the subsystem being changed

Do not turn an archived PASS statement into a current PASS. The latest recoverable model state is `MANUAL_VISUAL_APPROVAL_REQUIRED`.

## Current scope

The active engineering line is Phase 1: four-module swerve foundations and a trustworthy Isaac model baseline. Do not start Point-LIO, Nav2, terrain, behavior-tree, or RL implementation until the corresponding Gate is explicitly passed.

## Protected conclusions

- V2 model output and its FULL package are `INVALID_VISUAL_ASSEMBLY`.
- Historical Stage5C hash `ffa8ecbf83a047f05cc1e4aeb3005b1fa8c09da651c273bb4a4d03a62a0dcacc` identifies an old checkpoint only.
- Historical Stage5D straight/lateral/diagonal/rotate results are not current recovery evidence.
- V3 HOOPS Variant A uses `globalXforms=false` and is the recommended raw candidate. It still needs human visual approval.
- Do not retry a global `set_physics_dt(1/200)` experiment; it previously caused RTX LiDAR device loss and crashes.

## Control and safety ownership

- Planner, teleop, MCP, and policy outputs enter through `/cmd_vel`.
- `safety_supervisor` alone publishes `/sentry/cmd_vel_safe`.
- A simulation adapter or hardware bridge consumes the safe command; never both for the same actuator.
- STM32 owns the hard real-time motor loops, final limits, watchdog, power fallback, and emergency stop.
- MCP is diagnostic by default. Motion requires explicit human enable and must never bypass the safety path.
- Exactly one component owns each dynamic TF edge and each actuator loop.

## Shared C++ rules

`sentinel_common` must remain independent of ROS, Isaac Sim, STM32 HAL, FreeRTOS, CAN, and UART. Keep it suitable for C++17 embedded builds:

- no dynamic allocation in the control path;
- no exceptions or RTTI requirement;
- fixed-size containers;
- explicit SI units in names;
- no hidden fixed control period;
- deterministic, host-testable pure calculations.

## Repository safety

- Preserve user changes and dirty worktrees.
- Do not run destructive Git commands or force-push.
- Do not commit credentials, private keys, machine passwords, internal IP logs, installers, archives, STEP files, generated USD, build trees, or rosbag data.
- Do not vendor third-party repositories. Record repository URL, branch, and commit instead.
- Archived scripts are evidence and migration aids; update active documentation rather than silently rewriting historical records.

## Minimum verification

For shared C++ changes:

```bash
cmake -S . -B build -DSENTRY_BUILD_TESTS=ON
cmake --build build
ctest --test-dir build --output-on-failure
```

For shell/Python changes, run syntax checks. Before a commit, run `git diff --check`, a secret scan, and a large-file scan.
