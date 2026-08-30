# 可复现依赖

主仓库只保存一方源码和接口。Point-LIO、Livox 驱动、RMUC-OfflineRL 和 dp_sdk_core
按 [`../VERSIONS.lock.yaml`](../VERSIONS.lock.yaml) 的固定 commit 获取，下载目录被
`.gitignore` 排除，避免把第三方 Git 历史和本机生成物提交进来。

在 Ubuntu 具备网络和 Git 后执行：

```bash
bash tools/dependencies/fetch.sh ros
bash tools/dependencies/fetch.sh training
bash tools/dependencies/fetch.sh firmware
bash tools/dependencies/fetch.sh all
```

脚本不会覆盖已有目录；如果目录不是预期 commit，会停止并要求人工处理。Livox 驱动
需要仓库中的 sibling-SDK 补丁，脚本会在补丁尚未应用时应用一次，并为 `Livox-SDK2`
写入 `COLCON_IGNORE`，因为它是驱动的 CMake 依赖而不是 ROS 包。

联网失败、上游 commit 变化或补丁冲突时应停在依赖阶段，不得把“源码已导入”误报为
ROS/Nav2/Point-LIO 运行通过。
