# Open-source references

These projects are references, not vendored dependencies. Audit license, branch, interfaces, and compatibility before reuse.

## MCP and ROS learning material

| Project | Pinned observation | Use |
|---|---|---|
| https://github.com/robotmcp/ros-mcp-server | commit `f1c023bb5570794ee4d935aa2c7c06e025810952` | MCP-to-rosbridge bridge and client setup |
| https://gitee.com/gwmunan/ros2.wiki.git | commit `bd480cec3444b41d7b7c8dd6835a062054d86467` | Chinese ROS 2/SLAM/Point-LIO learning notes |

## Navigation, localization, simulation, and planning candidates

- `SMBU-PolarBear-Robotics-Team/point_lio`, observed branch `RM2025_SMBU_auto_sentry`, historical commit `e85e79558cf746f6699888a54285fe48b3b0ac71`;
- Livox `livox_ros_driver2` and `Livox-SDK2`;
- `pb2025_sentry_nav`;
- `cod_-rm2026_-navigation`;
- `rose_navigation`;
- `awakening`;
- `small_point_lio`;
- `ISAAC-RM`;
- `ERASOR2`;
- `pb_rm_simulation`;
- `navi_minco_bit`;
- `sentry26`;
- `HERO_2026_Sentry_NAV`.

The names above came from project research and may move or disappear. Record exact URL, license, branch, and commit in a dependency manifest before importing code.

## Point-LIO historical audit notes

The observed PolarBear branch used:

- package/executable `point_lio` / `pointlio_mapping`;
- Livox custom-message and generic `sensor_msgs/msg/PointCloud2` parsers;
- a generic path compatible with `x`, `y`, `z`, `intensity`, and floating `time`;
- `timestamp_unit` enum value `SEC=0` for seconds;
- a default TF behavior that must be disabled or isolated to avoid duplicate `odom -> base_link` ownership.

Re-audit the actual checked-out commit before configuring a current build.
