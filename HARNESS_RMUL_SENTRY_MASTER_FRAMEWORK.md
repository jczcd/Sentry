# RMUL 哨兵项目总方案（Harness Engineering 主框架）
**项目名称**：RMUL 2026 哨兵自主导航与对抗系统
**适用对象**：三人开发小队
**硬件约束**：四舵轮底盘 + 单激光雷达 **MID360** + **1 台 NUC** + STM32/C板下位机
**主比赛范围**：**RoboMaster 高校联盟赛 RMUL（仅联盟赛）**
**版本**：v1.0
**用途**：作为后续所有开发、Codex 提示词、任务分解、评审验收、版本管理的**总纲领文件**。若后续需求与本文件冲突，**优先以本文件为准**，除非明确修订版本。

---

# 0. 本文件的作用

本文件不是单纯的“想法汇总”，而是项目的 **Harness Engineering / Prompt-as-Spec** 框架文件。
后续无论是：

- 让 Codex 写代码
- 让 ChatGPT 帮你拆模块
- 团队内部分工
- 每周验收
- 仿真到实车迁移
- RL 方案引入
- Isaac Sim / Isaac Lab 工程设计

都必须在本文件定义的：

1. **目标**
2. **边界**
3. **系统架构**
4. **阶段计划**
5. **接口定义**
6. **验收 Gate**
7. **风险控制**
8. **禁止事项**

之内执行，避免项目越做越散、越来越偏。

---

# 1. 项目总目标

构建一套适用于 **RMUL 哨兵机器人** 的、可比赛、可调试、可扩展的自主运动与决策系统。

核心目标不是“某个算法很先进”，而是：

> **做出一套分层清晰、能稳定上场、能逐步增强到 RL 的完整系统。**

---

# 2. 硬件与比赛约束

## 2.1 固定硬件配置
- **底盘**：四舵轮全向底盘（swerve）
- **激光雷达**：**1 个 MID360**
- **上位机**：**1 台 NUC**
- **下位机**：STM32 / C板 / 等价 MCU
- **云台/自瞄**：后续接入，但不作为第一阶段核心
- **通讯**：NUC ↔ STM32，裁判系统，必要的传感器链路

## 2.2 比赛约束
只考虑 **RMUL 联盟赛**，不直接套用 RMUC 方案。
因此后续设计必须遵守：

- 哨兵自主运行
- 不能依赖不允许的多机通信
- 必须遵守底盘功率、热量、回血/复活、控制区、补给区、禁区等规则
- 战术层不能依赖联盟赛规则不允许的隐含信息

---

# 3. 总体技术路线（一句话版）

> **先做舵轮底盘基础层 → 再做 Isaac 数字孪生 → 再做定位/重定位 → 再做传统导航 baseline → 再做 Safety Guard → 再做 Local RL → 最后做 Tactical RL。**

也就是说：

- **不是纯 Nav2**
- **不是纯 RL**
- **不是先战术后底盘**
- **不是先花很久建花哨仿真场景**

而是：

> **先把“机器人能正确运动”这件最底层的事做扎实。**

---

# 4. 系统总架构

## 4.1 分层架构图

```text
                   ┌────────────────────────┐
                   │   Tactical Layer       │
                   │   BT/FSM baseline      │
                   │   后期 Tactical RL     │
                   └──────────┬─────────────┘
                              │
                        TacticalGoal
                              │
                              ▼
                   ┌────────────────────────┐
                   │ Global / Semantic Layer│
                   │ 语义地图 / 路线管理     │
                   │ Global Planner         │
                   └──────────┬─────────────┘
                              │
                       ReferencePath
                              │
                              ▼
                   ┌────────────────────────┐
                   │ Local Motion Layer     │
                   │ MPPI/MPC baseline      │
                   │ 后期 Residual Local RL │
                   └──────────┬─────────────┘
                              │
                         vx / vy / wz
                              │
                              ▼
                   ┌────────────────────────┐
                   │ Safety Guard           │
                   │ 速度/碰撞/功率/超时    │
                   └──────────┬─────────────┘
                              │
                              ▼
                   ┌────────────────────────┐
                   │ Swerve Chassis Layer   │
                   │ IK / FK / Odom / 模式  │
                   └──────────┬─────────────┘
                              │
                              ▼
                   ┌────────────────────────┐
                   │ STM32 / Motor Control  │
                   │ 转向环 / 驱动环         │
                   └────────────────────────┘
```

