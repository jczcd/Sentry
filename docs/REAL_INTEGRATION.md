# 实车集成门禁

按以下顺序逐级放行，上一项没有记录证据就不要进入下一项：

1. **协议台架**：MCU 不接电机，Python/C 固定向量一致，CRC 错帧会丢弃。
2. **轮子悬空**：急停默认开启；只验证 X/Y 方向、单位、看门狗和零速。
3. **低速落地**：限速 0.2 m/s，发射位在 MCU 编译期禁用。
4. **里程计/TF**：直行、横移、原地受力后坐标方向正确；无重复 TF 发布者。
5. **雷达/Nav2**：静态地图定位稳定，局部障碍会停，规划输出只进入 `cmd_vel`。
6. **HIL 策略**：记录所有 161 维输入和 10 维输出，异常/NaN 一律安全空闲。
7. **自瞄门控**：目标、热量、弹量、裁判许可四项同时满足才允许发射。
8. **实车策略**：先 mock/BC，再最优检查点；每次只提高一个速度或权限上限。

建议记录一个 `ros2 bag` 验收包，至少包含：

```text
/sentry/battle_state
/sentry/policy/observation
/sentry/policy/command
/cmd_vel
/sentry/cmd_vel_safe
/sentry/hardware_state
/sentry/system_status
/sentry/odom
/sentry/scan
/tf
/tf_static
```

真实 URDF 的质量、惯量、轮距、碰撞外形和传感器外参必须来自测量，不从图片或旧 USD
猜测。默认 URDF 只是接口模型。
