#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/sentinel_env.sh"
fail(){ echo "RESULT: FAIL"; echo "FAILED_STAGE=$1"; echo "ROOT_CAUSE=$2"; exit 1; }
ros2 pkg prefix pcl_ros >/dev/null 2>&1 || fail dependency "ros-jazzy-pcl-ros is not installed"
ros2 pkg prefix livox_ros_driver2 >/dev/null 2>&1 || fail dependency "livox_ros_driver2 has not been built"
ros2 pkg prefix point_lio >/dev/null 2>&1 || fail dependency "point_lio has not been built"
fail runtime "Point-LIO functional motion runner is intentionally disabled until dependency/build preflight passes"
