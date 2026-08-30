# Rules and hardware reference index

Official PDFs are not copied into this public repository. The following page references were verified against the locally supplied 2026 editions.

## RMUL 2026 competition rules V1.2.0 (2026-01-09)

- PDF p. 19: the sentinel must run fully automatically, may fire 17 mm projectiles, may have at most one remote controller for debugging, and may not use multi-robot communication.
- PDF p. 20: sentinel initial/max HP is 400; chassis power limit is 100 W; shooting heat limit is 260; chassis-power overrun rules apply.
- PDF p. 30: the referee system monitors chassis power at 10 Hz. Power overrun consumes buffer energy; when the buffer is exhausted and overrun continues, chassis power is cut for five seconds.
- PDF p. 62 and p. 71: after the preparation stage the sentinel debug controller must be placed at the designated battlefield entrance and may not be used after the countdown begins.

Engineering consequences:

- autonomous operation cannot depend on a human remote controller;
- final power protection must remain in the lower controller even if the host also pre-limits commands;
- referee-system state and offline conditions belong in the safety state machine;
- MCP or teleop is a controlled debug path, not a competition control path.

## Robot construction specification V1.3.0 (2026-02-09)

- PDF pp. 14-17: general control, remote-controller, supercapacitor, and wireless-device constraints.
- PDF p. 17, S21: robots may not carry wireless communication equipment beyond the listed permitted categories.
- PDF p. 42, S113: the sentinel must support horizontal movement and firing 17 mm projectiles.
- PDF p. 43, S114: sentinel construction parameters include at most one remote controller for debugging and a 300 Wh maximum total supply capacity.
- PDF p. 66: the referee power-management allocation includes chassis, gimbal, 17 mm launcher, and Mini PC power for the sentinel.
- PDF pp. 77-78, S159: armor-module non-obstruction regions apply to hero, infantry, and sentinel robots.
- PDF p. 98, S187: hero, infantry, and sentinel robots must install the supercapacitor management module even when no supercapacitor module is used.

## RoboMaster development board C

Local reference set:

- gyroscope FPC placement and schematic;
- board placement and schematic;
- C-board instructions and user manual;
- embedded-software tutorial.

Useful verified locations:

- user manual pp. 10-15: USB FS, two UART, two CAN, PWM, and DBUS interfaces;
- user manual pp. 12-13: voltage/interface caveats and enclosure-to-MCU UART naming mismatch;
- user manual p. 20: BMI088 IMU;
- tutorial pp. 193-204: 1 Mbps CAN configuration and motor examples;
- tutorial pp. 224-240: IMU temperature control;
- tutorial pp. 264-269: Mahony attitude example.

Always check for a newer official rule/manual revision before inspection or competition. A page summary in this repository is not a substitute for the current official document.
