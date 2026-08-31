#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${script_dir}/_env.sh"

hardware_endpoint="${1:-192.168.10.2:20000}"
exec ros2 launch sentinel_bringup hil.launch.py \
  hardware_endpoint:="${hardware_endpoint}"
