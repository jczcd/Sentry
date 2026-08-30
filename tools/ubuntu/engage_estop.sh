#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${script_dir}/_env.sh"
ros2 service call /sentry/set_estop \
  sentinel_interfaces/srv/SetEstop "{engaged: true}"
