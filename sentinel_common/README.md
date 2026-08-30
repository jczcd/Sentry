# sentinel_common

Hardware-independent C++17 algorithms shared by the simulator, host tests, and STM32 firmware.

The first committed module provides:

- four-module swerve inverse kinematics;
- shortest steering-path optimization;
- zero-speed steering hold;
- uniform wheel-speed saturation;
- forward kinematics through a fixed 3x3 least-squares solve.

All public values use SI units. The module contains no ROS, Isaac, HAL, FreeRTOS, CAN, UART, dynamic allocation, exception, or RTTI dependency.

Geometry values in the tests are examples. Do not copy them to the robot until the physical module positions, wheel radius, gear ratio, motor direction, and steering zero have been measured.
