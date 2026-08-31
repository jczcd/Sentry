# 固件层

- `protocol/`：本工程真正使用、Python/C 互测的无动态内存协议。
- `vendor/dp_sdk_core/`：KaminDeng/dp_sdk_core 固定提交快照，用作 OSAL/HAL/Device
  架构参考，不直接链接到 ROS 2 节点。

建议把协议层复制或作为子模块加入 STM32 工程；不要把整个 ROS 工作空间塞进 MCU
仓库。USB CDC 面向 NUC，UART6 保留 VOFA，底盘和云台控制周期仍由 MCU 定时器决定。
