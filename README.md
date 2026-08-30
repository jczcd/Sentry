# Sentry

> 汽大27哨兵工作车间，只为守护最好的汽车大学，前进。

RMUL 2026 四舵轮哨兵的项目总纲、仿真恢复工具、Sim-to-Real 接口约定和可复用 C++ 运动学核心。

> 当前不是“已经恢复完成的整车工程”。截至 2026-08-30，可验证的最新模型状态是 `MANUAL_VISUAL_APPROVAL_REQUIRED`：V2 因视觉装配错位已失效；V3 的 HOOPS Variant A（`globalXforms=false`）是推荐候选，但必须先由人工在 Isaac Sim 中确认外观。历史 Stage5D 4/4 PASS 仅作历史记录，不能作为当前 Gate 证据。

## 当前可用内容

- [项目总框架](HARNESS_RMUL_SENTRY_MASTER_FRAMEWORK.md)：阶段、边界、三人分工和 Gate。
- [项目真实状态](PROJECT_STATE.md)：有效结论、失效结论、哈希和当前阻塞项。
- [完整控制流](docs/architecture/CONTROL_FLOW.md)：MCP/规划/安全/仿真/实车/STM32 的唯一控制权边界。
- `sentinel_common/`：不依赖 ROS、Isaac、HAL 或 FreeRTOS 的 C++17 四舵轮 IK/FK 核心。
- `tools/isaac/`：CAD 导入与历史 Stage5D 构建/测试工具。
- `tools/migration/`：4090、5090 主机迁移、校验和恢复脚本。
- `archive/`：旧机器交接和恢复资料，只作取证，不代表当前通过状态。

## 当前控制主链

```text
MCP / 操作员 / 导航 / RL
          -> /cmd_vel
          -> safety_supervisor
          -> /sentry/cmd_vel_safe
          -> 仿真后端 或 实车硬件桥
          -> 四舵轮控制器
          -> 执行器
```

`/sentry/cmd_vel_safe` 是唯一的上层安全边界。MCP 默认只用于诊断；没有人工使能时，不得发布运动命令，更不能绕过安全节点直达关节、电机或 CAN。

## 编译公共运动学核心

```bash
cmake -S . -B build -DSENTRY_BUILD_TESTS=ON
cmake --build build
ctest --test-dir build --output-on-failure
```

同一组 `sentinel_common` 源码可分别由桌面编译器和 `arm-none-eabi-g++` 编译。实车仍需另外实现 CAN、IMU、串口/USB、定时任务、功率限制和故障保护。

## 从哪里继续

1. 阅读 [AGENTS.md](AGENTS.md)、[PROJECT_STATE.md](PROJECT_STATE.md) 和主框架。
2. 完成 V3 Variant A 的人工视觉确认；未确认前禁止恢复关节、PhysX 或训练。
3. 测量并冻结四个舵轮坐标、轮径、减速比、编码器方向与零位。
4. 运行 `sentinel_common` 单元测试，再接入虚拟下位机。
5. 仅在当前 Gate 通过后进入 Mid-360、Small Point-LIO、Nav2 或 RL。

VS Code 与 ROS MCP 的接入见 [VS Code MCP 设置](docs/development/VSCODE_MCP_SETUP.md)。

![Isaac Sim 中的历史哨兵模型画面](docs/assets/isaac-sim-stage5d.png)

## 大文件策略

STEP、USD 二进制、Isaac 安装包、ROS 构建产物、rosbag 和迁移压缩包不进入普通 Git 历史。已知源文件及校验值记录在 [资产清单](docs/history/ARTIFACT_MANIFEST.md)；需要长期托管时应使用 Git LFS 或 Release，并再次核对许可和仓库配额。
