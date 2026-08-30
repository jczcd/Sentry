#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

EXPECTED_STAGE5C_SHA256="${EXPECTED_STAGE5C_SHA256:-ffa8ecbf83a047f05cc1e4aeb3005b1fa8c09da651c273bb4a4d03a62a0dcacc}"
WORKSPACE_ROOT="${SENTRY_WORKSPACE_ROOT:-$HOME/RoboMaster/Sentinel/SentinelWorkspace/workspace}"
USD_PROJECT_ROOT="${SENTRY_USD_PROJECT_ROOT:-$HOME/RoboMaster/Sentinel/sentinelusd/Sentry_IsaacSim_Linux}"
ISAAC_SIM_ROOT="${ISAAC_SIM_ROOT:-$HOME/issac-sim/isaac-sim}"
OUTPUT_DIR="${SENTRY_BUNDLE_OUTPUT_DIR:-$HOME/SentinelTransfer}"

usage() {
  cat <<'EOF'
Usage:
  ./pack_sentinel_5090.sh

Optional environment overrides:
  SENTRY_WORKSPACE_ROOT
  SENTRY_USD_PROJECT_ROOT
  SENTRY_BUNDLE_OUTPUT_DIR
  ISAAC_SIM_ROOT
  EXPECTED_STAGE5C_SHA256

The script is read-only with respect to both source projects. It creates a new
tar.gz archive and sidecar files in the output directory.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -ne 0 ]]; then
  usage >&2
  exit 64
fi

for command_name in tar gzip sha256sum find sed awk date du df mktemp git; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    printf 'ERROR: required command not found: %s\n' "$command_name" >&2
    exit 69
  fi
done

if [[ ! -d "$WORKSPACE_ROOT" ]]; then
  printf 'ERROR: workspace not found: %s\n' "$WORKSPACE_ROOT" >&2
  exit 66
fi

if [[ ! -d "$USD_PROJECT_ROOT" ]]; then
  printf 'ERROR: USD project not found: %s\n' "$USD_PROJECT_ROOT" >&2
  exit 66
fi

if [[ "$(basename "$WORKSPACE_ROOT")" != "workspace" ]]; then
  printf 'ERROR: workspace directory basename must be "workspace": %s\n' "$WORKSPACE_ROOT" >&2
  exit 65
fi

if [[ "$(basename "$USD_PROJECT_ROOT")" != "Sentry_IsaacSim_Linux" ]]; then
  printf 'ERROR: USD project basename must be "Sentry_IsaacSim_Linux": %s\n' "$USD_PROJECT_ROOT" >&2
  exit 65
fi

STAGE5C="$USD_PROJECT_ROOT/output/Sentry_stage5c_joint_drives.usda"
STAGE5D="$USD_PROJECT_ROOT/output/Sentry_stage5d_swerve.usda"
STAGE5D_REPORT="$USD_PROJECT_ROOT/output/stage5d_runtime_report.json"

for required_path in "$STAGE5C" "$STAGE5D" "$STAGE5D_REPORT"; do
  if [[ ! -f "$required_path" ]]; then
    printf 'ERROR: required project file not found: %s\n' "$required_path" >&2
    exit 66
  fi
done

actual_stage5c_sha256="$(sha256sum "$STAGE5C" | awk '{print $1}')"
if [[ "$actual_stage5c_sha256" != "$EXPECTED_STAGE5C_SHA256" ]]; then
  printf 'ERROR: protected Stage5C SHA256 mismatch.\n' >&2
  printf 'Expected: %s\n' "$EXPECTED_STAGE5C_SHA256" >&2
  printf 'Actual:   %s\n' "$actual_stage5c_sha256" >&2
  exit 65
fi

mkdir -p "$OUTPUT_DIR"

case "$OUTPUT_DIR/" in
  "$WORKSPACE_ROOT/"*|"$USD_PROJECT_ROOT/"*)
    printf 'ERROR: output directory must not be inside a source project: %s\n' "$OUTPUT_DIR" >&2
    exit 65
    ;;
esac

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
archive_name="Sentinel_IsaacSim_Stage5D_${timestamp}.tar.gz"
archive_path="$OUTPUT_DIR/$archive_name"
partial_archive="${archive_path}.partial"
checksum_path="${archive_path}.sha256"
contents_path="${archive_path}.contents.txt"

if [[ -e "$archive_path" || -e "$partial_archive" ]]; then
  printf 'ERROR: output already exists: %s\n' "$archive_path" >&2
  exit 73
fi

temp_root="$(mktemp -d)"
cleanup() {
  rm -f "$partial_archive"
  rm -rf "$temp_root"
}
trap cleanup EXIT

metadata_root="$temp_root/SentinelMigration/metadata"
mkdir -p "$metadata_root"

{
  printf 'bundle_format=sentinel-migration-v1\n'
  printf 'created_utc=%s\n' "$timestamp"
  printf 'source_workspace=%s\n' "$WORKSPACE_ROOT"
  printf 'source_usd_project=%s\n' "$USD_PROJECT_ROOT"
  printf 'source_isaac_sim=%s\n' "$ISAAC_SIM_ROOT"
  printf 'stage5c_sha256=%s\n' "$actual_stage5c_sha256"
  printf 'stage5d_sha256=%s\n' "$(sha256sum "$STAGE5D" | awk '{print $1}')"
  printf 'stage5d_report_sha256=%s\n' "$(sha256sum "$STAGE5D_REPORT" | awk '{print $1}')"
  printf 'archive_excludes=ros2_ws/build,ros2_ws/install,ros2_ws/log,firmware/vendor,caches,venvs,node_modules\n'
  printf 'isaac_sim_bundled=false\n'
} > "$metadata_root/MIGRATION_INFO.txt"

