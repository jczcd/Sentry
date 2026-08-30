# Sentinel / Isaac Sim 5090 换机迁移工具包

这是一套“在原 Ubuntu 设备上生成正式工程归档”的工具，不包含旧工程快照。

它会迁移两套彼此独立的工程：

- 主软件仓库：`~/RoboMaster/Sentinel/SentinelWorkspace/workspace`
- USD 工程：`~/RoboMaster/Sentinel/sentinelusd/Sentry_IsaacSim_Linux`

它不会复制：

- `~/issac-sim/isaac-sim` Isaac Sim 安装本体
- `ros2_ws/build`、`ros2_ws/install`、`ros2_ws/log`
- `firmware/vendor`
- Python、IDE、测试和运行缓存

主仓库和 USD 工程会在归档中保持分离；canonical USD 不会被复制到 ROS workspace。

## 1. 在原设备打包

将本工具包解压后执行：

```bash
cd sentinel_5090_migration_kit
chmod +x pack_sentinel_5090.sh restore_sentinel_5090.sh verify_sentinel_archive.sh
./pack_sentinel_5090.sh
```

默认输出目录：

```text
~/SentinelTransfer
```

会生成：

```text
Sentinel_IsaacSim_Stage5D_日期时间.tar.gz
Sentinel_IsaacSim_Stage5D_日期时间.tar.gz.sha256
Sentinel_IsaacSim_Stage5D_日期时间.tar.gz.contents.txt
```

打包前脚本会强制校验受保护的 Stage5C：

```text
ffa8ecbf83a047f05cc1e4aeb3005b1fa8c09da651c273bb4a4d03a62a0dcacc
```

若 Stage5C 不存在或哈希不一致，打包会中止。Stage5D 和
`stage5d_runtime_report.json` 缺失也会中止，避免迁移不完整版本。

若原设备路径不同，可只对本次命令覆盖路径：

```bash
SENTRY_WORKSPACE_ROOT=/实际路径/workspace \
SENTRY_USD_PROJECT_ROOT=/实际路径/Sentry_IsaacSim_Linux \
SENTRY_BUNDLE_OUTPUT_DIR=/实际输出目录 \
./pack_sentinel_5090.sh
```

## 2. 传到 RTX 5090 新设备

至少复制以下三个文件：

- `.tar.gz`
- `.tar.gz.sha256`
- 本工具包中的 `restore_sentinel_5090.sh`

可先验证归档：

```bash
./verify_sentinel_archive.sh /路径/Sentinel_IsaacSim_Stage5D_日期时间.tar.gz
```

再恢复：

```bash
./restore_sentinel_5090.sh /路径/Sentinel_IsaacSim_Stage5D_日期时间.tar.gz
```

默认恢复到：

```text
~/RoboMaster/Sentinel/SentinelWorkspace/workspace
~/RoboMaster/Sentinel/sentinelusd/Sentry_IsaacSim_Linux
```

脚本不会覆盖已有的上述两个目录；如果目录已经存在，会直接停止。

## 3. 新设备环境

Isaac Sim 6.0.1 应在新设备单独安装，默认仍使用项目既定拼写：

```text
~/issac-sim/isaac-sim
```

不要从旧设备复制 Isaac Sim 安装目录、RTX shader cache、Kit cache 或 NVIDIA
缓存。新设备应重新安装适配 RTX 5090 的 NVIDIA 驱动和 Isaac Sim 6.0.1。

恢复脚本会生成：

```text
~/RoboMaster/Sentinel/migration_5090.env
```

使用：

```bash
source ~/RoboMaster/Sentinel/migration_5090.env
cd "$SENTRY_WORKSPACE"
source tools/integration/sentinel_env.sh
./tools/ubuntu/doctor.sh
```

先查看 doctor 结果，再由用户本人安装缺少的系统依赖。不要自动绕过 sudo。
随后重新构建 `ros2_ws`；旧设备的 `build/install/log` 不应复用。

GUI 基线启动：

```bash
cd "$SENTRY_WORKSPACE"
./tools/integration/run_sentinel_gui.sh
```

确认正常后再测试：

```bash
./tools/integration/run_sentinel_gui.sh --diagnostic
```

RTX 5090 可能提高 RTX LiDAR 和 GUI 的实时倍率，但迁移后仍保持当前物理配置。
不要因为更换显卡就直接恢复已经导致 device-lost 的 200 Hz PhysX 方案。

## 4. 迁移保护规则

- 不修改、不覆盖 Stage5C。
- 不执行 `git reset`、`git restore`、`git clean`、`git checkout --`、
  `git stash`、`git commit` 或 `git push`。
- 打包时会记录 Git HEAD、branch、dirty 状态和 submodule 状态，但不会改变仓库。
- 不在 `~/RoboMaster/Sentinel` 父目录初始化 Git，也不会删除该目录中已有的
  `.git`。
- Small Point-LIO / PolarBear Point-LIO 的运行状态会原样迁移，不会被工具包宣称为
  PASS。
