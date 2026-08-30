# Test Gates

No phase advances on narrative confidence alone. Each Gate needs artifacts, commands, measurements, and a clear PASS/FAIL decision.

## G0 - Source and model identity

- canonical source hash recorded;
- converter version and parameters recorded;
- model opens without missing references;
- independent visual approval recorded;
- no invalidated model reused.

Current status: **BLOCKED at manual V3 visual approval**.

## G1 - Swerve math

- host IK/FK unit tests pass;
- forward, strafe, diagonal, rotation, and combined commands round-trip;
- shortest-path optimization and zero-speed hold pass;
- wheel saturation preserves motion ratios;
- x86 and ARM test vectors agree within an explicit tolerance;
- measured geometry replaces template `null` values.

## G2 - Isaac motion

- accepted articulation has exactly the expected DOF and ownership;
- forward, backward, strafe, diagonal, and rotation pass from fresh starts;
- command timeout stops the robot;
- no direct pose teleport is used to fake motion;
- wall-time latency and real-time factor are recorded.

## G3 - Host/MCU protocol

- golden vectors for every frame type;
- CRC, truncated, oversized, reordered, duplicate, stale, NaN/Inf, and out-of-range cases tested;
- protocol version mismatch fails closed;
- 100 ms zero-target and 500 ms disable behavior measured;
- motor power remains disabled during decoder fuzzing.

## G4 - Suspended hardware

- one motor direction and feedback verified;
- one full swerve module calibrates and takes the shortest path;
- all four suspended modules execute canonical commands;
- any critical steer motor loss causes a stop;
- estop and communication-loss tests pass.

## G5 - Low-speed ground test

- current, speed, acceleration, and test-area limits active;
- forward/strafe/rotate directions match REP-103;
- odometry compared to an external reference;
- wheel radius, dead zone, slip, and latency identified;
- no unexplained power or thermal fault.

## G6 - Sensors and localization

- point-cloud fields, frames, per-point time, QoS, and rates verified;
- IMU bias, mounting, timing, and temperature behavior verified;
- only one `odom -> base_link` publisher;
- LIO publishes separately during simulation truth comparison;
- dropout and degraded-localization fallbacks pass.

## G7 - Navigation and policy

- baseline navigation succeeds repeatedly before RL;
- safety supervisor cannot be bypassed;
- policy timeout, NaN/Inf, and out-of-distribution fallback pass;
- learned controller shows a measured benefit over the baseline;
- real-robot promotion follows the low-energy staged sequence.
