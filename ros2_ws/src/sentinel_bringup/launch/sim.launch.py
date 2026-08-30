from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description() -> LaunchDescription:
    share = Path(get_package_share_directory("sentinel_bringup"))
    return LaunchDescription(
        [
            DeclareLaunchArgument("policy_backend", default_value="mock"),
            DeclareLaunchArgument("policy_dir", default_value=""),
            DeclareLaunchArgument("rmuc_rl_path", default_value=""),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    str(share / "launch" / "sentinel.launch.py")
                ),
                launch_arguments={
                    "mode": "sim",
                    "use_sim_time": "true",
                    "initial_estop": "true",
                    "policy_backend": LaunchConfiguration("policy_backend"),
                    "policy_dir": LaunchConfiguration("policy_dir"),
                    "rmuc_rl_path": LaunchConfiguration("rmuc_rl_path"),
                    "start_nav2": "true",
                    "send_nav2_goal": "true",
                    "start_hardware": "false",
                    "start_mock_hardware": "false",
                    "start_mock_battle": "false",
                    "start_mock_nav": "false",
                }.items(),
            )
        ]
    )
