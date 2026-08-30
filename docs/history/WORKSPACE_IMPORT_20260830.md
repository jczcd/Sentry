# workspace.zip 导入记录

日期：2026-08-30
来源：`/Robomaster电控/workspace.zip`
SHA256：`118276849edf3fe0920c8d6addfca4eb8b1b73e867a50d17a78a9472519a0cc2`

## 导入原则

本次把原工作区中的一方源码、配置、接口、测试和工具合并进 `jczcd/Sentry`，保留
仓库已有的 Harness、共享运动学、迁移文档和 CI。源工作区内的 `.git` 仅用于追溯，
不作为嵌套 Git 仓库提交。

已导入的主要目录：

- `ros2_ws/src`：五个 ROS 2 包、消息/服务、Mock、导航和启动文件；
- `isaac_sim`：场景加载、状态/传感器适配器与契约；
- `training`：观测/动作契约、任务配置和运行器；
- `firmware/protocol`：C11 线协议；
- `config`、`tests`、`tools/{common,integration,ubuntu,windows}`；
- 原工作区文档和来源说明。

## 明确排除

- `ros2_ws/build`、`install`、`log`、Python `__pycache__` 和运行日志；
- `ros2_ws/src/third_party`、`firmware/vendor`、`training/RMUC-OfflineRL` 的完整工作树；
- Isaac/NVIDIA 缓存、运行输出和未批准 USD/STEP/ZIP。

第三方依赖通过 `dependencies/` 按 `VERSIONS.lock.yaml` 的固定 commit 获取，避免将
上游历史、未审查补丁和本机路径混入主仓库。

## 接口收敛

- 原始底盘输入统一为全局 `/cmd_vel`，遥控输入为 `/cmd_vel_teleop`；
- `/sentry/cmd_vel_safe` 只允许 `safety_supervisor` 发布；
- TF 使用全局 `/tf`、`/tf_static`，时钟使用全局 `/clock`；
- `/sentry/odom`、`/joint_states` 只能由当前模式选定的一个后端发布；
- 详细契约见 `docs/TOPIC_CONTRACT.md` 与 `config/interfaces/ros_topics.yaml`。

## 真实性边界

压缩包内的旧日志和 `PROJECT_STATE.md` 被保存为历史材料，不能证明当前环境仍能复现
旧的 Stage5D/Phase F–J1 PASS。V2 模型视觉结论已撤销；V3 Variant A 仍需人工 GUI
确认，未批准前不允许运动仿真或训练。
