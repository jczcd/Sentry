#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/sentinel_env.sh"
echo "ROS_DOMAIN_ID=$ROS_DOMAIN_ID"
echo "RMW_IMPLEMENTATION=$RMW_IMPLEMENTATION"
echo
pgrep -af 'launch_stage.py.*Sentry_stage5d_swerve' || echo 'Isaac process: NOT FOUND'
echo
topics=(/clock /cmd_vel /sentry/cmd_vel_safe /sentry/odom /joint_states /tf /tf_static /sentry/lidar/points /sentry/scan /sentry/imu /sentry/lio/odom /sentry/lio/cloud_registered)
listing="$(ros2 topic list -t 2>/dev/null || true)"
for topic in "${topics[@]}"; do
  match="$(printf '%s\n' "$listing" | awk -v topic="$topic" '$1 == topic {print; exit}')"
  printf '%-31s %s\n' "$topic" "${match:-MISSING}"
done
