# 训练层

本目录把两类训练分开：

1. `RMUC-OfflineRL/`：固定到提交
   `f0d54521caa5b5701665b97f87df309ab2ed8f87` 的离线战术学习上游快照。
2. `isaac_lab/`：Isaac Lab 在线仿真训练的接口契约和任务迁移骨架。

离线策略的默认部署接口是 161 维观测、10 维战术动作。Isaac Lab 任务也必须保持这
两个维度，才能复用 ROS 2 的 `PolicyObservation` / `TacticalCommand` 边界。

## ROS 2 总调度

在工作空间根目录启动任务管理器：

```bash
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
ros2 launch sentinel_bringup training.launch.py workspace_root:="$PWD"
```

启动一个允许列表中的训练配置：

```bash
ros2 service call /sentry/training/start \
  sentinel_interfaces/srv/StartTraining \
  "{config_path: training/jobs/offline_infantry_iql.yaml, run_name: iql_try_01}"
```

查看状态或停止：

```bash
ros2 topic echo /sentry/training/status
ros2 service call /sentry/training/stop \
  sentinel_interfaces/srv/StopTraining "{force: false}"
```

管理器不执行 shell 字符串，只调用预配置的 `training/run_job.py`，配置也必须位于
`training/jobs/` 内。这样 ROS 2 能调度作业，但不能被远端请求变成任意命令执行器。

## 建议顺序

1. 用官方 SQLite 数据构建 `data/infantry_tactical`。
2. 训练并保留验证集最优的 `best.pt`，不要默认用 `final.pt`。
3. 用 mock 与 rosbag 回放验证输出稳定性。
4. 在 Isaac Lab 中做随机化/碰撞/约束验证，不把 DDS 放入并行物理内环。
5. 导出策略到 `artifacts/policies/<run_name>`，在 HIL 中限制速度且禁用发射。
6. 最后才在实车上释放急停和开火门控。

离线数据集和训练的具体命令以 `RMUC-OfflineRL/README.md` 为准。