## 4.2 感知与定位链路

```text
MID360 + IMU
      │
      ▼
Small Point-LIO
      │
      ▼
odom
      │
      ▼
relocalization (small_gicp / ICP / GICP)
      │
      ▼
map -> odom
      │
      ▼
Global / Local Planner
```

## 4.3 仿真与训练链路

```text
Phase1_TestWorld / RMUL2026.usd
            │
            ▼
        Isaac Sim
            │
            ├── 机器人数字孪生
            ├── 传感器仿真
            ├── Ground Truth
            └── 场景验证
            │
            ▼
        Isaac Lab
            │
            └── Local RL 大规模并行训练
```

---

# 5. 为什么选这条路线

## 5.1 为什么先做舵轮
因为后续所有模块——导航、LIO、RL、战术——最终都要落到：

```text
vx, vy, wz
```

如果这层不稳定，则后面任何高级算法都没有意义。

## 5.2 为什么只用一个 MID360
因为当前硬件约束明确：**单雷达 + 单 NUC**。
因此所有方案必须默认：

- 定位依赖单雷达
- 局部环境理解优先使用单雷达点云
- 不以双雷达、雷达阵列作为系统必要条件

## 5.3 为什么不直接纯 RL
因为纯端到端方案同时把：

- 定位
- 规划
- 避障
- 决策
- 战术
- 动力学

都埋进黑盒里，训练难、调试难、实车风控差。
对三人 RMUL 团队不合适。

## 5.4 为什么不是只做传统 Nav2
因为 RMUL 场地虽小，但动态对抗强，单纯传统局部规划在堵路、抢点、对抗穿行时上限有限。
因此更合理的路线是：

> **传统 baseline 保底，RL 做局部增强。**

---

# 6. 第一阶段：舵轮底盘基础层（当前唯一主任务）

## 6.1 第一阶段目标
完成四舵轮底盘的：

- 正运动学 FK
- 逆运动学 IK
- 原地自转
- 平移
- 平移 + 旋转
- 舵角最短路径优化
- 轮速整体饱和
- 车体 / 世界 / 云台三坐标系变换
- 底盘跟随云台
- 小陀螺
- 基础 wheel odometry
- Isaac 中运动验证

## 6.2 第一阶段绝对禁止的扩散任务
本阶段**禁止提前做**：

- Small Point-LIO
- Nav2
- 地图
- MPPI
- MPC
- RL
- 战术决策
- 比赛场地语义导航
- 多机器人对抗逻辑

## 6.3 第一阶段输出接口
第一阶段结束后固定输出：

### 输入
```text
vx, vy, wz
mode
frame
```

### 输出
```text
4 * steering target
4 * drive target
vx_est, vy_est, wz_est
x, y, yaw
```

---

# 7. Swerve 方案（底盘基础方案）

## 7.1 坐标系
统一采用 ROS REP-103：

- +x：车头前方
- +y：车体左方
- +z：向上

定义：

- `vx > 0`：前进
- `vy > 0`：向左
- `wz > 0`：俯视逆时针

## 7.2 运动学
对第 i 个舵轮，轮模块位置为 `(x_i, y_i)`：

```text
v_ix = vx - wz * y_i
v_iy = vy + wz * x_i
theta_i = atan2(v_iy, v_ix)
s_i = sqrt(v_ix^2 + v_iy^2)
```

## 7.3 最短舵角优化
若目标角相对当前角度差超过 90°：

- 舵角加 π
- 驱动速度反向

减少无意义大角度转向。

## 7.4 零速保持
当轮速接近 0 时：

- 保持上一时刻舵角
- 驱动速度置 0

避免停车抖动。

