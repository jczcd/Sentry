from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description() -> LaunchDescription:
    share = Path(get_package_share_directory("sentinel_bringup"))
    return LaunchDescription(
        [
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    str(share / "launch" / "sentinel.launch.py")
                ),
                launch_arguments={
                    "mode": "sim",
                    "use_sim_time": "false",
                    "initial_estop": "false",
                    "policy_backend": "mock",
                    "start_nav2": "false",
                    "send_nav2_goal": "false",
                    "start_hardware": "false",
                    "start_mock_hardware": "true",
                    "start_mock_battle": "true",
                    "start_mock_nav": "true",
                }.items(),
            )
        ]
    )
