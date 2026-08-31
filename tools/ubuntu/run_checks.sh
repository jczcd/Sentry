#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
workspace_root="$(cd -- "${script_dir}/../.." && pwd)"
cd "${workspace_root}"
python3 -m unittest discover -s tests -v
python3 -m compileall -q \
  ros2_ws/src \
  isaac_sim/scripts \
  tools/common \
  training
