#!/usr/bin/env bash
set -u

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# Keep the report stable; this script reports missing components itself.
# shellcheck disable=SC1091
source "$script_dir/sentinel_env.sh" >/dev/null 2>&1

blocked=0

report_file() {
    local label="$1"
    local path="$2"
    if [[ -e "$path" ]]; then
        printf '%-26s PASS\n' "$label"
    else
        printf '%-26s BLOCKED (%s missing)\n' "$label" "$path"
        blocked=1
    fi
}

report_command() {
    local label="$1"
    local command_name="$2"
    if command -v "$command_name" >/dev/null 2>&1; then
        printf '%-26s PASS\n' "$label"
    else
        printf '%-26s BLOCKED (%s not found)\n' "$label" "$command_name"
        blocked=1
    fi
}

echo "Sentinel Environment Check"
echo
report_file "Isaac Sim" "$ISAAC_SIM_PATH"
report_file "Isaac Python" "$ISAAC_SIM_PYTHON"
report_file "Isaac launcher" "$ISAAC_SIM_PATH/isaac-sim.sh"
if [[ "$SENTRY_MODEL_APPROVED" == "1" && -n "$SENTRY_USD_PATH" ]]; then
    report_file "Approved USD" "$SENTRY_USD_PATH"
else
    printf '%-26s BLOCKED (explicit GUI approval required)\n' "Approved USD"
    blocked=1
fi
report_file "ROS2 Jazzy" "/opt/ros/jazzy/setup.bash"
report_command "colcon" "colcon"
report_file "rmw_fastrtps_cpp" "/opt/ros/jazzy/share/rmw_fastrtps_cpp"
report_file "ROS2 workspace" "$SENTINEL_ROS2_WS/src"

if [[ -r "$SENTINEL_ROS2_WS/install/setup.bash" ]]; then
    printf '%-26s PASS\n' "ROS2 workspace install"
else
    printf '%-26s NOT BUILT\n' "ROS2 workspace install"
fi

if git -C "$SENTINEL_WORKSPACE_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    printf '%-26s PASS\n' "Git repository"
else
    printf '%-26s BLOCKED (invalid repository)\n' "Git repository"
    blocked=1
fi

echo
if (( blocked )); then
    echo "Overall: BLOCKED_BY_ROS2_DEPENDENCIES"
    exit 2
fi

echo "Overall: PASS"
