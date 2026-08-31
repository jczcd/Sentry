# ROS 第三方依赖目录

此目录由 `tools/dependencies/fetch.sh ros` 创建并填充。当前固定依赖：

- `point_lio`：SMBU PolarBear 的 RM2025 哨兵分支；
- `livox_ros_driver2`：Livox ROS 2 驱动；
- `Livox-SDK2`：Livox C++ SDK，作为 sibling CMake 依赖。

完整 URL、commit 和补丁见仓库根目录的 `VERSIONS.lock.yaml`。不要直接把完整第三方
工作树提交到本仓库。
