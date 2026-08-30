# CURRENT TASK

现在先做两件事：

## 1. GUI 体验
已知：
- GUI 可以打开
- 机器人可以运动
- 初次不动是 estop 未解除
- 人工反馈：响应有点慢

下一步不要调底盘参数，先测：
- RTF
- /cmd_vel → /sentry/cmd_vel_safe latency
- odom response
- diagnostic/debug draw 对性能影响

新电脑 GPU 很强，必须重新实测。

## 2. Small Point-LIO
优先研究：
https://github.com/Yancey2023/small_point_lio.git

目标：
- 优先 livox_pointcloud2 adapter
- /sentry/lidar/points
- /sentry/imu
- /sentry/lio/odom
- /sentry/lio/cloud_registered
- 禁止 TF 冲突
- 对比 Isaac GT
