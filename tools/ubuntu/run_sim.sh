#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${script_dir}/_env.sh"

policy_backend="${SENTINEL_POLICY_BACKEND:-mock}"
policy_dir="${SENTINEL_POLICY_DIR:-}"
exec ros2 launch sentinel_bringup sim.launch.py \
  policy_backend:="${policy_backend}" \
  policy_dir:="${policy_dir}" \
  rmuc_rl_path:="${SENTINEL_WORKSPACE}/training/RMUC-OfflineRL"
