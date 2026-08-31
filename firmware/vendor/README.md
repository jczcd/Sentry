# 固件第三方依赖目录

`tools/dependencies/fetch.sh firmware` 会在这里按固定 commit 获取 `dp_sdk_core`。
该目录只用于编译参考和适配，不替代 Sentinel 自己的 USB CDC、UART6、CAN 和安全
控制实现。
