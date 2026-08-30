# Sentinel Isaac Sim GUI 人工验收

> 当前验收是 Gate，不是历史报告的重放。V2 模型的视觉结论已撤销；V3 Variant A 只有自动取证，仍需人工确认。必须先设置 `SENTRY_MODEL_APPROVED=1` 并显式提供 `SENTRY_USD_PATH`，否则启动脚本会拒绝运行。

当前 GUI baseline 使用经人工批准的 USD、ROS 2 safety flow、真实 RTX 3D LiDAR 和 Isaac physics IMU。运行期传感器、墙体和障碍物不会保存进 USD。不要在 Isaac Sim 中执行 Save、Save As 或 Flatten。

## 启动

第一终端：

```bash
./tools/integration/run_sentinel_gui.sh --diagnostic
```

第二终端：

```bash
./tools/integration/sentry_teleop.sh
```

第三终端（可选）：

```bash
./tools/integration/sentinel_gui_status.sh
```

可用 `--rviz` 同时打开仅包含 RobotModel、TF、RTX PointCloud2 和 Isaac odometry 的 RViz。只有 `phase_j_runtime_report.json` 证明 Point-LIO functional PASS 后，`--with-lio` 才会被接受；未验证时会明确拒绝。

## A. Robot

- 确认机器人没有掉地，轮子没有穿模。
- 四个 steer/drive module 位置正常。
- yaw_big、yaw_small、pitch 云台层级和位置正常。
- LiDAR 安装位置在仿真中合理；注意 base→LiDAR 仍是诊断 placeholder，不是实车标定外参。

## B. Drive

- `W`：直行；`A`：左横移；`W+A`：左前斜移；`Q`：原地左旋。
- `SPACE` 或 `X`：立即停止。
- 观察 steer 先转向、drive 后驱动，没有异常轮胎拖拽。
- 键盘超时或 Ctrl+C 后必须看到零速度；所有命令都发布到 `/cmd_vel` 并经过 safety_supervisor。

## C. LiDAR

- `--diagnostic` 默认启用 Isaac 6.0.1 官方 `draw-point-cloud` RTX writer。
- 确认真正的 3D 点云在 viewport 可见，front/side/elevated geometry 均产生回波。
- 机器人运动时点云持续刷新。显示只用于 debug，不进入碰撞，也不是从 ROS cloud 反画的假点。

## D. IMU

- 静止时 angular velocity 接近零，但不要求严格为零。
- `Q` 左旋时 `/sentry/imu.angular_velocity.z` 为正。
- 启动和停止时 linear acceleration 有有限响应。

## E. TF

确认拓扑为 `odom → base_link → lidar_link → imu_link`，无跳变、环或 duplicate parent。

## F. Point-LIO

仅在 PHASE J FUNCTIONAL PASS 后使用 `--with-lio`：

- 比较 GT `/sentry/odom` 和估计 `/sentry/lio/odom`。
- 分别测试直行、横移、旋转和组合全向运动。
- 方向不能反向，估计不能飞散或突然跳几十米。
- `/sentry/lio/cloud_registered` 应持续、有限且稳定。

当前 Mid-360 hardware rate target 是 LiDAR 10 Hz、IMU 200 Hz；仿真 profile 必须单独报告实际 rate，不能称为硬件等价。
