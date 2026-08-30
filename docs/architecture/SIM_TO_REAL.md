# Sim-to-Real and Isaac Sim

Sim-to-Real is the engineering process; Isaac Sim is one tool inside that process.

Isaac Sim supplies a controllable physics model, virtual sensors, ground truth, repeatable test scenes, and failure injection. It does not automatically turn Python or USD into STM32 firmware. Transfer succeeds only when the simulator and robot share contracts, algorithms, coordinates, tests, and measured parameters.

## What is reused

| Module | Reuse policy |
|---|---|
| Swerve IK/FK | same C++17 source where practical |
| Steering shortest-path optimization | same source |
| Angle wrapping and uniform saturation | same source |
| Follow/spin mode math | same source after it is added and tested |
| PID/filter structure | shared implementation possible; gains and calibration are not shared blindly |
| ROS command/state messages | same external contract |
| Test vectors and Gate criteria | same scenarios and tolerances where physics permits |

## What is replaced

| Isaac side | Real side |
|---|---|
| articulation joint writer | motor target and CAN-current pipeline |
| simulated joint state | encoder/CAN feedback |
| simulated IMU | calibrated physical IMU driver |
| simulated LiDAR | Mid-360 driver |
| `/clock` | host and MCU monotonic time |
| ideal geometry | measured geometry and calibrated offsets |
| simulated gains/friction | system identification and real tuning |

## Correct adapter pattern

```text
ROS command
  -> adapter input
  -> hardware-independent algorithm
  -> adapter output
```

The virtual lower controller converts `/sentry/cmd_vel_safe` to Isaac joint targets. The hardware bridge frames the same safe body command for STM32. On the MCU, the shared algorithm produces steering and drive targets before hard real-time loops.

Do not bury kinematics inside USD Prim access, ROS callback code, HAL drivers, or CAN handlers. Those APIs are adapters, not the algorithm.

## Parameter transfer

The simulator begins with nominal values. The robot provides measured distributions:

- mass and inertia;
- wheel radius and module coordinates;
- tire-ground friction and slip;
- gearbox backlash and dead zone;
- steering-zero error;
- motor and communication latency;
- control-period jitter;
- IMU noise, bias, mounting rotation, and temperature drift;
- battery-voltage and power-limit behavior.

Feed those measurements back into the simulator as parameter identification and domain randomization. Do not treat randomization as a substitute for calibration.

## Promotion sequence

1. Host unit tests for pure algorithms.
2. Isaac deterministic motion tests.
3. Cross-build the same C++ for ARM.
4. Compare host and ARM test vectors.
5. MCU test with simulated feedback and motors disabled.
6. One motor, then one suspended swerve module.
7. Four suspended modules with offline-stop tests.
8. Low-speed ground test under current and velocity limits.
9. Pose comparison against external localization.
10. Only then add autonomous navigation or learned policies.

The value of simulation is not avoiding real-robot work. It separates mathematical/interface defects from calibration, wiring, dynamics, and hardware faults before energy is applied.
