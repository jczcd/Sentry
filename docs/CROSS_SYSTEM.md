# Windows / Ubuntu 跨系统通信

## 推荐方式

Windows 用于编辑；Ubuntu 原生运行 Isaac Sim、Nav2、策略和硬件桥。需要 Windows
端查看话题时，再安装原生 ROS 2 并编译相同的 `sentinel_interfaces`。

两端必须一致：

- `ROS_DOMAIN_ID=0`（或两端共同约定的同一非零值）
- `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`
- `ROS_LOCALHOST_ONLY=0`
- `FASTRTPS_DEFAULT_PROFILES_FILE=<workspace>/config/fastdds.xml`
- 自定义消息定义完全一致
- 系统时间尽量通过 NTP 同步

## 局域网组播

先互相 `ping`，再临时关闭第三方虚拟网卡/VPN，允许 UDP 7400–7600。两端分别运行：

```bash
ros2 multicast receive
ros2 multicast send
```

若互相收不到，说明网络屏蔽 DDS 组播，不是节点代码问题。

## Discovery Server

在 Ubuntu 安装 Fast DDS 工具后启动：

```bash
fastdds discovery --server-id 0 --ip-address 0.0.0.0 --port 11811
```

两端设置 Ubuntu 的实际地址：

```text
ROS_DISCOVERY_SERVER=192.168.1.20:11811
```

然后重新启动所有 ROS 进程。防火墙放行 UDP 11811。

本工程使用 tf2 约定的全局 TF 总线：`/tf` 与 `/tf_static`。不要把它们重映射到
`/sentry/tf`，否则 Nav2、RViz 和定位节点会看到不同的 TF 树。

## WSL2

WSL2 默认 NAT 会让 DDS 发现、组播和 GPU GUI 链路更复杂。可以用它跑静态检查与
编译，但本工程不把“WSL2 + Windows Isaac Sim + Linux ROS 2”作为首选闭环。若必须
跨 NAT，优先使用 Discovery Server 或本工程的 UDP 硬件协议，不要同时混用多个 RMW。

## 远程跨公网

DDS 不应直接裸露到公网。使用 WireGuard/Tailscale 等受控 VPN 后再运行 Discovery
Server，并限制允许的节点与端口。比赛网络中不要开启不必要的远程入口。