## 7.5 轮速整体饱和
如果某轮速度超上限：

- 四轮统一缩放
- 保持整体运动意图

## 7.6 正运动学与里程计
由四轮舵角与轮速反推：

- `vx, vy, wz`
- 再积分得到 `x, y, yaw`

## 7.7 模式
底盘模式最少包含：

- `STOP`
- `DIRECT`
- `FOLLOW`
- `SPIN`

### DIRECT
外部直接给 `vx, vy, wz`

### FOLLOW
平移按 GIMBAL_FRAME
旋转由云台相对底盘 yaw 的跟随控制器给出

### SPIN
平移通常按 WORLD_FRAME 或 GIMBAL_FRAME
同时叠加固定 `wz_spin`

---

# 8. 第一阶段 Isaac Sim 目标

## 8.1 仿真目标
不是“好看”，而是验证运动链正确。

## 8.2 必须完成
- 机器人 Articulation
- 4 个 steering joint
- 4 个 drive joint
- `/cmd_vel` 或内部 twist 输入
- 通过 IK 驱动物理运动
- 记录 Ground Truth
- 自动测试：

  - forward
  - backward
  - strafe
  - diagonal
  - pure rotation
  - follow
  - spin

## 8.3 第一阶段测试世界
使用简单测试场，不用 RMUL 场地：

- 平地
- 网格线
- 坐标轴
- 足够大空间

例如：

- `Phase1_TestWorld.usd`

---

# 9. 第二阶段起：RMUL 场地资产策略

用户已提供：

- `RMUL2026.usd`

该文件后续固定视为：

> **RMUL 2026 3V3 比赛场地 USD 原始资产**

## 9.1 资产原则
- 原始文件不直接修改
- 派生 Isaac 场地版本
- 用 layer 或副本增加：

  - collision
  - semantic region
  - spawn point
  - control zone
  - supply zone
  - forbidden zone

## 9.2 典型结构
```text
simulation/
└── isaac/
    ├── assets/
    │   └── worlds/
    │       └── rmul2026/
    │           ├── RMUL2026_3v3_original.usd
    │           └── RMUL2026_3v3_isaac.usd
    └── worlds/
        ├── Phase1_TestWorld.usd
        └── RMUL2026_3v3_Physics.usd
```

---

# 10. 后续完整开发路线图

## Phase 1：舵轮基础层
**目标**：让机器人正确运动
**交付**：IK/FK/Odom/Follow/Spin

## Phase 2：Isaac 数字孪生
**目标**：完善机器人模型与基础测试世界
**交付**：可复现实车运动特征的机器人仿真体

## Phase 3：定位
**目标**：单 MID360 跑通 Small Point-LIO
**交付**：稳定 `odom`

## Phase 4：重定位与地图
**目标**：先验地图 + 重定位
**交付**：`map -> odom`

## Phase 5：传统导航 baseline
**目标**：HOME→CONTROL→PATROL→HOME
**交付**：无 RL 的自主导航闭环

## Phase 6：Safety Guard
**目标**：风控独立
**交付**：速度/碰撞/超时/功率/禁区保护

## Phase 7：Local RL
**目标**：动态环境下局部穿行增强
**交付**：Residual RL / fallback

## Phase 8：BT 战术完整局
**目标**：先不用 Tactical RL，打完整流程
**交付**：开局抢点、守点、低血回补等

## Phase 9：Tactical RL
**目标**：高层战术决策增强
**交付**：goal 级策略

---

# 11. Local RL 方案（后期）

## 11.1 定位
Local RL 只负责：

> **动态环境里具体怎么穿**

不负责全局地图规划和总战术。

## 11.2 Observation（建议）
- LiDAR sector / 极坐标距离
- goal vector
- path tangent
- cross-track error
- corridor width
- current `vx vy wz`
- previous action
- nearest obstacle / dynamic obstacle info

## 11.3 Action（建议）
优先采用 Residual RL：

```text
u = u_base + alpha * u_rl
```

其中：

- `u_base` = MPPI / MPC / 传统 controller
- `u_rl` = `Δvx, Δvy, Δwz`

