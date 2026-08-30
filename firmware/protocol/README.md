# STM32 / NUC 线协议

Python 与 C 实现使用同一帧：

```text
magic:u16  version:u8  type:u8  payload_len:u16  seq:u16  timestamp_ms:u32
payload[0..256]  crc16_ccitt:u16
```

- 全部字段小端。
- `magic = 0x534E`，版本 1。
- CRC 是 CCITT-FALSE 多项式 `0x1021`，初值 `0xFFFF`，覆盖头和 payload。
- 指令 payload：`vx/vy(mm/s), wz(mrad/s), target(int8), weapons, estop, reserved`。
- 遥测 payload：位姿、速度、热量/上限、剩余弹量、电池 mV、故障位。

## 固件接入

把 `sentinel_wire_protocol.c/.h` 加入 STM32 工程。USB CDC 是 NUC 主链路，UART6
继续用于 VOFA 调试，不要混用。USB 收到每个字节时调用：

```c
sentinel_frame_t frame;
if (sentinel_parser_push(&parser, rx_byte, &frame)) {
    sentinel_command_t command;
    if (sentinel_decode_command(&frame, &command)) {
        /* 先检查 command.estop、超时和本地机械/裁判安全条件。 */
    }
}
```

必须在 MCU 本地再做一次 200 ms 指令看门狗；ROS 2 失联时底盘清零、发射禁止、目标
置为 `-1`。任何网络/NUC 命令都不能绕过 MCU 的热量、弹量、裁判状态和物理急停。

`firmware/vendor/dp_sdk_core` 是固定版本的上游参考。可以借鉴其 OSAL/HAL/Device
分层，把 USB CDC、时间源和执行器封装为端口；本协议本身保持 C11、无动态内存，
不会强制你的 STM32 工程依赖该 SDK。
