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
            DeclareLaunchArgument("hardware_endpoint", default_value="192.168.10.2:20000"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    str(share / "launch" / "sentinel.launch.py")
                ),
                launch_arguments={
                    "mode": "hil",
                    "use_sim_time": "false",
                    "initial_estop": "true",
                    "policy_backend": "mock",
                    "start_nav2": "true",
                    "send_nav2_goal": "true",
                    "start_hardware": "true",
                    "hardware_transport": "udp",
                    "hardware_endpoint": LaunchConfiguration("hardware_endpoint"),
                    "start_mock_hardware": "false",
                    "start_mock_battle": "true",
                    "start_mock_nav": "false",
                }.items(),
            )
        ]
    )
