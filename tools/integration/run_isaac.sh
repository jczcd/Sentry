#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$script_dir/sentinel_env.sh"

if [[ ! -x "$ISAAC_SIM_PATH/isaac-sim.sh" ]]; then
    echo "ERROR: Isaac Sim launcher is missing or not executable: $ISAAC_SIM_PATH/isaac-sim.sh" >&2
    exit 2
fi
if [[ ! -x "$ISAAC_SIM_PYTHON" ]]; then
    echo "ERROR: Isaac Sim Python is missing or not executable: $ISAAC_SIM_PYTHON" >&2
    exit 2
fi
if [[ "$SENTRY_MODEL_APPROVED" != "1" ]]; then
    echo "ERROR: model gate is closed; set SENTRY_MODEL_APPROVED=1 only after GUI approval" >&2
    exit 2
fi
if [[ -z "$SENTRY_USD_PATH" || ! -f "$SENTRY_USD_PATH" ]]; then
    echo "ERROR: set SENTRY_USD_PATH to an approved USD outside this repository" >&2
    exit 2
fi

if [[ ! -r /opt/ros/jazzy/setup.bash ]]; then
    echo "WARNING: ROS2 Jazzy is not installed; ROS2 Bridge communication cannot currently be verified." >&2
fi

case "${1-}" in
    "")
        mode_args=()
        ;;
    --headless)
        mode_args=(--headless)
        ;;
    *)
        echo "Usage: $0 [--headless]" >&2
        exit 2
        ;;
esac

exec "$ISAAC_SIM_PYTHON" \
    "$SENTINEL_ISAAC_INTEGRATION/scripts/launch_stage.py" \
    --stage "$SENTRY_USD_PATH" \
    "${mode_args[@]}"