## 11.4 Reward（原则）
奖励：

- 路径前进
- 接近目标
- 保持在走廊内
- 通过动态障碍

惩罚：

- 碰撞
- 贴障太近
- 偏离路径
- 速度抖动过大
- 卡住

---

# 12. Tactical RL 方案（后期）

## 12.1 定位
Tactical RL 只负责：

> **去哪 / 当前站哪一侧 / 是否回补 / 是否前压**

不直接输出电机或轮速。

## 12.2 动作空间（离散）
例如：

- HOME
- CONTROL_CENTER
- CONTROL_LEFT
- CONTROL_RIGHT
- PATROL_BACK
- PATROL_FRONT
- PRESS
- RETREAT
- RECOVER

## 12.3 Reward 原则
必须和 RMUL 机制挂钩：

- 控制区收益
- 胜利点差
- 存活
- 低血安全返回
- 无意义死亡大惩罚

---

# 13. Safety Guard（全程独立存在）

RL 永远不能绕过 Safety Guard。

## 13.1 必须保护
- 最大线速度/角速度
- 最大加速度
- 碰撞预测 / TTC
- 场地边界
- 禁区
- 功率限制
- 定位失效
- LiDAR/IMU 超时
- NUC/ROS 节点超时
- policy 推理超时
- policy NaN/Inf
- 通信断连
- 急停

## 13.2 核心原则
```text
Planner / RL
     │
     ▼
Safety Guard
     │
     ▼
Swerve
```

不是：

```text
RL -> Swerve
```

---

# 14. 三人分工（长期）

## A：Simulation / Localization / Mapping
负责：
- Isaac Sim
- USD / URDF / 传感器仿真
- Small Point-LIO
- 地图 / 重定位
- rosbag / 数据回放

## B：Planning / RL / Decision
负责：
- Global / Semantic planner
- MPPI / MPC baseline
- Local RL
- BT / Tactical RL
- Evaluation

## C：Vehicle / Integration / Referee
负责：
- 底盘控制
- 舵轮运动学实车链路
- STM32 / CAN / 编码器
- 裁判系统
- NUC ↔ MCU 通讯
- Watchdog / 急停

## 14.1 防止三人做成三个孤岛
必须固定：
- 每周一次整车联调
- 统一接口
- 统一消息定义
- 统一日志格式
- 代码 review 交叉进行

---

# 15. 固定接口（建议冻结）

## 15.1 RobotState
- pose
- twist
- hp
- heat
- power
- localization_quality

## 15.2 WorldModel
- obstacles
- enemy estimate
- control zone status
- semantic region

## 15.3 TacticalGoal
- goal_id
- target pose / target region
- aggressiveness

## 15.4 ReferencePath
- path points
- path tangent
- corridor width

## 15.5 ChassisCommand
- `vx`
- `vy`
- `wz`
- mode
- frame

## 15.6 SafetyStatus
- normal
- speed_limited
- localization_degraded
- fallback_active
- e_stop

---

# 16. 开发中的“禁止事项”

后续所有开发必须避免：

1. **没有底盘基础，就提前做 RL**
2. **没有稳定 odom，就开始调导航**
3. **把比赛规则写死在低层控制**
4. **到处用 `*-1` 修方向**
5. **把 joint name / geometry 写死在代码里**
6. **为仿真作弊，直接 set pose 替代真实舵轮运动**
7. **让 RL 直接绕过 Safety Guard**
8. **同时推进太多方向，没人真正收口**
9. **没有 Gate 就进入下一阶段**
10. **把 RMUC 的机制直接套给 RMUL**

---

# 17. Gate 机制（必须遵守）

## Gate P1：舵轮基础层
通过条件：
- IK/FK 单元测试通过
- Isaac 运动正确
- Follow / Spin 正确
- wheel odometry 可用

## Gate P2：数字孪生
通过条件：
- 机器人模型稳定
- 仿真链可复用
- Ground Truth 可记录

## Gate P3：定位
通过条件：
- 单 MID360 的 Small Point-LIO 稳定输出 odom

