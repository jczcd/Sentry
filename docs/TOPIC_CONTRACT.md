# 哨兵 ROS 2 话题契约

本文件定义跨仿真、HIL 和实车的公共接口。表中名称是最终解析后的绝对名称；节点可以
运行在 `/sentry` namespace 下，但不得因此改变全局安全入口、时钟或 TF 总线。

## 控制与安全

| 话题 | 类型 | 主要发布者 | 用途 |
|---|---|---|---|
| `/cmd_vel` | `geometry_msgs/msg/Twist` | Nav2/策略仲裁器/Mock | 底盘原始速度入口 |
| `/cmd_vel_teleop` | `geometry_msgs/msg/Twist` | 遥控适配器 | 遥控优先入口，仍必须过安全层 |
| `/sentry/cmd_vel_nav` | `geometry_msgs/msg/Twist` | Nav2 controller | Nav2 原始输出，需被仲裁到 `/cmd_vel` |
| `/sentry/cmd_vel_safe` | `geometry_msgs/msg/Twist` | `safety_supervisor` 唯一 | 仿真或实车唯一执行速度 |
| `/sentry/estop` | `std_msgs/msg/Bool` | `mode_manager`/授权操作员 | 急停锁存；`true` 表示禁止运动 |
| `/sentry/system_mode` | `std_msgs/msg/UInt8` | `mode_manager` | `sim=0`、`hil=1`、`real=2` |
| `/sentry/system_status` | `sentinel_interfaces/msg/SystemStatus` | `safety_supervisor` | 看门狗、模式和互锁状态 |

安全监督必须执行急停、速度/加速度限幅、命令超时和 HIL/实车硬件心跳检查。MCP、调试
键盘、自瞄和固件上位机均不得直接发布 `/sentry/cmd_vel_safe`、电机电流、PWM 或 CAN
帧。

## 战术与交战

| 话题 | 类型 | 发布者 | 说明 |
|---|---|---|---|
| `/sentry/battle_state` | `sentinel_interfaces/msg/BattleState` | 裁判/融合适配器 | 策略输入 |
| `/sentry/policy/observation` | `sentinel_interfaces/msg/PolicyObservation` | observation node | 固定 161 维 |
| `/sentry/policy/command` | `sentinel_interfaces/msg/TacticalCommand` | policy node | 子目标、目标槽位和交战请求 |
| `/sentry/target_request` | `std_msgs/msg/Int8` | tactical executor | 未裁决的目标槽位 |
| `/sentry/weapons_free_request` | `std_msgs/msg/Bool` | tactical executor | 未裁决的交战请求 |
| `/sentry/target_safe` | `std_msgs/msg/Int8` | `safety_supervisor` 唯一 | `-1` 表示无目标 |
| `/sentry/weapons_free_safe` | `std_msgs/msg/Bool` | `safety_supervisor` 唯一 | 固件仍需再次复核 |

目标槽位必须在 `0–5` 范围内；目标、交战请求、裁判许可、热量和弹量任一过期或非法时，
安全层输出 `false/-1`。

## 状态与传感器

| 话题 | 类型 | 约定 |
|---|---|---|
| `/clock` | `rosgraph_msgs/msg/Clock` | 仿真全局时钟；实车不发布 |
| `/sentry/odom` | `nav_msgs/msg/Odometry` | 选定的仿真或状态估计输出 |
| `/sentry/lio/odom` | `nav_msgs/msg/Odometry` | Point-LIO 输出，接入前必须验收 |
| `/joint_states` | `sensor_msgs/msg/JointState` | 仿真关节或实车编码器 |
| `/sentry/lidar/points` | `sensor_msgs/msg/PointCloud2` | `lidar_link`，字段至少 `x,y,z,intensity,time`，时间单位秒 |
| `/sentry/scan` | `sensor_msgs/msg/LaserScan` | 2D 投影/调试输入，可选 |
| `/sentry/imu` | `sensor_msgs/msg/Imu` | `imu_link`，仿真和实车保持同一语义 |
| `/sentry/hardware_state` | `sentinel_interfaces/msg/HardwareState` | 硬件在线、热量、弹量和链路状态 |

## TF 所有权

TF 使用 tf2 标准全局话题 `/tf` 与 `/tf_static`，禁止创建 `/sentry/tf` 作为第二套树。

```text
map -> odom -> base_link -> lidar_link
                         -> imu_link
                         -> camera_optical_frame
                         -> gimbal_yaw_link -> gimbal_pitch_link -> barrel_link
```

- `map -> odom`：定位/重定位节点唯一发布；
- `odom -> base_link`：仿真或状态估计二选一；
- `base_link -> robot links`：`robot_state_publisher`；
- `lidar_link -> imu_link`：Mid-360 内部固定外参；
- `/tf_static` 使用 transient-local QoS，不能被动态节点重复发布。

## 后端互斥

```text
/cmd_vel 或 /cmd_vel_teleop
        ↓
safety_supervisor
        ↓
/sentry/cmd_vel_safe
        ├── VirtualLowerController → Isaac Sim
        └── hardware_bridge → USB CDC/UDP → STM32
```

运行模式中只能启用一个运动后端和一个 `odom -> base_link` 所有者。完整机器可读版本见
[`config/interfaces/ros_topics.yaml`](../config/interfaces/ros_topics.yaml)。
