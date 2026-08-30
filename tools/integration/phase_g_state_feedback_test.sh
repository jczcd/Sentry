#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(cd "$DIR/../.." && pwd)"
# shellcheck disable=SC1091
source "$DIR/sentinel_env.sh"
sentinel_require_approved_usd
OUT="$SENTINEL_ISAAC_INTEGRATION/output"; LOG="$ROOT/logs"; mkdir -p "$OUT" "$LOG"
REPORT="$OUT/phase_g_runtime_report.json"; EVIDENCE="$OUT/phase_g_topic_evidence.json"; rm -f "$REPORT" "$EVIDENCE"
PIDS=(); cleanup(){ for p in "${PIDS[@]}"; do kill "$p" 2>/dev/null||true; done; for p in "${PIDS[@]}"; do wait "$p" 2>/dev/null||true; done; }; trap cleanup EXIT INT TERM
fail(){ echo "RESULT: FAIL"; echo "FAILED_STAGE=$1"; echo "ROOT_CAUSE=$2"; exit 1; }
python3 "$DIR/phase_g_state_observer.py" --evidence "$EVIDENCE" --report "$REPORT" >"$LOG/phase_g_observer.log" 2>&1 & PIDS+=($!)
ros2 run sentinel_core safety_supervisor --ros-args -r __ns:=/sentry -r cmd_vel:=/cmd_vel -p initial_mode:=sim -p command_timeout_s:=0.5 -p max_linear_x:=0.2 -p max_linear_y:=0.2 -p max_linear_speed:=0.2828427125 -p max_angular_speed:=0.6 >"$LOG/phase_g_safety.log" 2>&1 & PIDS+=($!)
"$ISAAC_SIM_PYTHON" "$SENTINEL_ISAAC_INTEGRATION/scripts/launch_stage.py" --stage "$SENTRY_USD_PATH" --headless --enable-swerve-control --enable-state-publishers --state-publish-rate-hz 50 --phase-f-report "$OUT/phase_g_unused_phase_f.json" --phase-f-evidence "$OUT/phase_f_topic_evidence.json" >"$LOG/phase_g_isaac.log" 2>&1 & ISAAC_PID=$!; PIDS+=($ISAAC_PID)
wait_topic(){ local t=$1 deadline=$((SECONDS+90)); while ((SECONDS<deadline)); do kill -0 "$ISAAC_PID" 2>/dev/null||fail "$t" "Isaac exited"; ros2 topic list 2>/dev/null|grep -qx "$t"&&return; sleep 1; done; fail "$t" timeout; }
for t in /clock /sentry/odom /joint_states /tf /sentry/cmd_vel_safe; do wait_topic "$t"; done
deadline=$((SECONDS+20)); while ((SECONDS<deadline)); do ros2 node list 2>/dev/null|grep -qx /phase_g_state_observer&&break; sleep 1; done
ros2 node list 2>/dev/null|grep -qx /phase_g_state_observer||fail observer "observer discovery timeout"
sleep 3
[[ "$(ros2 topic type /sentry/odom)" == nav_msgs/msg/Odometry ]]||fail odom_type mismatch
[[ "$(ros2 topic type /joint_states)" == sensor_msgs/msg/JointState ]]||fail joint_type mismatch
[[ "$(ros2 topic type /tf)" == tf2_msgs/msg/TFMessage ]]||fail tf_type mismatch
deadline=$((SECONDS+30)); while ((SECONDS<deadline)); do
  if [[ -f "$REPORT" ]] && python3 - "$REPORT" <<'PY'
import json,sys
r=json.load(open(sys.argv[1])); s=r.get("stationary")
sys.exit(0 if r.get("counts",{}).get("odom",0)>=25 and s and s.get("pass") is True else 1)
PY
  then break; fi
  sleep 1
done
[[ -f "$REPORT" ]] && python3 - "$REPORT" <<'PY' || fail stationary "fresh odom/stationary evidence timeout"
import json,sys
r=json.load(open(sys.argv[1]));s=r.get("stationary");sys.exit(0 if r.get("counts",{}).get("odom",0)>=25 and s and s.get("pass") is True else 1)
PY
ros2 topic pub --once /sentry/estop std_msgs/msg/Bool '{data: false}' >/dev/null; sleep 3
pub(){ set +e; timeout 3 ros2 topic pub -r 15 /cmd_vel geometry_msgs/msg/Twist "$1" >/dev/null 2>&1; s=$?; set -e; [[ $s == 0 || $s == 124 ]]||fail publish "$s"; ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist '{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}' >/dev/null; sleep 2; }
pub '{linear: {x: 0.12, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}'
pub '{linear: {x: 0.0, y: 0.12, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}'
pub '{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.35}}'
deadline=$((SECONDS+10)); while ((SECONDS<deadline)); do [[ -f "$REPORT" ]]&&python3 - "$REPORT" <<'PY' && { echo '[OK] PHASE G COMPLETE'; exit 0; }
import json,sys
r=json.load(open(sys.argv[1]));sys.exit(0 if r.get('runtime_validation_all_pass') is True else 1)
PY
sleep 1; done
fail report "strict evidence gate failed"
