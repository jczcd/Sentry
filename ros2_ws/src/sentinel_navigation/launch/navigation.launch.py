from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import GroupAction, SetRemap


def generate_launch_description() -> LaunchDescription:
    package_dir = Path(get_package_share_directory("sentinel_navigation"))
    nav2_dir = Path(get_package_share_directory("nav2_bringup"))
    params = str(package_dir / "config" / "nav2.yaml")
    map_file = str(package_dir / "map" / "rmuc2024.yaml")
    namespace = LaunchConfiguration("namespace")
    use_sim_time = LaunchConfiguration("use_sim_time")
    autostart = LaunchConfiguration("autostart")

    nav2_include = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(nav2_dir / "launch" / "bringup_launch.py")),
        launch_arguments={
            "namespace": namespace,
            "use_namespace": "true",
            "slam": "false",
            "map": LaunchConfiguration("map"),
            "use_sim_time": use_sim_time,
            "params_file": LaunchConfiguration("params_file"),
            "autostart": autostart,
            "use_composition": "false",
            "use_respawn": "false",
        }.items(),
    )
    # Keep Nav2's namespaced internal controller output separate, then expose
    # only the smoothed result on the global raw command bus consumed by safety.
    nav2 = GroupAction(
        actions=[
            SetRemap(src="cmd_vel", dst="/sentry/cmd_vel_nav"),
            SetRemap(src="cmd_vel_smoothed", dst="/cmd_vel"),
            SetRemap(src="tf", dst="/tf"),
            SetRemap(src="tf_static", dst="/tf_static"),
            nav2_include,
        ]
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("namespace", default_value="sentry"),
            DeclareLaunchArgument("use_sim_time", default_value="false"),
            DeclareLaunchArgument("autostart", default_value="true"),
            DeclareLaunchArgument("params_file", default_value=params),
            DeclareLaunchArgument("map", default_value=map_file),
            nav2,
        ]
    )
