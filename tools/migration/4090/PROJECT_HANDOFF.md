# Sentinel / Isaac Sim 工程交接

更新时间：2026-08-18

## 当前真实状态

- PHASE A、B、C、D、E、F、F1、G、H、I、I2：PASS。
- PHASE J PolarBear Point-LIO：BLOCKED / NOT COMPLETE。
- PHASE J1 GUI baseline：PASS。
- Stage5D 四舵轮：Straight、Lateral、Diagonal、Rotate，4/4 PASS。
- GUI 已能运动；曾经“不动”的原因之一是 safety supervisor 启动后 `/sentry/estop` 未自动解除。
- GUI/sensor stack 在旧显卡上 RTF 曾约0.3，但不能当作4090机器的结果。
- 4090云机已能打开 Isaac Sim；必须确认实际版本是否为6.0.1。
- 云机是 Ubuntu 22.04；原基线是 Ubuntu 24.04 + ROS 2 Jazzy。

## 受保护文件

```text
Sentry_stage5c_joint_drives.usda
SHA256:
ffa8ecbf83a047f05cc1e4aeb3005b1fa8c09da651c273bb4a4d03a62a0dcacc
```

禁止覆盖或重新生成 Stage5C。

Stage5D：

```text
Sentry_stage5d_swerve.usda
```

## 机器人与 TF 所有权

11个 revolute DOF：四个 steer、四个 drive、yaw_big、yaw_small、pitch。

```text
odom
└── base_link
    ├── 四个 steer/drive
    ├── yaw_big -> yaw_small -> pitch
    └── lidar_link -> imu_link
```

- Isaac 发布 `odom -> base_link`。
- robot_state_publisher 发布 `base_link -> robot links`。
- LIO 不得重复发布 `odom -> base_link`。

## 控制链

```text
/cmd_vel
  -> safety_supervisor
  -> /sentry/cmd_vel_safe
  -> Isaac Stage5D
  -> swerve controller
```

反馈：`/clock`、`/sentry/odom`、`/joint_states`、`/tf`、`/tf_static`。

## Mid-360 合同

- `/sentry/lidar/points`：`sensor_msgs/msg/PointCloud2`
- frame：`lidar_link`
- fields：`x y z intensity time`
- `time`：每点时间偏移，单位秒，来自 RTX native `timeOffsetNs`
- `/sentry/imu`：`sensor_msgs/msg/Imu`，frame `imu_link`
- `/sentry/scan`：辅助2D LaserScan

当前只是 `MID360_GEOMETRIC_BASELINE`，不是真实 Livox non-repetitive scan ground truth。

Mid-360 Lidar→IMU 外参：

```text
extrinsic_T = [-0.01100, -0.02329, +0.04412] m
extrinsic_R = identity
```

`base_link -> lidar_link` 仍是占位值，未做硬件标定。

## IMU速率边界

- 当前真实 distinct physics samples 约60Hz：功能仿真可用。
- 硬件目标200Hz：未达到硬件等价。
- 曾尝试整场 PhysX 200Hz，RTX LiDAR 出现 GPU device-lost/segfault，已回退。
- 禁止直接重试 `set_physics_dt(1/200)`。

## 当前优先级

1. 迁移完整工程并验证 Stage5C/Stage5D。
2. 在4090上重新测 GUI、RTF、RTX LiDAR和debug draw负载。
3. 分离 teleop、ROS command latency、safety supervisor latency和仿真实时倍率。
4. 基线确认后，安全地把 estop false 纳入 GUI enable 流程。
5. 优先评估 Small Point-LIO `livox_pointcloud2` adapter。
6. 保留 `/sentry/odom` 真值；LIO发布 `/sentry/lio/odom` 和 `/sentry/lio/cloud_registered`。
7. 暂不进入 terrain、Nav2、行为树或 tactical RL。

## Git保护

禁止自动执行：

```text
git reset
git restore
git clean
git checkout --
git stash
git commit
git push
```

保护用户已有修改，尤其：

```text
tools/ubuntu/bootstrap_jazzy.sh
tools/ubuntu/build.sh
```
