#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(cd "$DIR/../.." && pwd)"
# shellcheck disable=SC1091
source "$DIR/sentinel_env.sh"
diagnostic=0; with_lio=0; with_rviz=0; preflight=0
while (($#)); do
  case "$1" in
    --diagnostic) diagnostic=1 ;;
    --with-lio) with_lio=1 ;;
    --rviz) with_rviz=1 ;;
    --preflight) preflight=1 ;;
    -h|--help) echo "Usage: $0 [--diagnostic] [--with-lio] [--rviz] [--preflight]"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done
if [[ "$SENTRY_MODEL_APPROVED" != "1" || -z "$SENTRY_USD_PATH" || ! -f "$SENTRY_USD_PATH" ]]; then
  echo "GUI blocked: set SENTRY_USD_PATH and obtain human GUI approval first" >&2
  exit 2
fi
REPORT="$SENTINEL_ISAAC_INTEGRATION/output/phase_j_runtime_report.json"
if ((with_lio)); then
  python3 - "$REPORT" <<'PY' || { echo "Point-LIO NOT VALIDATED: --with-lio refused" >&2; exit 3; }
import json,sys
try: r=json.load(open(sys.argv[1]))
except Exception: raise SystemExit(1)
raise SystemExit(0 if r.get('FUNCTIONAL_POINT_LIO_PASS') is True else 1)
PY
fi
mkdir -p "$ROOT/logs" "$SENTINEL_ISAAC_INTEGRATION/output"
PIDS=(); cleanup(){ for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done; for pid in "${PIDS[@]}"; do wait "$pid" 2>/dev/null || true; done; }
trap cleanup EXIT INT TERM
ros2 launch sentinel_description description.launch.py use_sim_time:=true >"$ROOT/logs/gui_rsp.log" 2>&1 & PIDS+=($!)
ros2 run sentinel_core safety_supervisor --ros-args -r __ns:=/sentry -r cmd_vel:=/cmd_vel -p initial_mode:=sim -p command_timeout_s:=0.5 -p max_linear_x:=0.2 -p max_linear_y:=0.2 -p max_linear_speed:=0.2828427125 -p max_angular_speed:=0.6 >"$ROOT/logs/gui_safety.log" 2>&1 & PIDS+=($!)
isaac_args=("$ISAAC_SIM_PYTHON" "$SENTINEL_ISAAC_INTEGRATION/scripts/launch_stage.py" --stage "$SENTRY_USD_PATH" --enable-swerve-control --enable-state-publishers --enable-sensors --sensor-config "$SENTINEL_ISAAC_INTEGRATION/config/phase_i_sensors.json" --phase-f-report "$SENTINEL_ISAAC_INTEGRATION/output/gui_phase_f_report.json" --phase-f-evidence "$SENTINEL_ISAAC_INTEGRATION/output/gui_phase_f_evidence.json")
if ((diagnostic)); then isaac_args+=(--diagnostic-environment --show-lidar-debug); fi
if ((preflight)); then isaac_args+=(--headless); fi
"${isaac_args[@]}" >"$ROOT/logs/gui_isaac.log" 2>&1 & ISAAC_PID=$!; PIDS+=($ISAAC_PID)
if ((with_lio)); then
  ros2 run point_lio pointlio_mapping --ros-args -r __ns:=/sentry/lio --params-file "$ROOT/ros2_ws/src/sentinel_navigation/config/point_lio_sim.yaml" -r aft_mapped_to_init:=odom >"$ROOT/logs/gui_point_lio.log" 2>&1 & PIDS+=($!)
fi
if ((with_rviz)); then
  rviz2 -d "$ROOT/ros2_ws/src/sentinel_navigation/rviz/sentinel_sim.rviz" >"$ROOT/logs/gui_rviz.log" 2>&1 & PIDS+=($!)
fi
wait_message(){ local topic="$1"; timeout 3 ros2 topic echo "$topic" --once >/dev/null 2>&1; }
deadline=$((SECONDS+150)); ready=0
while ((SECONDS<deadline)); do
  kill -0 "$ISAAC_PID" 2>/dev/null || { echo "GUI FAIL: Isaac exited; see logs/gui_isaac.log" >&2; exit 4; }
  if wait_message /clock && wait_message /sentry/odom && wait_message /sentry/lidar/points && wait_message /sentry/imu; then
    info="$(ros2 topic info /sentry/cmd_vel_safe -v 2>/dev/null || true)"
    if grep -q 'Subscription count: [1-9]' <<<"$info"; then ready=1; break; fi
  fi
  sleep 1
done
((ready)) || { echo "GUI FAIL: ROS readiness timeout" >&2; exit 5; }
lio_state="NOT VALIDATED"; ((with_lio)) && lio_state=ACTIVE
cat <<EOF
========================================
SENTINEL ISAAC GUI READY
========================================
Isaac Stage:
$SENTRY_USD_PATH

ROS_DOMAIN_ID:
$ROS_DOMAIN_ID

Control:
./tools/integration/sentry_teleop.sh

Status:
./tools/integration/sentinel_gui_status.sh

LiDAR:
/sentry/lidar/points

IMU:
/sentry/imu

GT odom:
/sentry/odom

Point-LIO:
$lio_state

IMPORTANT:
Runtime changes are NOT saved to the approved USD.
DO NOT SAVE RUNTIME DIAGNOSTIC STAGE.
========================================
EOF
if ((preflight)); then exit 0; fi
wait "$ISAAC_PID"
