#!/usr/bin/env bash
set -Eeuo pipefail

EXPECTED_STAGE5C_SHA256="${EXPECTED_STAGE5C_SHA256:-ffa8ecbf83a047f05cc1e4aeb3005b1fa8c09da651c273bb4a4d03a62a0dcacc}"

usage() {
  printf 'Usage: %s /path/to/Sentinel_IsaacSim_Stage5D_*.tar.gz\n' "$0"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -ne 1 ]]; then
  usage >&2
  exit 64
fi

archive_path="$1"
checksum_path="${archive_path}.sha256"

if [[ ! -f "$archive_path" ]]; then
  printf 'ERROR: archive not found: %s\n' "$archive_path" >&2
  exit 66
fi

gzip -t "$archive_path"

if [[ -f "$checksum_path" ]]; then
  (
    cd "$(dirname "$archive_path")"
    sha256sum -c "$(basename "$checksum_path")"
  )
else
  printf 'WARNING: checksum sidecar not found: %s\n' "$checksum_path" >&2
fi

required_entries=(
  'SentinelMigration/SentinelWorkspace/workspace/'
  'SentinelMigration/sentinelusd/Sentry_IsaacSim_Linux/'
  'SentinelMigration/sentinelusd/Sentry_IsaacSim_Linux/output/Sentry_stage5c_joint_drives.usda'
  'SentinelMigration/sentinelusd/Sentry_IsaacSim_Linux/output/Sentry_stage5d_swerve.usda'
  'SentinelMigration/sentinelusd/Sentry_IsaacSim_Linux/output/stage5d_runtime_report.json'
  'SentinelMigration/metadata/MIGRATION_INFO.txt'
)

archive_listing="$(mktemp)"
stage5c_temp="$(mktemp)"
cleanup() {
  rm -f "$archive_listing" "$stage5c_temp"
}
trap cleanup EXIT

tar -tzf "$archive_path" > "$archive_listing"
for required_entry in "${required_entries[@]}"; do
  if ! grep -Fx "$required_entry" "$archive_listing" >/dev/null; then
    printf 'ERROR: required archive entry missing: %s\n' "$required_entry" >&2
    exit 65
  fi
done

tar -xOzf "$archive_path" \
  'SentinelMigration/sentinelusd/Sentry_IsaacSim_Linux/output/Sentry_stage5c_joint_drives.usda' \
  > "$stage5c_temp"
actual_stage5c_sha256="$(sha256sum "$stage5c_temp" | awk '{print $1}')"

if [[ "$actual_stage5c_sha256" != "$EXPECTED_STAGE5C_SHA256" ]]; then
  printf 'ERROR: Stage5C hash in archive does not match protected checkpoint.\n' >&2
  printf 'Expected: %s\n' "$EXPECTED_STAGE5C_SHA256" >&2
  printf 'Actual:   %s\n' "$actual_stage5c_sha256" >&2
  exit 65
fi

printf 'Archive verification PASS.\n'
printf 'Stage5C SHA256: %s\n' "$actual_stage5c_sha256"
