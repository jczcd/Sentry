#!/usr/bin/env bash
# Source this file to configure Sentinel ROS 2 / Isaac integration.
# Every path is overrideable so the same checkout works on a laptop or 4090 host.

sentinel_env_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
sentinel_default_workspace="$(cd -- "$sentinel_env_dir/../.." && pwd)"
export SENTINEL_WORKSPACE_ROOT="${SENTINEL_WORKSPACE_ROOT:-$sentinel_default_workspace}"
export SENTINEL_ROOT="${SENTINEL_ROOT:-$(cd -- "$SENTINEL_WORKSPACE_ROOT/.." && pwd)}"
export SENTINEL_ROS2_WS="${SENTINEL_ROS2_WS:-$SENTINEL_WORKSPACE_ROOT/ros2_ws}"
export SENTINEL_ISAAC_INTEGRATION="${SENTINEL_ISAAC_INTEGRATION:-$SENTINEL_WORKSPACE_ROOT/isaac_sim}"

# The USD asset project is intentionally separate from this software checkout.
export SENTINEL_SIM_ROOT="${SENTINEL_SIM_ROOT:-}"
export ISAAC_SIM_PATH="${ISAAC_SIM_PATH:-${HOME:-}/issac-sim/isaac-sim}"
export ISAAC_SIM_PYTHON="${ISAAC_SIM_PYTHON:-$ISAAC_SIM_PATH/python.sh}"
export SENTRY_USD_PATH="${SENTRY_USD_PATH:-}"
export SENTRY_MODEL_APPROVED="${SENTRY_MODEL_APPROVED:-0}"

# Legacy phase scripts may read this alias, but no USD is selected implicitly.
export SENTRY_STAGE5D_USD_PATH="${SENTRY_STAGE5D_USD_PATH:-$SENTRY_USD_PATH}"

sentinel_require_approved_usd() {
    if [[ "$SENTRY_MODEL_APPROVED" != "1" || -z "$SENTRY_USD_PATH" || ! -f "$SENTRY_USD_PATH" ]]; then
        echo "Isaac run blocked: set SENTRY_MODEL_APPROVED=1 and an existing SENTRY_USD_PATH" >&2
        return 2
    fi
}

export ROS_DISTRO="${ROS_DISTRO:-jazzy}"
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}"
export ROS_LOCALHOST_ONLY="${ROS_LOCALHOST_ONLY:-0}"
export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}"

if [[ -n "${HOME:-}" \
    && -f "$HOME/.ros/rosdistro-local/index-v4.yaml" \
    && -f "$HOME/.ros/rosdep/local_sources/20-default.list" ]]; then
    export ROSDEP_SOURCE_PATH="$HOME/.ros/rosdep/local_sources"
    export ROSDISTRO_INDEX_URL="file://$HOME/.ros/rosdistro-local/index-v4.yaml"
fi

_sentinel_dedupe_path_var() {
    local variable_name="$1"
    local original="${!variable_name-}"
    local item rebuilt=""
    local -A seen=()
    IFS=':' read -r -a _sentinel_items <<< "$original"
    for item in "${_sentinel_items[@]}"; do
        [[ -n "$item" ]] || continue
        if [[ -z "${seen[$item]+x}" ]]; then
            seen["$item"]=1
            rebuilt="${rebuilt:+$rebuilt:}$item"
        fi
    done
    printf -v "$variable_name" '%s' "$rebuilt"
    export "$variable_name"
    unset _sentinel_items
}

_sentinel_nounset_was_enabled=0
case $- in
    *u*) _sentinel_nounset_was_enabled=1; set +u ;;
esac

if [[ -r "/opt/ros/$ROS_DISTRO/setup.bash" ]]; then
    # shellcheck disable=SC1090
    source "/opt/ros/$ROS_DISTRO/setup.bash"
else
    echo "WARNING: ROS 2 $ROS_DISTRO environment not installed" >&2
fi

if [[ -r "$SENTINEL_ROS2_WS/install/setup.bash" ]]; then
    # shellcheck disable=SC1090
    source "$SENTINEL_ROS2_WS/install/setup.bash"
else
    echo "WARNING: ROS 2 workspace has not been built yet" >&2
fi

if (( _sentinel_nounset_was_enabled )); then
    set -u
fi

for _sentinel_path_var in PATH PYTHONPATH LD_LIBRARY_PATH; do
    _sentinel_dedupe_path_var "$_sentinel_path_var"
done

unset -f _sentinel_dedupe_path_var
unset sentinel_env_dir sentinel_default_workspace _sentinel_path_var _sentinel_nounset_was_enabled
