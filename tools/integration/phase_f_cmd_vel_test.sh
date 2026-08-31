#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/sentinel_env.sh"
sentinel_require_approved_usd

LOG_DIR="$WORKSPACE_ROOT/logs"
ISAAC_LOG="$LOG_DIR/phase_f_isaac.log"
SAFETY_LOG="$LOG_DIR/phase_f_safety.log"
REPORT="$SENTINEL_ISAAC_INTEGRATION/output/phase_f_runtime_report.json"
EVIDENCE="$SENTINEL_ISAAC_INTEGRATION/output/phase_f_topic_evidence.json"
mkdir -p "$LOG_DIR" "$SENTINEL_ISAAC_INTEGRATION/output"
rm -f "$REPORT" "$EVIDENCE"

ISAAC_PID=""
SAFETY_PID=""
OBSERVER_PID=""
fail() {
  echo "RESULT: FAIL"
  echo "FAILED_STAGE=$1"
  echo "ROOT_CAUSE=$2"
  echo "LOG=$ISAAC_LOG"
  exit 1
}
cleanup() {
  [[ -z "$ISAAC_PID" ]] || kill "$ISAAC_PID" 2>/dev/null || true
  [[ -z "$SAFETY_PID" ]] || kill "$SAFETY_PID" 2>/dev/null || true
  [[ -z "$OBSERVER_PID" ]] || kill "$OBSERVER_PID" 2>/dev/null || true
  [[ -z "$ISAAC_PID" ]] || wait "$ISAAC_PID" 2>/dev/null || true
  [[ -z "$SAFETY_PID" ]] || wait "$SAFETY_PID" 2>/dev/null || true
  [[ -z "$OBSERVER_PID" ]] || wait "$OBSERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

[[ "$ROS_DISTRO" == jazzy ]] || fail environment "ROS_DISTRO is not jazzy"
[[ "$ROS_DOMAIN_ID" == 0 ]] || fail environment "ROS_DOMAIN_ID is not 0"
[[ "$RMW_IMPLEMENTATION" == rmw_fastrtps_cpp ]] || fail environment "unexpected RMW"
[[ -x "$ISAAC_SIM_PYTHON" ]] || fail environment "Isaac Python missing"
[[ -f "$SENTRY_USD_PATH" ]] || fail environment "approved USD missing"
command -v ros2 >/dev/null || fail environment "ros2 CLI missing"

python3 "$SCRIPT_DIR/phase_f_topic_observer.py" --output "$EVIDENCE" \
  >"$LOG_DIR/phase_f_observer.log" 2>&1 &
OBSERVER_PID=$!

ros2 run sentinel_core safety_supervisor --ros-args \
  -r __ns:=/sentry -r cmd_vel:=/cmd_vel \
  -p initial_mode:=sim -p command_timeout_s:=0.5 \
  -p max_linear_x:=0.2 -p max_linear_y:=0.2 \
  -p max_linear_speed:=0.2828427125 -p max_angular_speed:=0.6 \
  -p max_linear_accel:=3.0 >"$SAFETY_LOG" 2>&1 &
SAFETY_PID=$!

"$ISAAC_SIM_PYTHON" "$SENTINEL_ISAAC_INTEGRATION/scripts/launch_stage.py" \
  --stage "$SENTRY_USD_PATH" --headless --enable-swerve-control \
  --phase-f-report "$REPORT" --phase-f-evidence "$EVIDENCE" \
  >"$ISAAC_LOG" 2>&1 &
ISAAC_PID=$!

wait_for() {
  local description="$1" command="$2" deadline=$((SECONDS + 90))
  while (( SECONDS < deadline )); do
    kill -0 "$ISAAC_PID" 2>/dev/null || fail "$description" "Isaac exited before readiness"
    kill -0 "$OBSERVER_PID" 2>/dev/null || fail "$description" "topic observer exited before readiness"
    if bash -c "$command" >/dev/null 2>&1; then return 0; fi
    sleep 1
  done
  fail "$description" "timeout waiting for readiness"
}

wait_for safety_node "ros2 node list | grep -qx /sentry/safety_supervisor"
ros2 topic pub --once /sentry/estop std_msgs/msg/Bool '{data: false}' >/dev/null
wait_for clock "ros2 topic list | grep -qx /clock"
wait_for safe_topic "ros2 topic list | grep -qx /sentry/cmd_vel_safe"
wait_for safe_subscriber "ros2 topic info /sentry/cmd_vel_safe -v | grep -Eq 'Subscription count: [1-9]'"

[[ "$(ros2 topic type /cmd_vel)" == geometry_msgs/msg/Twist ]] || fail cmd_vel_type "wrong /cmd_vel type"
[[ "$(ros2 topic type /sentry/cmd_vel_safe)" == geometry_msgs/msg/Twist ]] || fail safe_type "wrong safe topic type"
timeout 12 ros2 topic echo /clock --once >/dev/null || fail clock_message "no /clock message"

publish_for() {
  local message="$1" duration="$2"
  set +e
  timeout "$duration" ros2 topic pub -r 15 /cmd_vel geometry_msgs/msg/Twist "$message" >/dev/null 2>&1
  local status=$?
  set -e
  [[ $status -eq 0 || $status -eq 124 ]] || fail ros_publish "ros2 topic pub failed: $status"
}
zero="{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
publish_for "{linear: {x: 0.12, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" 3
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "$zero" >/dev/null; sleep 2
publish_for "{linear: {x: 0.0, y: 0.12, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" 3
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "$zero" >/dev/null; sleep 2
publish_for "{linear: {x: 0.09, y: 0.09, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" 3
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "$zero" >/dev/null; sleep 2
publish_for "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.35}}" 3
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "$zero" >/dev/null; sleep 2

# Watchdog case: deliberately stop publishing without sending zero.
publish_for "{linear: {x: 0.10, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" 1

deadline=$((SECONDS + 45))
while kill -0 "$ISAAC_PID" 2>/dev/null && (( SECONDS < deadline )); do sleep 1; done
kill -0 "$ISAAC_PID" 2>/dev/null && fail runtime_report "Isaac did not finish after watchdog"
wait "$ISAAC_PID" || fail isaac_process "Isaac controller returned non-zero"
ISAAC_PID=""
[[ -f "$REPORT" ]] || fail runtime_report "report missing"

python3 - "$REPORT" <<'PY'
import json, sys
p=sys.argv[1]
r=json.load(open(p))
ok=(r.get("runtime_validation_all_pass") is True and r.get("pass_count")==4
    and r.get("expected_count")==4 and r.get("watchdog_pass") is True
    and r.get("watchdog_triggered") is True
    and r.get("received_raw_msg_count",0)>0 and r.get("received_safe_msg_count",0)>0
    and r.get("clock_pass") is True and r.get("safe_topic_type_pass") is True
    and r.get("last_command_zero") is True)
sys.exit(0 if ok else 1)
PY

echo "[OK] PHASE F COMPLETE"
