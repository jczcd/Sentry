# RTX 4090 云机下一步

## 0. 先建立可复现基线

在任何代码修改之前记录：

- Ubuntu、内核、NVIDIA驱动、GPU和显存。
- Isaac Sim真实版本与安装路径。
- ROS 2、Docker、Codex、colcon状态。
- 系统盘容量与可用空间。
- Stage5C和Stage5D哈希。

运行：

```bash
./check_4090_host.sh "$HOME/robomaster/space/Sentinel_work" \
  | tee "$HOME/sentinel_4090_host_report.txt"
```

## 1. 处理 Ubuntu 22.04 / Jazzy 兼容层

不要直接在 Ubuntu 22.04 上执行 Ubuntu 24.04 的 Jazzy apt 安装流程。

优先保留现有系统和其他工程，采用：

- 主机：Isaac Sim 6.0.1 GUI与RTX传感器。
- 容器/专用工作区：ROS 2 Jazzy外部节点、Sentinel ROS workspace、Small Point-LIO。
- 同一 `ROS_DOMAIN_ID=0`。
- 首次联调记录实际 RMW；项目基线仍是 `rmw_fastrtps_cpp`，不要静默改成其他实现。

在正式构建容器前，先让 Codex只读检查项目脚本对 `/opt/ros/jazzy`、Python版本和绝对路径的依赖。

## 2. 验证迁移结果

```bash
source "$HOME/robomaster/space/Sentinel_work/migration_4090.env"
sha256sum "$SENTRY_USD_PROJECT/output/Sentry_stage5c_joint_drives.usda"
test -f "$SENTRY_USD_PROJECT/output/Sentry_stage5d_swerve.usda"
```

Stage5C必须严格等于：

```text
ffa8ecbf83a047f05cc1e4aeb3005b1fa8c09da651c273bb4a4d03a62a0dcacc
```

## 3. Isaac GUI人工基线

先运行普通模式：

```bash
cd "$SENTRY_WORKSPACE"
./tools/integration/run_sentinel_gui.sh
```

再运行诊断模式：

```bash
./tools/integration/run_sentinel_gui.sh --diagnostic
```

逐项检查：

- 直行、横移、斜移、原地旋转、停车。
- 点云、IMU、TF、joint_states、odom。
- `/cmd_vel` 与 `/sentry/cmd_vel_safe`。
- 普通模式与 diagnostic 模式的 RTF差异。
- GPU利用率、显存、CPU单核瓶颈。

teleop：

```bash
./tools/integration/sentry_teleop.sh --timeout 0.6
```

需要时再临时测试：

```bash
./tools/integration/sentry_teleop.sh --timeout 0.6 --linear 0.18 --angular 0.5
```

不要超过 safety supervisor 限制。

如果机器人不动，先检查 `/sentry/estop`，不要先调整舵轮IK、摩擦、joint gain或Stage5D物理。

## 4. GUI响应延迟诊断

按以下顺序建立时间线：

1. 键盘事件到 `/cmd_vel`。
2. `/cmd_vel` 到 `/sentry/cmd_vel_safe`。
3. safe command 到车体速度响应。
4. wall time 与 simulation time 比值。
5. RTX LiDAR和debug draw开启/关闭差异。

4090应重新测量，不能沿用旧机器RTF约0.3的结果。

## 5. estop正规化

基线确认后才改：

- 默认仍保持安全停车。
- 仅在仿真GUI确认启动成功、ROS bridge和safety supervisor就绪后发布一次 `estop=false`。
- 保留重新触发 estop 的能力。
- 不删除 safety supervisor。

## 6. Small Point-LIO实验

优先使用 `livox_pointcloud2` adapter：

```text
LiDAR input: /sentry/lidar/points
IMU input:   /sentry/imu
LIO odom:    /sentry/lio/odom
LIO cloud:   /sentry/lio/cloud_registered
```

必须关闭或隔离 LIO 的 `odom -> base_link` TF发布。

对比指标：

- build complexity
- CPU使用率
- 仿真RTF
- LIO频率
- 直行误差
- 横移误差
- 旋转误差
- 复合全向运动误差

`/sentry/odom` 始终保留为 Isaac ground truth。

## 7. 暂停项

- terrain point-cloud processing
- Nav2
- tactical RL
- 端到端RL
- 整场 PhysX 200Hz
