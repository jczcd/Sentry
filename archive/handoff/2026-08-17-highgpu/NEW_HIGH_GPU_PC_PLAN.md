# NEW HIGH GPU PC PLAN

这台电脑显卡配置较高，因此迁移后不要继承旧机器性能结论。

## 必测
- GPU 型号/VRAM/驱动
- CPU/RAM
- Isaac Sim 版本
- RTF
- GPU utilization
- VRAM usage
- CPU utilization
- RTX LiDAR cadence
- IMU unique cadence
- command latency

## 性能 profile
1. 无 diagnostic debug draw
2. sensors only
3. diagnostic + RTX debug draw
4. 可选 RViz

## 重要
GPU强不代表 Point-LIO 一定更快：
Small Point-LIO 很大一部分性能依赖 CPU、内存与算法实现。

也不要因为新 GPU 强就直接把全局 PhysX 改成200Hz。
之前 200Hz 全局 PhysX + RTX 曾触发 device-lost。
若新机要重测，应做隔离实验，不破坏 Stage5D baseline。
