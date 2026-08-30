#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
workspace_root="$(cd -- "${script_dir}/../.." && pwd)"

if [[ ! -r /opt/ros/jazzy/setup.bash ]]; then
  echo "ROS 2 Jazzy is not installed or is not readable at /opt/ros/jazzy/setup.bash." >&2
  echo "Run tools/ubuntu/bootstrap_jazzy.sh before building this workspace." >&2
  exit 2
fi

source /opt/ros/jazzy/setup.bash
cd "${workspace_root}/ros2_ws"
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy
colcon build --symlink-install --event-handlers console_direct+

echo "Build complete. Source ros2_ws/install/setup.bash before running."
