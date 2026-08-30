#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
workspace_root="$(cd -- "${script_dir}/../.." && pwd)"

required=(python3 gcc unzip)
failed=0
for executable in "${required[@]}"; do
  if ! command -v "${executable}" >/dev/null 2>&1; then
    echo "MISSING: ${executable}"
    failed=1
  else
    echo "OK: ${executable} -> $(command -v "${executable}")"
  fi
done

if [[ -r /opt/ros/jazzy/setup.bash ]]; then
  echo "OK: ROS 2 Jazzy"
else
  echo "MISSING: /opt/ros/jazzy/setup.bash"
  failed=1
fi
if [[ -r "${workspace_root}/ros2_ws/install/setup.bash" ]]; then
  echo "OK: ROS workspace built"
else
  echo "NOT BUILT: ros2_ws/install/setup.bash"
fi

echo "ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-unset}"
echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-unset}"
echo "ROS_LOCALHOST_ONLY=${ROS_LOCALHOST_ONLY:-unset}"
exit "${failed}"