## Gate P4：重定位
通过条件：
- 先验地图 + 重定位闭环打通

## Gate P5：导航 baseline
通过条件：
- 无 RL 情况下，连续多次完成 HOME→CENTER→HOME

## Gate P6：Safety
通过条件：
- 超时/碰撞/定位异常均能受控 fallback

## Gate P7：Local RL
通过条件：
- 比 baseline 至少在局部避障性能上有清晰收益
- 且风险可控

## Gate P8：战术闭环
通过条件：
- BT 可完整跑局流程

## Gate P9：Tactical RL
通过条件：
- 相比 BT / hand-tuned 有明确收益
- 不破坏稳定性

---

# 18. Harness Engineering 使用方法（给后续所有对话/提示词）

后续无论给 Codex 还是给我发任务，都建议遵循下面模板。

## 18.1 标准任务模板

```text
你现在在执行 RMUL 哨兵项目。
必须遵守主框架文件《RMUL 哨兵项目总方案（Harness Engineering 主框架）》。

当前阶段：
[填写 Phase 1 / Phase 2 / ...]

当前 Gate：
[填写 Gate 名称]

本次任务目标：
[明确只做什么]

输入：
[列出输入/已有内容]

输出：
[列出必须交付]

约束：
- 不得扩展到下一阶段
- 不得破坏已有工程
- 不得绕过 Safety Guard
- 必须和既有接口一致

验收标准：
[列出测试与 PASS 条件]

最终请输出：
1. 修改了什么
2. 哪些测试通过
3. 哪些问题未解决
4. 是否达到当前 Gate
```

## 18.2 Codex 任务使用原则
每次只做一个清晰闭环，例如：

- 审计当前舵轮模型
- 实现 IK/FK
- 实现 Follow
- 构建 Phase1_TestWorld
- 接入 Small Point-LIO

不要一个 prompt 同时要求它：

- 写底盘
- 写导航
- 写 RL
- 写 Isaac Lab
- 写战术

---

# 19. 当前立即执行建议

基于本总方案，**当前唯一建议主任务**：

> **继续完成 Phase 1：四舵轮底盘基础层。**

当前顺序必须是：

```text
Gate 1  模型审计
   ↓
Gate 2  IK/FK/优化/odom
   ↓
Gate 3  Isaac 运动验证
   ↓
Gate 4  Follow
   ↓
Gate 5  Spin
```

只有这条线完成后，才进入：

- MID360
- Small Point-LIO
- RMUL2026.usd 导入
- 地图
- 导航

---

# 20. 项目最终追求的状态

最终系统应该达到：

```text
Tactical BT / RL
        │
        ▼
Semantic / Global Planner
        │
        ▼
Traditional Local Planner + Local RL
        │
        ▼
Safety Guard
        │
        ▼
Swerve Chassis
        │
        ▼
STM32 / Motors
```

并且：

- 仿真和实车接口一致
- RL 是增强层，不是基础依赖
- 比赛规则约束能映射到 reward / safety / tactics
- 整个项目能持续迭代而不走偏

---

# 21. 结论（项目总原则）

后续所有开发，统一遵守以下 8 条总原则：

1. **先底盘，后导航，再 RL**
2. **先保底 baseline，再做性能增强**
3. **单 MID360 + 单 NUC 是硬约束**
4. **RMUL 规则优先于通用想象**
5. **仿真与实车接口必须同构**
6. **Safety Guard 始终独立**
7. **每个阶段必须过 Gate**
8. **后续所有开发必须在本框架内推进**

---

# 22. 文件状态

本文件为当前项目的**顶层主框架文件**。
建议命名：

```text
HARNESS_RMUL_SENTRY_MASTER_FRAMEWORK.md
```

后续如果方案有重大更新，请新增版本，例如：

- `HARNESS_RMUL_SENTRY_MASTER_FRAMEWORK_v1.1.md`
- `HARNESS_RMUL_SENTRY_MASTER_FRAMEWORK_v1.2.md`

不要直接丢失旧版本。
