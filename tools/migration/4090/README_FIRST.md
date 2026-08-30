# Sentinel / Isaac Sim 4090 迁移工具包

更新时间：2026-08-18

## 先说明这个 ZIP 是什么

本 ZIP 是“完整工程打包、校验、恢复和续接工具包”。它本身不可能包含旧电脑此刻的实时工程内容，因为旧工程仍在旧电脑：

```text
/home/xkddyl/RoboMaster/Sentinel/SentinelWorkspace/workspace
/home/xkddyl/RoboMaster/Sentinel/sentinelusd/Sentry_IsaacSim_Linux
```

需要先在旧电脑运行本包中的 `pack_sentinel_full.sh`。脚本会生成真正包含当前源码、Git 工作区、ROS 2 源码、Isaac 集成、USD 工程和 Stage5C/Stage5D 的正式归档。

正式工程归档使用 `tar.gz`，而不是 ZIP，因为 Linux 工程中的可执行权限和符号链接需要可靠保留。

不会把 Isaac Sim 安装本体打入归档。4090 云机已经能够打开 Isaac Sim，安装本体应留在新机器。

## 一、在旧工程电脑生成正式归档

解压本工具包，然后执行：

```bash
cd Sentinel_Migration_4090_20260818
chmod +x ./*.sh
./pack_sentinel_full.sh
```

默认读取：

```text
$HOME/RoboMaster/Sentinel/SentinelWorkspace/workspace
$HOME/RoboMaster/Sentinel/sentinelusd/Sentry_IsaacSim_Linux
```

如果旧电脑当前用户不是 `xkddyl`，但工程仍位于原绝对路径，可执行：

```bash
SENTRY_WORKSPACE_ROOT=/home/xkddyl/RoboMaster/Sentinel/SentinelWorkspace/workspace \
SENTRY_USD_PROJECT_ROOT=/home/xkddyl/RoboMaster/Sentinel/sentinelusd/Sentry_IsaacSim_Linux \
./pack_sentinel_full.sh
```

默认输出到：

```text
$HOME/SentinelTransfer/
```

生成三个文件：

```text
Sentinel_IsaacSim_Stage5D_FULL_时间.tar.gz
Sentinel_IsaacSim_Stage5D_FULL_时间.tar.gz.sha256
Sentinel_IsaacSim_Stage5D_FULL_时间.tar.gz.contents.txt
```

打包脚本只读取工程，不修改代码、不清理 Git，也不会覆盖 Stage5C。它会先强制验证：

```text
Sentry_stage5c_joint_drives.usda
SHA256 = ffa8ecbf83a047f05cc1e4aeb3005b1fa8c09da651c273bb4a4d03a62a0dcacc
```

同时要求 Stage5D 和 Stage5D 运行报告存在，防止迁移半成品。

## 二、传到4090云机

可以用 SFTP、scp 或 NoMachine 文件传输。使用 scp 的通用形式：

```bash
scp ~/SentinelTransfer/Sentinel_IsaacSim_Stage5D_FULL_*.tar.gz* \
  gelinhe@服务器IP:/home/gelinhe/
```

不要把服务器密码写进命令、脚本或聊天记录。

## 三、在4090云机验证并恢复

把本工具包也放到云机，执行：

```bash
cd Sentinel_Migration_4090_20260818
chmod +x ./*.sh

./verify_sentinel_archive.sh \
  "$HOME/Sentinel_IsaacSim_Stage5D_FULL_时间.tar.gz"

./restore_sentinel_full.sh \
  "$HOME/Sentinel_IsaacSim_Stage5D_FULL_时间.tar.gz" \
  "$HOME/robomaster/space/Sentinel_work"
```

恢复脚本不会覆盖已有的工作区或 USD 工程。目标目录已存在时会停止，避免误覆盖。

恢复后的主要路径：

```text
$HOME/robomaster/space/Sentinel_work/SentinelWorkspace/workspace
$HOME/robomaster/space/Sentinel_work/sentinelusd/Sentry_IsaacSim_Linux
$HOME/robomaster/space/Sentinel_work/migration_4090.env
```

检查4090云机：

```bash
./check_4090_host.sh "$HOME/robomaster/space/Sentinel_work" \
  | tee "$HOME/sentinel_4090_host_report.txt"
```

## 四、Ubuntu 22.04 与 ROS 2 Jazzy 注意事项

当前云机是 Ubuntu 22.04，而原工程基线是 Ubuntu 24.04 + ROS 2 Jazzy。

Isaac Sim 6.0 文档将 Ubuntu 24.04 + Jazzy 作为推荐组合。Ubuntu 22.04 可以使用 Jazzy，但需要按 NVIDIA 的“Other Platforms”流程从源码或 Docker 构建相应工作区，不能直接假设 `/opt/ros/jazzy` 已存在：

- https://docs.isaacsim.omniverse.nvidia.com/6.0.1/ros2_tutorials/ros2_landing_page.html
- https://docs.isaacsim.omniverse.nvidia.com/6.0.1/installation/install_ros_other_platforms.html

不要现在重装云机。云机原有 CARLA、Autoware 等数据较多，必须先完成备份和迁移评估。优先方案是在 Ubuntu 22.04 主机运行 Isaac Sim，外部 Jazzy 节点使用 Docker/专用工作区；确认通信链后再决定是否换 Ubuntu 24.04。

## 五、用 Codex 续接

Codex 官方建议从项目目录启动。恢复后执行：

```bash
source "$HOME/robomaster/space/Sentinel_work/migration_4090.env"
cd "$SENTRY_WORKSPACE"

if [ ! -e AGENTS.md ]; then
  cp "$SENTINEL_ROOT/migration_metadata/handoff/AGENTS_SENTINEL_4090.md" AGENTS.md
fi

codex
```

进入 Codex 后，将下面文件内容作为第一条指令：

```text
$SENTINEL_ROOT/migration_metadata/handoff/CODEX_FIRST_PROMPT.txt
```

Codex CLI 官方说明：

- https://learn.chatgpt.com/docs/codex/cli
- https://learn.chatgpt.com/docs/agent-configuration/agents-md

第一轮只做只读检查和报告，不立刻改代码。

## 六、4090云机的实际工作顺序

1. 确认打开的是 Isaac Sim 6.0.1，而不是6.0.0。
2. 恢复真实完整工程，并验证 Stage5C 哈希。
3. 先确认 Stage5D 正常打开，不修改物理参数。
4. 比较普通 GUI 与 `--diagnostic` 的 RTF、GPU、CPU和传感器负载。
5. 测量 `/cmd_vel` 到 `/sentry/cmd_vel_safe` 的延迟和 teleop 手感。
6. 基线确认后，才实现安全的仿真 estop 自动解除流程。
7. 优先接入 Small Point-LIO 的 `livox_pointcloud2` adapter。
8. 保留 `/sentry/odom` 作为 Isaac 真值，LIO 输出改为 `/sentry/lio/odom`，禁止重复发布 `odom -> base_link`。
9. 暂不进入 terrain、Nav2 或 tactical RL。
10. 不再尝试整场 `set_physics_dt(1/200)`。

详细步骤见 `NEXT_STEPS_4090.md`。
