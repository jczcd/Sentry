from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            DeclareLaunchArgument("workspace_root", default_value="."),
            DeclareLaunchArgument(
                "config_root", default_value="training/jobs"
            ),
            Node(
                package="sentinel_core",
                executable="training_manager",
                namespace="sentry",
                name="training_manager",
                output="screen",
                parameters=[
                    {
                        "enabled": True,
                        "working_directory": LaunchConfiguration(
                            "workspace_root"
                        ),
                        "allowed_config_root": LaunchConfiguration(
                            "config_root"
                        ),
                        "runner_argv": [
                            "python3",
                            "training/run_job.py",
                        ],
                    }
                ],
            ),
        ]
    )
