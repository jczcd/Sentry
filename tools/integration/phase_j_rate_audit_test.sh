#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(cd "$DIR/../.." && pwd)"
# shellcheck disable=SC1091
source "$DIR/sentinel_env.sh"
sentinel_require_approved_usd
OUT="$SENTINEL_ISAAC_INTEGRATION/output"; LOG="$ROOT/logs"; REPORT="$OUT/phase_j_rate_audit.json"
mkdir -p "$OUT" "$LOG"; rm -f "$REPORT"
PIDS=(); cleanup(){ for p in "${PIDS[@]}"; do kill "$p" 2>/dev/null || true; done; for p in "${PIDS[@]}"; do wait "$p" 2>/dev/null || true; done; }; trap cleanup EXIT INT TERM
python3 "$DIR/phase_j_rate_audit.py" --output "$REPORT" --simulation-seconds 5 >"$LOG/phase_j_rate_audit.log" 2>&1 & OBS=$!; PIDS+=($OBS)
PYTHONUNBUFFERED=1 "$ISAAC_SIM_PYTHON" "$SENTINEL_ISAAC_INTEGRATION/scripts/launch_stage.py" --stage "$SENTRY_USD_PATH" --headless --enable-state-publishers --enable-sensors --disable-legacy-scan --pointcloud-rate-hz 30 --sensor-config "$SENTINEL_ISAAC_INTEGRATION/config/phase_i_sensors.json" >"$LOG/phase_j_rate_isaac.log" 2>&1 & ISAAC=$!; PIDS+=($ISAAC)
deadline=$((SECONDS+180)); while ((SECONDS<deadline)); do
  if ! kill -0 "$ISAAC" 2>/dev/null; then
    set +e
    wait "$ISAAC"
    isaac_status=$?
    set -e
    echo "Isaac exited before rate evidence; status=$isaac_status"
    echo "RESULT: FAIL"
    exit 1
  fi
  kill -0 "$OBS" 2>/dev/null || break
  sleep 1
done
[[ -f "$REPORT" ]] || { echo "RESULT: FAIL"; exit 1; }
python3 - "$REPORT" <<'PY'
import json,sys
r=json.load(open(sys.argv[1])); print(json.dumps(r,indent=2))
ok=(r['lidar_rate_sim_hz'] >= 7.0 and r['imu_rate_sim_hz'] >= 25.0 and
    r['imu_duplicate_timestamps'] == 0)
sys.exit(0 if ok else 1)
PY
