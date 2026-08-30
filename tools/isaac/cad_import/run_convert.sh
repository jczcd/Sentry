#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

find_isaac_python() {
  if [[ -n "${ISAAC_SIM_PYTHON:-}" && -x "${ISAAC_SIM_PYTHON}" ]]; then
    echo "$ISAAC_SIM_PYTHON"; return 0
  fi
  if [[ -n "${ISAAC_SIM_PATH:-}" && -x "${ISAAC_SIM_PATH}/python.sh" ]]; then
    echo "${ISAAC_SIM_PATH}/python.sh"; return 0
  fi
  for p in \
    "$HOME/isaacsim/python.sh" \
    "$HOME/isaac-sim/python.sh" \
    "/opt/isaacsim/python.sh" \
    "/isaac-sim/python.sh"; do
    [[ -x "$p" ]] && { echo "$p"; return 0; }
  done
  # Older Omniverse Launcher-style installs.
  local p
  p=$(find "$HOME/.local/share/ov/pkg" -maxdepth 2 -name python.sh -path '*isaac*' -type f 2>/dev/null | sort -V | tail -n 1 || true)
  [[ -n "$p" ]] && { echo "$p"; return 0; }
  # Pip/venv install fallback.
  if python -c 'import isaacsim' >/dev/null 2>&1; then
    command -v python; return 0
  fi
  return 1
}

PYTHON_CMD="$(find_isaac_python || true)"
if [[ -z "$PYTHON_CMD" ]]; then
  cat >&2 <<EOF
[ERROR] Isaac Sim Python environment not found.
Set one of:
  export ISAAC_SIM_PATH=/path/to/isaac-sim
or
  export ISAAC_SIM_PYTHON=/path/to/isaac-sim/python.sh
Then run this script again.
EOF
  exit 2
fi

echo "[INFO] Isaac Python: $PYTHON_CMD"
echo "[1/2] Converting STEP -> USD ..."
"$PYTHON_CMD" "$ROOT/scripts/convert_cad.py" "$@" 2>&1 | tee "$ROOT/logs/convert.log"
echo "[2/2] Inspecting semantic links ..."
"$PYTHON_CMD" "$ROOT/scripts/inspect_links.py" 2>&1 | tee "$ROOT/logs/inspect_links.log"

echo
echo "Done. Open this file in Isaac Sim:"
echo "  $ROOT/output/Sentry.usda"
