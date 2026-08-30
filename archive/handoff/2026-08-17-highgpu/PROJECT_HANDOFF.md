# RoboMaster Sentinel / Isaac Sim 工程完整交接

更新时间：2026-08-17

## 1. 项目目标

RoboMaster 哨兵：
- Ubuntu 24.04
- ROS 2 Jazzy
- Isaac Sim 6.0.1
- 四舵轮全向底盘
- Mid-360 LiDAR / IMU
- Small Point-LIO / Point-LIO
- 后续 terrain navigation / Nav2 / tactical RL

当前最优先：
1. 继续 Isaac Sim GUI 人工验收
2. 诊断 GUI 反应慢 / RTF
3. 修正 GUI 自动解除仿真 estop
4. 优先评估 Small Point-LIO
5. 暂不进入 Nav2 / terrain / RL

## 2. 当前已完成阶段

PHASE A: PASS
PHASE B: PASS
PHASE C: PASS
PHASE D: PASS
PHASE E: PASS
PHASE F: PASS
PHASE F1: PASS
PHASE G: PASS
PHASE H: PASS
PHASE I: PASS
PHASE I2: PASS

PHASE J Point-LIO:
BLOCKED / NOT COMPLETE

PHASE J1 GUI baseline:
PASS

## 3. 旧机器已知路径

主仓库：
/home/xkddyl/RoboMaster/Sentinel/SentinelWorkspace/workspace

ROS2：
/home/xkddyl/RoboMaster/Sentinel/SentinelWorkspace/workspace/ros2_ws

Isaac integration：
/home/xkddyl/RoboMaster/Sentinel/SentinelWorkspace/workspace/isaac_sim

USD project：
/home/xkddyl/RoboMaster/Sentinel/sentinelusd/Sentry_IsaacSim_Linux

Isaac Sim：
/home/xkddyl/issac-sim/isaac-sim

注意：旧机器目录确实拼写为 issac-sim。

新机器不要盲目硬编码这些路径，先自动探测。

## 4. ROS 环境基线

ROS_DISTRO=jazzy
ROS_DOMAIN_ID=0
RMW_IMPLEMENTATION=rmw_fastrtps_cpp

统一环境入口：
source tools/integration/sentinel_env.sh

## 5. 受保护 Stage checkpoint

Stage5C：
Sentry_stage5c_joint_drives.usda

SHA256：
ffa8ecbf83a047f05cc1e4aeb3005b1fa8c09da651c273bb4a4d03a62a0dcacc

Stage5D：
Sentry_stage5d_swerve.usda

Stage5D 已验证：
- Straight PASS
- Lateral PASS
- Diagonal PASS
- Rotate PASS
- 4/4 PASS

禁止覆盖 Stage5C。
不要为了性能优化直接修改 Stage5D 的 physics / friction / swerve IK。

## 6. 机器人结构

base_link
├── steer_FL
│   └── drive_FL
├── steer_FR
│   └── drive_FR
├── steer_RL
│   └── drive_RL
├── steer_RR
│   └── drive_RR
└── yaw_big
    └── yaw_small
        └── pitch

11 revolute DOF。

传感器 TF：
odom
└── base_link
    └── lidar_link
        └── imu_link

TF ownership：
- Isaac：odom → base_link
- robot_state_publisher：base_link → robot links

禁止 LIO 再重复广播 odom → base_link。

## 7. 当前控制链

/cmd_vel
↓
safety_supervisor
↓
/sentry/cmd_vel_safe
↓
Isaac Stage5D
↓
四舵轮控制

反馈：
/clock
/sentry/odom
/joint_states
/tf
/tf_static

GUI 已成功人工验证“机器人可以运动”。

### GUI 曾经不动的真实原因

GUI launcher 启动 safety_supervisor 后没有自动解除仿真 estop。

人工执行：

ros2 topic pub --once /sentry/estop std_msgs/msg/Bool '{data: false}'

后机器人可以正常运动。

后续必须把“仿真启动后安全解除 estop”的行为正规化到 GUI startup/enable 流程，但不要删掉 safety 机制。

## 8. GUI 入口

cd /home/xkddyl/RoboMaster/Sentinel/SentinelWorkspace/workspace

基础：
./tools/integration/run_sentinel_gui.sh

诊断模式：
./tools/integration/run_sentinel_gui.sh --diagnostic

Teleop：
./tools/integration/sentry_teleop.sh

Status：
./tools/integration/sentinel_gui_status.sh

说明：
docs/ISAAC_GUI_VALIDATION.md

### Teleop 已知 bug

曾出现：
UnboundLocalError: active referenced before assignment

原因：
run() 内对 active 重新赋值导致 Python 判定为局部变量。

修复：
在 def run(screen) 内加入：
nonlocal active

新机器/新 checkout 必须检查该修复是否已经在当前代码中。

### GUI“反应慢”

不要先改底盘参数。

优先区分：
1. teleop 输入行为
2. /cmd_vel latency
3. /sentry/cmd_vel_safe latency
4. Isaac RTF
5. RTX LiDAR / debug draw GPU负载
6. 真正 chassis dynamics

旧机器 GUI/sensor stack RTF 曾约 0.3。

但【新电脑显卡配置很高】：
- 不得把旧机器 RTF 当成新机器事实
- 必须重新 benchmark
- 先测基础 GUI，再测 diagnostic/debug draw
- 对比 real_time_factor
- 记录 GPU utilization / VRAM / CPU bottleneck

