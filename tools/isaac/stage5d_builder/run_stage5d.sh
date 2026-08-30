#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for f in \
  "$ROOT/output/Sentry_stage5c_joint_drives.usda" \
  "$ROOT/output/stage4_report.json" \
  "$ROOT/output/stage5b_preflight.json" \
  "$ROOT/config/stage5d_swerve.json"; do
  if [[ ! -f "$f" ]]; then
    echo "[ERROR] Required file not found: $f" >&2
    exit 2
  fi
done

find_isaac_python() {
  if [[ -n "${ISAAC_SIM_PYTHON:-}" && -x "${ISAAC_SIM_PYTHON}" ]]; then
    echo "$ISAAC_SIM_PYTHON"; return 0
  fi
  if [[ -n "${ISAAC_SIM_PATH:-}" && -x "${ISAAC_SIM_PATH}/python.sh" ]]; then
    echo "${ISAAC_SIM_PATH}/python.sh"; return 0
  fi
  if [[ -x "$HOME/issac-sim/isaac-sim/python.sh" ]]; then
    echo "$HOME/issac-sim/isaac-sim/python.sh"; return 0
  fi
  return 1
}

PYTHON_CMD="$(find_isaac_python || true)"
if [[ -z "$PYTHON_CMD" ]]; then
  echo "[ERROR] Isaac Sim python.sh not found." >&2
  exit 2
fi

mkdir -p "$ROOT/logs" "$ROOT/output"

echo "============================================================"
echo " Stage 5D ONE-COMMAND"
echo " 4-Swerve Calibration + Ground Motion Validation"
echo "============================================================"
echo "[INFO] Isaac Python: $PYTHON_CMD"

if [[ "${1:-}" == "--dry-run" ]]; then
  echo "[DRY-RUN] Validating Stage5C input, wheel colliders and Stage5B radius..."
  "$PYTHON_CMD" "$ROOT/scripts/stage5d_build_swerve.py" --dry-run \
    2>&1 | tee "$ROOT/logs/stage5d_build.log"
  exit ${PIPESTATUS[0]}
fi

echo
echo "[STEP 1/2] Building Stage5D friction/gain overlay..."
"$PYTHON_CMD" "$ROOT/scripts/stage5d_build_swerve.py" \
  2>&1 | tee "$ROOT/logs/stage5d_build.log"
BUILD_RC=${PIPESTATUS[0]}
if [[ "$BUILD_RC" -ne 0 ]]; then
  echo "[FATAL] Stage5D build failed; runtime test will not run." >&2
  exit "$BUILD_RC"
fi

echo
echo "[STEP 2/2] Auto-calibrating four swerve modules and running ground motion tests..."
set +e
"$PYTHON_CMD" "$ROOT/scripts/stage5d_runtime_swerve_test.py" \
  2>&1 | tee "$ROOT/logs/stage5d_runtime.log"
RUNTIME_RC=${PIPESTATUS[0]}
set -e

REPORT="$ROOT/output/stage5d_runtime_report.json"
if [[ ! -f "$REPORT" ]]; then
  echo "[FAIL] Stage5D runtime report was not generated." >&2
  exit 1
fi

set +e
python3 - "$REPORT" <<'PY'
import json, sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
    d = json.load(f)
ok = (
    d.get("runtime_validation_all_pass") is True
    and int(d.get("pass_count", -1)) == int(d.get("expected_count", -2))
    and int(d.get("expected_count", 0)) == 4
)
print(
    f"[GATE] motion cases={d.get('pass_count')}/{d.get('expected_count')}, "
    f"runtime_validation_all_pass={d.get('runtime_validation_all_pass')}"
)
sys.exit(0 if ok else 1)
PY
REPORT_RC=$?
set -e

if [[ "$REPORT_RC" -ne 0 ]]; then
  echo
  echo "============================================================"
  echo "[FAIL] STAGE 5D NOT COMPLETE"
  echo "[FAIL] One or more motion cases failed."
  echo "[FAIL] Inspect: output/stage5d_runtime_report.json"
  echo "[FAIL] Do not proceed to ROS2 cmd_vel yet."
  echo "============================================================"
  exit 1
fi

echo
echo "============================================================"
echo "[OK] STAGE 5D COMPLETE"
echo "[OK] Auto steer calibration: PASS"
echo "[OK] Straight / lateral / diagonal / rotate: 4/4 PASS"
echo "[OK] Output: output/Sentry_stage5d_swerve.usda"
echo "============================================================"
