# Mid-360-compatible simulation contract

> 本文件定义传感器接口，不代表当前 USD 已通过人工验收。使用 Isaac 前必须显式设置
> `SENTRY_MODEL_APPROVED=1` 和 `SENTRY_USD_PATH`；历史 Phase I/J 报告不能替代当前 Gate。

PHASE I2 establishes sensor messages only. It does not run Point-LIO, SLAM, Nav2,
or state estimation.

## Data boundary

- Simulation: Isaac RTX 3D returns with native per-return nanosecond timestamps are
  normalized to `/sentry/lidar/points` (`sensor_msgs/msg/PointCloud2`) fields
  `x`, `y`, `z`, `intensity`, `time`. `time` is the acquisition offset from the
  first return in the message, in seconds. Future Point-LIO must use its
  Velodyne-style PointCloud2 parser with `timestamp_unit: SEC`.
- Real robot: Livox Mid-360 is owned by `livox_ros_driver2` and normally supplies
  `livox_ros_driver2/msg/CustomMsg` with `timebase` plus per-point `offset_time`.
- Future convergence: a Phase J Point-LIO adapter/configuration selects either
  simulation PointCloud2 or real Livox CustomMsg. Simulation does not impersonate
  the Livox Ethernet driver.

`/sentry/lidar/points` is primary LiDAR data. `/sentry/scan` remains an auxiliary
2D diagnostic/compatibility topic and is not the Point-LIO input.

## Fidelity and extrinsics

The hardware target is Livox Mid-360 (360 degree horizontal FOV, -7 to +52 degree
vertical FOV, 0.1 m blind zone, nominal 200000 points/s at 10 Hz, 200 Hz ICM40609
IMU). The current Isaac `Example_Rotary` model is a mechanical rotary pattern and
is classified `MID360_GEOMETRIC_BASELINE`; it is not the exact Livox
non-repetitive optical pattern.

`base_link -> lidar_link` remains a diagnostic placeholder and is **NOT HARDWARE
CALIBRATED**. The Mid-360 manual locates the IMU origin in point-cloud coordinates
at `[0.011, 0.02329, -0.04412]` metres with aligned axes, so ROS TF uses
`lidar_link -> imu_link` with that translation and identity rotation. Livox and
ROS use x-forward/y-left/z-up. The `Example_Rotary` GMO encodes returns as
azimuth degrees, elevation degrees, and distance metres; the adapter applies the
installed Isaac point-cloud node's spherical-to-Cartesian convention, with no
additional axis rotation. Point-LIO
defines its extrinsic as the LiDAR pose in the IMU body frame; with aligned axes,
the corresponding future `extrinsic_T` is `[-0.011, -0.02329, 0.04412]` metres.
