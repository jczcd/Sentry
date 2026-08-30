# TF contract

## Required tree

```text
map
└── odom
    └── base_link
        ├── four steer/drive chains
        ├── yaw_big -> yaw_small -> pitch
        └── lidar_link -> imu_link
```

`map` is optional before localization is enabled.

## Ownership

| Edge | Simulation owner | Real owner |
|---|---|---|
| `map -> odom` | localization/relocalization, if enabled | localization/relocalization |
| `odom -> base_link` | Isaac Sim | chosen state estimator |
| `base_link -> robot links` | `robot_state_publisher` | `robot_state_publisher` |
| fixed sensor extrinsics | URDF/robot description | calibrated URDF/robot description |

STM32 sends sensor and joint measurements; it does not publish TF directly.

## Known historical conflict

An earlier Phase G run deferred `/tf_static` because two designs tried to parent `base_link`:

- `odom -> base_link`;
- `base_footprint -> base_link`.

A TF child has one parent. Resolve the robot root contract before restoring static TF. A valid alternative is `odom -> base_footprint -> base_link`, but only if the estimator and robot description are changed coherently and the extra frame serves a defined purpose.

## LIO rule

Keep Isaac truth `/sentry/odom` and estimated `/sentry/lio/odom` separate during simulation evaluation. Disable the LIO package's duplicate `odom -> base_link` broadcaster or remap its frames so only one source owns the edge.
