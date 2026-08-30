# STM32 firmware boundary

The real firmware is not recovered in this repository. This directory records the intended ownership before MCU code is added.

The lower controller must own:

- motor CAN parsing and transmission;
- encoder unwrapping and steering-zero calibration;
- four-module inverse kinematics or the final accepted equivalent;
- steering position, drive speed, and motor-current loops;
- gimbal stabilization and hard joint limits;
- command watchdog and emergency stop;
- final power/current limiting and referee-system fallback;
- deterministic timestamps and telemetry publication to the host.

The host owns mapping, localization, path planning, tactical decisions, perception, and policy inference. See `docs/architecture/CONTROL_OWNERSHIP.md` and `docs/hardware/LOWER_CONTROLLER.md` before implementing this directory.
