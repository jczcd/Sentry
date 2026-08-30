#!/usr/bin/env bash
set -uo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$script_dir/sentinel_env.sh"

log_dir="$SENTINEL_WORKSPACE_ROOT/logs"
isaac_log="$log_dir/phase_d_isaac.log"
discovery_file="$(mktemp /tmp/sentinel-phase-d-discovery.XXXXXX)"
topic_info_file="$(mktemp /tmp/sentinel-phase-d-topic-info.XXXXXX)"
clock_message_file="$(mktemp /tmp/sentinel-phase-d-clock.XXXXXX)"
isaac_pid=""

isaac_status="FAIL"
discovery_status="FAIL"
topic_status="FAIL"
type_status="FAIL"
message_status="FAIL"

cleanup() {
    if [[ -n "$isaac_pid" ]] && kill -0 "$isaac_pid" 2>/dev/null; then
        kill "$isaac_pid" 2>/dev/null || true
        wait "$isaac_pid" 2>/dev/null || true
    fi
    rm -f "$discovery_file" "$topic_info_file" "$clock_message_file"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

print_result() {
    local result="$1"
    echo "PHASE D ROS2 ↔ ISAAC SMOKE"
    echo
    echo "ROS_DOMAIN_ID=$ROS_DOMAIN_ID"
    echo "RMW_IMPLEMENTATION=$RMW_IMPLEMENTATION"
    echo
    printf '%-29s %s\n' "Isaac process" "$isaac_status"
    printf '%-29s %s\n' "ROS2 discovery" "$discovery_status"
    printf '%-29s %s\n' "/clock topic" "$topic_status"
    printf '%-29s %s\n' "/clock type" "$type_status"
    printf '%-29s %s\n' "/clock message received" "$message_status"
    echo
    echo "RESULT: $result"
}

fail() {
    local failed_stage="$1"
    local root_cause="$2"
    print_result "FAIL"
    echo "FAILED_STAGE=$failed_stage"
    echo "ROOT_CAUSE=$root_cause"
    echo "LOG=$isaac_log"
    exit 1
}

[[ "$ROS_DISTRO" == "jazzy" ]] || fail "environment" "ROS_DISTRO must be jazzy"
[[ "$ROS_DOMAIN_ID" == "0" ]] || fail "environment" "ROS_DOMAIN_ID must be 0"
[[ "$RMW_IMPLEMENTATION" == "rmw_fastrtps_cpp" ]] \
    || fail "environment" "RMW_IMPLEMENTATION must be rmw_fastrtps_cpp"
command -v ros2 >/dev/null 2>&1 || fail "prerequisite" "ros2 CLI not found"
[[ -x "$ISAAC_SIM_PYTHON" ]] || fail "prerequisite" "Isaac Python is not executable"
[[ "$SENTRY_MODEL_APPROVED" == "1" ]] || fail "prerequisite" "approved USD model gate is closed"
[[ -n "$SENTRY_USD_PATH" && -f "$SENTRY_USD_PATH" ]] \
    || fail "prerequisite" "SENTRY_USD_PATH must point to an approved USD"
[[ -f "$SENTINEL_ISAAC_INTEGRATION/scripts/launch_stage.py" ]] \
    || fail "prerequisite" "Sentinel Isaac launcher not found"

mkdir -p "$log_dir"
: > "$isaac_log"

"$ISAAC_SIM_PYTHON" \
    "$SENTINEL_ISAAC_INTEGRATION/scripts/launch_stage.py" \
    --stage "$SENTRY_USD_PATH" \
    --headless >"$isaac_log" 2>&1 &
isaac_pid=$!

if ! kill -0 "$isaac_pid" 2>/dev/null; then
    fail "Isaac process" "Isaac launcher exited immediately"
fi
isaac_status="PASS"

deadline=$((SECONDS + 90))
while (( SECONDS < deadline )); do
    if ! kill -0 "$isaac_pid" 2>/dev/null; then
        fail "Isaac process" "Isaac exited before /clock discovery"
    fi
    if ros2 topic list --no-daemon --spin-time 1 >"$discovery_file" 2>/dev/null \
        && grep -Fxq '/clock' "$discovery_file"; then
        discovery_status="PASS"
        topic_status="PASS"
        break
    fi
    sleep 1
done

[[ "$topic_status" == "PASS" ]] \
    || fail "ROS2 discovery" "/clock was not discovered within 90 seconds"

if ! ros2 topic info /clock --no-daemon >"$topic_info_file" 2>&1; then
    fail "/clock type" "ros2 topic info failed"
fi
if ! grep -Eq '^Type: +rosgraph_msgs/msg/Clock$' "$topic_info_file"; then
    fail "/clock type" "expected rosgraph_msgs/msg/Clock"
fi
type_status="PASS"

if ! ros2 topic echo /clock rosgraph_msgs/msg/Clock \
    --no-daemon --qos-profile sensor_data --once --timeout 15 \
    >"$clock_message_file" 2>&1; then
    fail "/clock message" "no /clock message received within 15 seconds"
fi
if ! grep -Eq '^clock:' "$clock_message_file"; then
    fail "/clock message" "received output was not a Clock message"
fi
message_status="PASS"

print_result "PASS"
exit 0
