#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(cd "$DIR/../.." && pwd)"
# shellcheck disable=SC1091
source "$DIR/sentinel_env.sh"
sentinel_require_approved_usd
OUT="$SENTINEL_ISAAC_INTEGRATION/output"; LOG="$ROOT/logs"; CONFIG="$SENTINEL_ISAAC_INTEGRATION/config/phase_i_sensors.json"
REPORT="$OUT/phase_i2_runtime_report.json"; EVIDENCE="$OUT/phase_i2_topic_evidence.json"; URDF=/tmp/phase_i2_robot_description.urdf
export ROS_LOG_DIR="$LOG/ros2_phase_i2"
mkdir -p "$OUT" "$LOG" "$ROS_LOG_DIR"; rm -f "$REPORT" "$EVIDENCE" "$URDF"
PIDS=()
cleanup(){ for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done; for pid in "${PIDS[@]}"; do wait "$pid" 2>/dev/null || true; done; }
trap cleanup EXIT INT TERM
fail(){ echo "RESULT: FAIL"; echo "FAILED_STAGE=$1"; echo "ROOT_CAUSE=$2"; exit 1; }

ros2 launch sentinel_description description.launch.py use_sim_time:=true >"$LOG/phase_i2_rsp.log" 2>&1 & PIDS+=($!)
deadline=$((SECONDS+20)); while ((SECONDS<deadline)); do
  ros2 param get /robot_state_publisher robot_description --hide-type >"$URDF" 2>/dev/null && grep -q '<robot' "$URDF" && break
  sleep 1
done
grep -q '<robot' "$URDF" || fail robot_description unavailable
python3 "$DIR/phase_i2_mid360_observer.py" --evidence "$EVIDENCE" --report "$REPORT" --config "$CONFIG" --urdf "$URDF" >"$LOG/phase_i2_observer.log" 2>&1 & PIDS+=($!)
ros2 run sentinel_core safety_supervisor --ros-args -r __ns:=/sentry -r cmd_vel:=/cmd_vel -p initial_mode:=sim -p command_timeout_s:=0.5 -p max_linear_x:=0.2 -p max_linear_y:=0.2 -p max_linear_speed:=0.2828427125 -p max_angular_speed:=0.6 >"$LOG/phase_i2_safety.log" 2>&1 & PIDS+=($!)
"$ISAAC_SIM_PYTHON" "$SENTINEL_ISAAC_INTEGRATION/scripts/launch_stage.py" --stage "$SENTRY_USD_PATH" --headless --enable-swerve-control --enable-state-publishers --enable-sensors --state-publish-rate-hz 50 --sensor-config "$CONFIG" --phase-f-report "$OUT/phase_i2_unused_f.json" --phase-f-evidence "$OUT/phase_f_topic_evidence.json" >"$LOG/phase_i2_isaac.log" 2>&1 & ISAAC=$!; PIDS+=($ISAAC)

deadline=$((SECONDS+180)); while ((SECONDS<deadline)); do
  kill -0 "$ISAAC" 2>/dev/null || fail isaac "exited before 3D sensor readiness; see logs/phase_i2_isaac.log"
  if [[ -f "$REPORT" ]] && python3 - "$REPORT" <<'PY'
import json,sys
r=json.load(open(sys.argv[1])); p=r.get('pointcloud',{}); i=r.get('imu',{}); t=r.get('tf',{})
sys.exit(0 if p.get('message_count',0)>2 and p.get('finite_xyz_count',0)>0 and i.get('stationary_pass') and t.get('pass') else 1)
PY
  then break; fi
  sleep 1
done
[[ -f "$REPORT" ]] || fail stationary "no fresh I2 observer report"
python3 - "$REPORT" <<'PY' || fail stationary "3D cloud fields/timing/geometry, IMU, or TF gate failed"
import json,sys
r=json.load(open(sys.argv[1])); p=r.get('pointcloud',{})
ok=(p.get('message_count',0)>2 and p.get('fields_pass') is True and p.get('timing_pass') is True
    and p.get('obstacle_pass') is True and p.get('z_span',0)>0.1 and r.get('imu',{}).get('stationary_pass') is True
    and r.get('tf',{}).get('pass') is True)
sys.exit(0 if ok else 1)
PY

[[ "$(ros2 topic type /sentry/lidar/points)" == sensor_msgs/msg/PointCloud2 ]] || fail pointcloud_type mismatch
[[ "$(ros2 topic type /sentry/scan)" == sensor_msgs/msg/LaserScan ]] || fail scan_type mismatch
[[ "$(ros2 topic type /sentry/imu)" == sensor_msgs/msg/Imu ]] || fail imu_type mismatch
ros2 topic pub --once /sentry/estop std_msgs/msg/Bool '{data: false}' >/dev/null
publish_for(){ set +e; timeout "$2" ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/Twist "$1" >/dev/null 2>&1; status=$?; set -e; [[ $status == 0 || $status == 124 ]] || fail publish "$status"; }
zero='{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}'
publish_for '{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.35}}' 8
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "$zero" >/dev/null; sleep 2
publish_for '{linear: {x: 0.12, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}' 8
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "$zero" >/dev/null; sleep 3

deadline=$((SECONDS+30)); while ((SECONDS<deadline)); do
  python3 - "$REPORT" <<'PY' && { echo '[OK] PHASE I2 COMPLETE'; exit 0; }
import json,sys
r=json.load(open(sys.argv[1])); sys.exit(0 if r.get('runtime_validation_all_pass') is True else 1)
PY
  sleep 1
done
fail report "strict PHASE I2 evidence gate failed"
