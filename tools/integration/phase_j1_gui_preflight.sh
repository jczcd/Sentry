#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(cd "$DIR/../.." && pwd)"
# shellcheck disable=SC1091
source "$DIR/sentinel_env.sh"
sentinel_require_approved_usd
[[ "$ROS_DISTRO" == jazzy && "$ROS_DOMAIN_ID" == 0 && "$RMW_IMPLEMENTATION" == rmw_fastrtps_cpp ]]
bash -n "$DIR/run_sentinel_gui.sh" "$DIR/sentry_teleop.sh" "$DIR/sentinel_gui_status.sh"
python3 -m py_compile "$DIR/sentry_teleop.py" "$SENTINEL_ISAAC_INTEGRATION/scripts/launch_stage.py" "$SENTINEL_ISAAC_INTEGRATION/scripts/stage5d_sensor_manager.py"
"$DIR/run_sentinel_gui.sh" --diagnostic --preflight
echo '[OK] PHASE J1 GUI PREFLIGHT COMPLETE'