推荐 teleop 手感测试：
./tools/integration/sentry_teleop.sh --timeout 0.6

可临时：
--linear 0.18
--angular 0.5

不要超过 safety supervisor limits。

## 9. PHASE I2 Mid-360 compatible contract

Primary LiDAR：
/sentry/lidar/points
sensor_msgs/msg/PointCloud2
frame = lidar_link

fields：
x
y
z
intensity
time

time：
- 来自 Isaac RTX native timeOffsetNs
- unit = seconds
- 同一帧内 point time span > 0
- 不是每点都复制 frame stamp

Legacy：
/sentry/scan
sensor_msgs/msg/LaserScan
只作为辅助 2D topic。

IMU：
/sentry/imu
sensor_msgs/msg/Imu
frame = imu_link

## 10. Mid-360 硬件目标

LiDAR：
- 360° horizontal FOV
- vertical FOV -7° ~ +52°
- 0.1 m blind zone
- ~200000 points/s
- typical 10 Hz

IMU：
- ICM40609
- 200 Hz

当前 Isaac：
MID360_GEOMETRIC_BASELINE

不是：
MID360_SENSOR_GROUND_TRUTH

Isaac scan pattern 不是真实 Livox non-repetitive pattern。

## 11. Mid-360 内部外参

官方内部几何：
IMU position in LiDAR frame：
[+0.01100, +0.02329, -0.04412] m

axes aligned。

Point-LIO 源码定义已验证：
point_imu = extrinsic_R * point_lidar + extrinsic_T

所以 LiDAR pose in IMU frame：
extrinsic_T =
[-0.01100, -0.02329, +0.04412] m

extrinsic_R = identity

注意：
base_link → lidar_link 仍是 placeholder，
NOT HARDWARE CALIBRATED。

## 12. PolarBear Point-LIO 状态

参考：
SMBU-PolarBear-Robotics-Team/point_lio

实际 branch：
RM2025_SMBU_auto_sentry

commit：
e85e79558cf746f6699888a54285fe48b3b0ac71

parser 已审查：
- generic PointCloud2
- lidar_type=2
- x y z intensity time
- timestamp_unit=0 (seconds)
- internal ms
- valid time 存在时 ring 不是时间重建硬要求

未完成功能测试。

阻塞依赖曾包括：
- ros-jazzy-pcl-ros
- libapr1-dev
- libaprutil1-dev

不要绕过 sudo 密码。

## 13. Sensor rate 已知结论

旧机器：
- LiDAR functional simulation cadence ~7–8 Hz
- IMU unique physics samples 最终可做到 ~60 Hz
- 无重复 timestamp
- 无 fake interpolation
- Hardware fidelity rate = DEGRADED
- Functional simulation rate = PASS

曾尝试整个 PhysX 200 Hz：
- IMU 可接近 200 Hz
- RTX LiDAR repeated GPU device-lost / segfault
- 已回退

新高性能电脑：
不要直接假定该结论仍相同。
但也不要一上来再次把正式 Stage5D 全局切 200 Hz。

若要重新评估：
- 使用隔离测试
- 不写回 Stage5D
- 第一次 device-lost 即停止
- 保持当前稳定 baseline

## 14. Small Point-LIO：下一优先级

最新重点：
https://github.com/Yancey2023/small_point_lio.git

优先于继续硬接 PolarBear Point-LIO 做对比试验。

重点理由：
- ROS2
- 高性能 Point-LIO 实现
- 支持 livox_pointcloud2
- 当前 Isaac 已有 PointCloud2
- Mid360 外参与当前推导一致
- 作者声称 2~3x 性能提升，但必须本机 benchmark，不能直接当事实结论

必须解决的冲突：
Small Point-LIO 可能默认发布：
/Odometry
/cloud_registered
并广播 odom → base_link

我们的设计必须保持：
/sentry/odom = Isaac Ground Truth
/sentry/lio/odom = LIO estimator

/sentry/lio/cloud_registered = registered cloud

必须关闭/隔离 Small Point-LIO 的 odom → base_link TF，防止重复 parent/TF冲突。

## 15. 新高性能电脑优先工作流

STEP 1：硬件/环境审计
- GPU
- driver
- VRAM
- CPU
- RAM
- Isaac Sim version
- ROS Jazzy
- RMW
- filesystem paths

STEP 2：原始 baseline 回归
- Stage5C SHA
- Stage5D 4/4
- D/F/G/H/I/I2
- GUI preflight

STEP 3：GUI 性能 benchmark
分别测：
A. GUI no sensors/debug
B. GUI sensors
C. GUI --diagnostic / debug draw
D. RViz optional

记录：
- wall elapsed
- simulation elapsed
- RTF
- GPU utilization
- VRAM
- CPU
- LiDAR simulation rate
- IMU unique simulation rate
- /cmd_vel → safe latency

STEP 4：修复 GUI 体验
- 自动 safe enable / estop false
- teleop nonlocal bug
- timeout 0.6 baseline
- 不先改 physics

STEP 5：Small Point-LIO integration experiment
- 独立 third_party
- source audit
- Jazzy build
- adapter selection
- topic remap
- TF disable
- GT vs LIO
- straight/lateral/rotate/combined
- CPU/RTF benchmark

STEP 6：
Small Point-LIO vs PolarBear Point-LIO
做数据对比后选 baseline。

不要现在进入 terrain/Nav2/RL。
