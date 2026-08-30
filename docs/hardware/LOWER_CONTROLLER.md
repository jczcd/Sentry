# Lower-controller design

## Boundary

The NUC sends body-level and gimbal-level intent. The STM32/C board turns that intent into deterministic actuator control and retains the final safety authority.

### Host to MCU

- `vx_mps`, `vy_mps`, `wz_radps`;
- chassis mode and command frame;
- `yaw_big`, `yaw_small`, and `pitch` targets as agreed per mode;
- enable, estop, sequence, and timestamp;
- optional power budget supplied by the referee-state pipeline.

### MCU responsibilities

- verify frame length, version, sequence, CRC, ranges, and freshness;
- execute four-swerve target calculation and steering optimization;
- run steering-position, drive-speed, and current loops;
- run gimbal stabilization and enforce mechanical limits;
- decode CAN feedback and detect motor loss;
- read/calibrate the board IMU and maintain fast attitude state;
- enforce watchdog, estop, current/power fallback, and fault state;
- report actuator, sensor, power, fault, and timing telemetry.

### Host responsibilities

- perception, mapping, localization, path planning, behavior and tactics;
- optional policy inference;
- ROS safety checks requiring world state;
- logging, visualization, parameter management, and operator tools.

## Proposed task rates

| Task | Starting rate |
|---|---:|
| motor feedback/control | 1000 Hz |
| IMU/filter and gimbal control | 500-1000 Hz |
| host command processing | 100 Hz or event driven with freshness checks |
| full telemetry | 100-200 Hz |
| diagnostics | 20-50 Hz |
| referee-state processing | according to protocol update rate |

These values require CPU/CAN-load measurement and WCET evidence before acceptance.

## Safety state machine

States:

- `DISARMED`
- `CALIBRATING`
- `READY`
- `ACTIVE`
- `SAFE_STOP`
- `FAULT`

Initial watchdog policy:

- command age over 100 ms: request zero chassis targets;
- command age over 500 ms: disable output or enter a verified safe hold;
- any critical steer motor offline: prohibit chassis motion;
- invalid gimbal feedback: prohibit motion farther into the affected limit;
- estop: override all communication and mode commands.

These are design starting points, not yet hardware-validated thresholds.

## Host-MCU framing draft

The concrete byte layout must be frozen before firmware and bridge implementation. A suitable v0 structure is:

| Field | Purpose |
|---|---|
| SOF | fast resynchronization |
| protocol version | reject incompatible peers |
| message type | command, telemetry, fault, parameter, heartbeat |
| sequence | drop/reorder detection |
| payload length | bounded parsing |
| sender monotonic timestamp | freshness/latency evidence |
| payload | fixed-layout, SI-unit values |
| CRC16/CRC32 | corruption detection |

Never transmit raw C++ structs without explicit packing, endianness, versioning, and static size assertions. Fuzz the decoder on the host before connecting motors.

## Development-board C notes

The available user manual records:

- two CAN interfaces (manual PDF pp. 13-14);
- two exposed UART interfaces, mapped to MCU UART1/UART6, with enclosure silk labels that do not directly match the MCU numbering (pp. 12-13);
- a USB full-speed interface (p. 10);
- one DBUS input (p. 15);
- a BMI088 six-axis IMU (p. 20);
- external interface support for 3.3 V or conditionally 5 V devices, depending on the documented resistor configuration (p. 12).

The embedded tutorial shows a 1 Mbps CAN configuration and RM motor send/receive examples (tutorial PDF pp. 193-204), as well as BMI088 and Mahony material. Treat these as reference implementations, not a ready-made safe sentinel controller.

Recommended first allocation, subject to bus-load analysis:

- CAN1: eight swerve steering/drive motors;
- CAN2: gimbal and launcher motors;
- USB CDC or a dedicated UART: NUC to MCU framed protocol;
- remaining UART: referee system;
- DBUS: inspection/debug and explicitly designed emergency takeover only.

Do not connect RS-232 or RS-485 electrical levels directly to MCU UART pins. Use the correct transceiver and verify the exact connector pinout against the manual and schematic.
