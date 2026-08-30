# ROS interface contract

The machine-readable draft is `config/interfaces/ros_topics.yaml`.

## Command topics

| Topic | Type | Publisher | Subscriber |
|---|---|---|---|
| `/cmd_vel` | `geometry_msgs/msg/Twist` | active teleop, navigation, or policy source via arbitration | `safety_supervisor` |
| `/sentry/cmd_vel_safe` | `geometry_msgs/msg/Twist` | `safety_supervisor` only | selected simulator or hardware backend |
| `/sentry/estop` | `std_msgs/msg/Bool` | authorized safety/operator path | safety supervisor and backend |

If multiple sources can produce `/cmd_vel`, use a mux/arbiter with explicit priority and timeouts. Do not rely on last-writer-wins DDS behavior.

## State topics

| Topic | Type | Intended meaning |
|---|---|---|
| `/clock` | `rosgraph_msgs/msg/Clock` | simulation time only |
| `/joint_states` | `sensor_msgs/msg/JointState` | all movable robot joints with coherent timestamp |
| `/sentry/odom` | `nav_msgs/msg/Odometry` | Isaac ground truth in simulation; chosen real odometry source on hardware |
| `/sentry/lio/odom` | `nav_msgs/msg/Odometry` | LIO estimate kept separate from Isaac truth |
| `/sentry/lidar/points` | `sensor_msgs/msg/PointCloud2` | Mid-360-compatible point cloud |
| `/sentry/imu` | `sensor_msgs/msg/Imu` | calibrated IMU data |
| `/sentry/scan` | `sensor_msgs/msg/LaserScan` | optional 2D diagnostic projection |

The point-cloud baseline fields are `x`, `y`, `z`, `intensity`, and per-point `time` in seconds. Verify the actual driver schema before configuring Point-LIO.

## Time rules

- Simulation nodes use `/clock` and `use_sim_time=true`.
- Real nodes use `use_sim_time=false`.
- The hardware bridge timestamps receipt with the host monotonic clock and preserves the MCU sequence/timestamp in telemetry.
- Do not compare unrelated wall, ROS, and MCU clocks without an explicit mapping.

## Initial QoS guidance

- sensor topics: sensor-data QoS unless a consumer requires otherwise;
- command topics: small depth, reliable where the measured latency remains acceptable;
- `/tf_static`: transient local;
- diagnostics: reliable with bounded history.

QoS is part of integration evidence. Confirm compatibility with `ros2 topic info --verbose` rather than assuming a topic name proves communication.
