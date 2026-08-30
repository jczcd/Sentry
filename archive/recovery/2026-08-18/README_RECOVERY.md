# Sentinel 4090 可恢复资料包

更新时间：2026-08-18

## 这是什么

这是目前能够找回的全部 Sentinel / Isaac Sim 工程资料的合并包，用于只有新电脑、没有原电脑实时工作区时的受控恢复。

它包含：

- 原始 `Sentry.step` CAD 总装及 STEP → USD 转换工具；
- Stage5D 构建和四舵轮运行测试脚本；
- PHASE I～J1、Mid-360、Point-LIO、GUI 等阶段交接和历史日志；
- 4090迁移检查、归档和恢复工具；
- Codex 恢复提示词。

## 重要边界

本包不是原电脑实时工作区的完整镜像。以下关键成品没有被保存进现有附件：

- `Sentry_stage5c_joint_drives.usda`；
- `Sentry_stage5d_swerve.usda`；
- 完整 `SentinelWorkspace/workspace`；
- 完整 ROS 2 `ros2_ws/src`；
- 完整 Isaac integration 脚本树。

因此不能把本包直接称为原 Stage5D baseline，也不能继续宣称 Stage5D 4/4 PASS。历史哈希

```text
ffa8ecbf83a047f05cc1e4aeb3005b1fa8c09da651c273bb4a4d03a62a0dcacc
```

只能证明原 Stage5C 的身份，不能证明后续重建文件与原文件完全相同。

## 目录

```text
01_cad_source/          原始 STEP 和 CAD 转换工具
02_stage5d_builder/     Stage5D overlay、标定和4/4测试工具
03_handoff/             项目交接、历史日志、Mid-360资料
04_migration_toolkit/   迁移、检查、恢复工具
CODEX_RECOVERY_PROMPT.txt
README_RECOVERY.md
MANIFEST.sha256
```

## 新电脑当前已知状态

```text
Ubuntu 22.04.4
RTX 4090 24GB
NVIDIA driver 580.173.02
根分区约500GB，剩余约352GB
Isaac Sim 6.0.0-rc.59
ROS 2 / colcon / CMake / Docker / Codex CLI 未在 PATH 中找到
```

原项目基线是 Ubuntu 24.04 + ROS 2 Jazzy + Isaac Sim 6.0.1。不要删除当前能启动的 Isaac Sim 6.0.0；如果安装6.0.1，应使用独立目录并保留回退能力。

## 恢复顺序

1. 解压本包，不修改 `01_cad_source/source/Sentry.step`。
2. 在项目根目录启动 Codex，并提交 `CODEX_RECOVERY_PROMPT.txt`。
3. 第一轮只读审计 CAD 转换工具、Stage5D builder、交接日志和本机环境。
4. 确认 Isaac Sim 6.0.1 与 Ubuntu 22.04 的运行方案。
5. 转换原始 CAD，得到 `Sentry_raw.usd`、`Sentry.usda` 和 link mapping。
6. 根据交接日志重新建立 articulation、碰撞体和 Stage1～Stage5C；每阶段重新验证。
7. Stage5C 输入、`stage4_report.json` 和 `stage5b_preflight.json` 都重新通过后，才能运行 Stage5D builder。
8. 重新完成 straight、lateral、diagonal、rotate 4/4，才能建立新的恢复 baseline。
9. 再恢复 ROS 2 GUI、传感器、RTF诊断和 Small Point-LIO。

暂不进入 terrain、Nav2或 tactical RL；不要重试整场 `set_physics_dt(1/200)`。

## 解压位置

推荐在新电脑执行：

```bash
cd /home/ubuntu/robomaster/sentel
unzip Sentinel_Recovery_4090_20260818.zip
cd Sentinel_Recovery_4090_20260818
```

然后安装或定位 Codex CLI，在此目录启动：

```bash
codex
```

并粘贴 `CODEX_RECOVERY_PROMPT.txt` 的全部内容。
