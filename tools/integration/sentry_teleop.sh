#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/sentinel_env.sh"
exec python3 "$DIR/sentry_teleop.py" "$@"
