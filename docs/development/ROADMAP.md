# Development roadmap

The top-level policy remains `HARNESS_RMUL_SENTRY_MASTER_FRAMEWORK.md`. This file maps it to the recovered project state.

## Immediate recovery sequence

1. Recover or recreate the exact V3 Variant A raw candidate.
2. Run human visual review in Isaac Sim and record approval/rejection.
3. If approved, create semantic link mapping without changing geometry.
4. Rebuild articulation and verify all 11 revolute joints.
5. Rebuild static physics and joint drives with evidence reports.
6. Re-run Stage5D straight, lateral, diagonal, and rotation tests.
7. Only then connect the shared C++ swerve core to the virtual lower controller.

## Product phases

| Phase | Deliverable | Entry condition |
|---|---|---|
| P1 Swerve foundation | measured geometry, IK/FK, optimization, odom, follow, spin | valid visual/articulation baseline |
| P2 Digital twin | repeatable robot and Phase1 test world | P1 algorithms host-tested |
| P3 Localization | single Mid-360 Small Point-LIO odometry | sensor timing/schema verified |
| P4 Relocalization | prior map and `map -> odom` | stable LIO |
| P5 Navigation baseline | repeatable HOME-CONTROL-PATROL-HOME | stable localization |
| P6 Safety | timeout, collision, localization, power, zone fallbacks | baseline navigation |
| P7 Local RL | measurable residual improvement with fallback | safety Gate passed |
| P8 Tactical BT | complete match flow without tactical RL | navigation and referee state stable |
| P9 Tactical RL | goal-level improvement over BT baseline | complete BT benchmark |

## Parallel hardware path

The hardware team can proceed without waiting for the full Isaac model on:

- motor ID and direction inventory;
- module geometry measurement;
- steering-zero fixture and calibration procedure;
- host-MCU frame codec and fuzz tests;
- CAN-load measurement;
- command watchdog and fault-state tests with power stage disabled;
- single-module suspended testing.

Interfaces and units must be frozen jointly so simulation and hardware do not diverge.