{
  printf 'Workspace size before exclusions:\n'
  du -sh "$WORKSPACE_ROOT" 2>&1 || true
  printf '\nUSD project size before exclusions:\n'
  du -sh "$USD_PROJECT_ROOT" 2>&1 || true
  printf '\nOutput filesystem:\n'
  df -h "$OUTPUT_DIR" 2>&1 || true
} > "$metadata_root/SOURCE_SIZES.txt"

{
  printf 'Kernel:\n'
  uname -a
  printf '\nOS release:\n'
  if [[ -f /etc/os-release ]]; then
    sed -n '1,200p' /etc/os-release
  fi
  printf '\nSelected ROS environment:\n'
  printf 'ROS_DISTRO=%s\n' "${ROS_DISTRO:-}"
  printf 'ROS_DOMAIN_ID=%s\n' "${ROS_DOMAIN_ID:-}"
  printf 'RMW_IMPLEMENTATION=%s\n' "${RMW_IMPLEMENTATION:-}"
  printf '\nPython:\n'
  python3 --version 2>&1 || true
  printf '\nCMake:\n'
  cmake --version 2>&1 | sed -n '1,3p' || true
  printf '\nNVIDIA GPU and driver:\n'
  if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>&1 || true
  else
    printf 'nvidia-smi not found\n'
  fi
} > "$metadata_root/ENVIRONMENT.txt"

if command -v dpkg-query >/dev/null 2>&1; then
  dpkg-query -W 'ros-jazzy-*' > "$metadata_root/ROS_JAZZY_PACKAGES.txt" 2>&1 || true
fi

if git -C "$WORKSPACE_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  {
    printf 'HEAD: '
    git -C "$WORKSPACE_ROOT" rev-parse HEAD 2>&1 || true
    printf 'Branch: '
    git -C "$WORKSPACE_ROOT" branch --show-current 2>&1 || true
    printf '\nStatus:\n'
    git -C "$WORKSPACE_ROOT" status --short --branch 2>&1 || true
    printf '\nDiff stat:\n'
    git -C "$WORKSPACE_ROOT" diff --stat 2>&1 || true
    printf '\nSubmodules:\n'
    git -C "$WORKSPACE_ROOT" submodule status --recursive 2>&1 || true
  } > "$metadata_root/WORKSPACE_GIT_STATE.txt"
else
  printf 'Workspace is not a Git worktree.\n' > "$metadata_root/WORKSPACE_GIT_STATE.txt"
fi

{
  printf 'Symlinks are archived as symlinks and are not dereferenced.\n\n'
  find "$WORKSPACE_ROOT" "$USD_PROJECT_ROOT" -type l -printf '%p -> %l\n' 2>&1 || true
} > "$metadata_root/SYMLINKS.txt"

sha256sum "$STAGE5C" "$STAGE5D" "$STAGE5D_REPORT" > "$metadata_root/PROTECTED_FILE_SHA256SUMS.txt"

printf 'Creating migration archive...\n'
tar -czf "$partial_archive" \
  --exclude='workspace/ros2_ws/build' \
  --exclude='workspace/ros2_ws/install' \
  --exclude='workspace/ros2_ws/log' \
  --exclude='workspace/firmware/vendor' \
  --exclude='*/__pycache__' \
  --exclude='*.pyc' \
  --exclude='*.pyo' \
  --exclude='*/.pytest_cache' \
  --exclude='*/.mypy_cache' \
  --exclude='*/.ruff_cache' \
  --exclude='*/.cache' \
  --exclude='*/.venv' \
  --exclude='*/venv' \
  --exclude='*/node_modules' \
  --exclude='*/.idea' \
  --exclude='*.core' \
  --exclude='core.*' \
  --transform='s|^workspace|SentinelMigration/SentinelWorkspace/workspace|' \
  --transform='s|^Sentry_IsaacSim_Linux|SentinelMigration/sentinelusd/Sentry_IsaacSim_Linux|' \
  -C "$(dirname "$WORKSPACE_ROOT")" workspace \
  -C "$(dirname "$USD_PROJECT_ROOT")" Sentry_IsaacSim_Linux \
  -C "$temp_root" SentinelMigration/metadata

gzip -t "$partial_archive"
mv "$partial_archive" "$archive_path"
chmod 600 "$archive_path"

(
  cd "$OUTPUT_DIR"
  sha256sum "$archive_name" > "$(basename "$checksum_path")"
)
tar -tzf "$archive_path" > "$contents_path"
chmod 600 "$checksum_path" "$contents_path"

printf '\nBundle created successfully.\n'
printf 'Archive:  %s\n' "$archive_path"
printf 'Checksum: %s\n' "$checksum_path"
printf 'Contents: %s\n' "$contents_path"
du -h "$archive_path"
