# 如何得到“真正的当前完整工程 ZIP”

重要说明：

ChatGPT 当前能访问的是你上传到会话的文件、阶段日志和历史附件，
不能直接读取你 Ubuntu 电脑上：
/home/xkddyl/RoboMaster/Sentinel/SentinelWorkspace/workspace
的当前实时全部文件。

所以这个交接 ZIP 是“完整上下文/提示词/日志交接包”，
不是当前电脑实时仓库的完整镜像。

要把当前真正的工程也打成 ZIP：

1. 把本包中的 make_real_full_project_zip.sh 放到旧电脑。
2. 执行：

chmod +x make_real_full_project_zip.sh
./make_real_full_project_zip.sh

会生成：

~/Sentinel_FULL_SOURCE_YYYYMMDD_HHMMSS.zip
~/Sentinel_FULL_SOURCE_YYYYMMDD_HHMMSS.zip.sha256

它包含：
- SentinelWorkspace/workspace 源码
- ROS2 src
- third_party 源码
- isaac_sim 集成
- sentinelusd/Sentry_IsaacSim_Linux 当前工程/Stage outputs
- Git 工作区内容（如果目录内存在 .git，会保留）
- machine report

默认排除：
- ros2_ws/build
- ros2_ws/install
- ros2_ws/log
- logs
- pycache

这些是机器相关、可重建内容，不应迁移。

新电脑上建议重新 colcon build。
