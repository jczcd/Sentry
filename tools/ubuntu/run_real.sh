#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${script_dir}/_env.sh"

hardware_endpoint="${1:-/dev/ttyACM0}"
policy_dir="${2:-${SENTINEL_POLICY_DIR:-}}"
if [[ -z "${policy_dir}" ]]; then
  echo "Usage: $0 [/dev/ttyACM0] /absolute/path/to/policy_run" >&2
  echo "Real mode remains blocked because no policy directory was supplied." >&2
  exit 2
fi
exec ros2 launch sentinel_bringup real.launch.py \
  hardware_endpoint:="${hardware_endpoint}" \
  policy_dir:="${policy_dir}" \
  rmuc_rl_path:="${SENTINEL_WORKSPACE}/training/RMUC-OfflineRL"
