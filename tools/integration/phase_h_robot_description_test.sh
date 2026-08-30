#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"&&pwd)"; ROOT="$(cd "$DIR/../.."&&pwd)"; source "$DIR/sentinel_env.sh"; sentinel_require_approved_usd
OUT="$SENTINEL_ISAAC_INTEGRATION/output"; LOG="$ROOT/logs"; mkdir -p "$OUT" "$LOG"; REPORT="$OUT/phase_h_runtime_report.json"; EVIDENCE="$OUT/phase_h_topic_evidence.json"; URDF=/tmp/phase_h_robot_description.urdf; rm -f "$REPORT" "$EVIDENCE" "$URDF"
PIDS=(); cleanup(){ for p in "${PIDS[@]}";do kill "$p" 2>/dev/null||true;done;for p in "${PIDS[@]}";do wait "$p" 2>/dev/null||true;done;};trap cleanup EXIT INT TERM
fail(){ echo RESULT: FAIL;echo FAILED_STAGE=$1;echo ROOT_CAUSE=$2;exit 1;}
ros2 launch sentinel_description description.launch.py use_sim_time:=true >"$LOG/phase_h_rsp.log" 2>&1 & PIDS+=($!)
deadline=$((SECONDS+20));while ((SECONDS<deadline));do ros2 param get /robot_state_publisher robot_description --hide-type >"$URDF" 2>/dev/null&&grep -q '<robot' "$URDF"&&break;sleep 1;done; grep -q '<robot' "$URDF"||fail robot_description unavailable
python3 "$DIR/phase_g_state_observer.py" --evidence "$EVIDENCE" --report "$REPORT" --urdf "$URDF" >"$LOG/phase_h_observer.log" 2>&1 & PIDS+=($!)
ros2 run sentinel_core safety_supervisor --ros-args -r __ns:=/sentry -r cmd_vel:=/cmd_vel -p initial_mode:=sim -p command_timeout_s:=0.5 -p max_linear_x:=0.2 -p max_linear_y:=0.2 -p max_linear_speed:=0.2828427125 -p max_angular_speed:=0.6 >"$LOG/phase_h_safety.log" 2>&1 & PIDS+=($!)
"$ISAAC_SIM_PYTHON" "$SENTINEL_ISAAC_INTEGRATION/scripts/launch_stage.py" --stage "$SENTRY_USD_PATH" --headless --enable-swerve-control --enable-state-publishers --state-publish-rate-hz 50 --phase-f-report "$OUT/phase_h_unused_f.json" --phase-f-evidence "$OUT/phase_f_topic_evidence.json" >"$LOG/phase_h_isaac.log" 2>&1 & ISAAC=$!;PIDS+=($ISAAC)
deadline=$((SECONDS+90));while ((SECONDS<deadline));do [[ -f "$REPORT" ]]&&python3 - "$REPORT" <<'PY' && break
import json,sys
r=json.load(open(sys.argv[1]));sys.exit(0 if r.get('counts',{}).get('odom',0)>=25 and r.get('stationary',{}).get('pass') is True else 1)
PY
kill -0 "$ISAAC" 2>/dev/null||fail isaac exited;sleep 1;done
[[ -f "$REPORT" ]]||fail feedback missing
ros2 topic pub --once /sentry/estop std_msgs/msg/Bool '{data: false}' >/dev/null
pub(){ set +e;timeout 3 ros2 topic pub -r 15 /cmd_vel geometry_msgs/msg/Twist "$1" >/dev/null 2>&1;s=$?;set -e;[[ $s == 0 || $s == 124 ]]||fail publish "$s";ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist '{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}' >/dev/null;sleep 2;}
pub '{linear: {x: 0.12, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}';pub '{linear: {x: 0.0, y: 0.12, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}';pub '{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.35}}'
deadline=$((SECONDS+15));while ((SECONDS<deadline));do python3 - "$REPORT" <<'PY' && { echo '[OK] PHASE H COMPLETE';exit 0; }
import json,sys
r=json.load(open(sys.argv[1]));sys.exit(0 if r.get('runtime_validation_all_pass') is True and r.get('joint_match_count')==11 and not r.get('tf_cycle_detected') and not r.get('duplicate_parent_detected') and not r.get('base_footprint_conflict') else 1)
PY
sleep 1;done;fail report "strict TF/URDF gate failed"
