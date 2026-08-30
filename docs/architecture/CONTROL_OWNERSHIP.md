# Control ownership

The same calculation may exist in tests and simulation, but one runtime component owns each output.

## Runtime ownership matrix

| Function | Simulation owner | Real-robot owner | Notes |
|---|---|---|---|
| Tactical goal | BT/FSM or later tactical policy | same host component | Never runs on STM32. |
| Global/local path | host planner | host planner | Produces desired body motion. |
| Raw chassis command | active source through arbiter | active source through arbiter | Exactly one active source. |
| Safe chassis command | ROS safety supervisor | ROS safety supervisor | Only publisher of `/sentry/cmd_vel_safe`. |
| Four-swerve IK | virtual lower controller | STM32 recommended | Must use the same formulas and parameters; do not solve twice in the real command path. |
| Steering target optimization | virtual lower controller | STM32 | Requires current steering feedback. |
| Steering/drive motor loops | Isaac drive/controller | STM32 | One final actuator-loop owner. |
| Chassis-follow mode | virtual lower controller | STM32 recommended | Path following remains on the host; gimbal-relative chassis follow is lower-level. |
| Fast attitude estimate | simulated sensor algorithm | STM32 | Used for stabilization and motor control. |
| Global pose estimate | Isaac truth or LIO | host state estimator/LIO | Used for navigation. |
| Power fallback | simulated check | STM32 final owner | Host may pre-limit, but MCU must enforce final fallback. |
| `odom -> base_link` | Isaac | real state estimator | Never publish both. |
| `map -> odom` | localization/relocalization | localization/relocalization | Only when map localization is enabled. |
| `base_link -> robot links` | robot_state_publisher | robot_state_publisher | Derived from joint states. |

## Useful duplication

The following duplication is intentional:

- host speed limiting plus MCU final limiting;
- host estop plus MCU communication-timeout stop;
- host navigation pose plus MCU fast attitude;
- host and MCU builds of the same pure kinematics source;
- simulator and hardware adapters tested against the same contract.

## Forbidden duplication

- host and STM32 independently applying different swerve IK in the same real command path;
- two nodes closing the same steering position loop;
- two sources publishing the same dynamic TF edge;
- Isaac and hardware backends writing the same actuator set;
- separate wheel radii, module coordinates, signs, or zero offsets with no generated single source of truth.

The rule is simple: algorithm verification can have multiple implementations or builds; final runtime authority has one owner.
