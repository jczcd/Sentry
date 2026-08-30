#!/usr/bin/env bash
set -Eeuo pipefail

target_root="${1:-$HOME/robomaster/space/Sentinel_work}"
workspace="$target_root/SentinelWorkspace/workspace"
usd_project="$target_root/sentinelusd/Sentry_IsaacSim_Linux"

printf '===== SENTINEL 4090 HOST CHECK =====\n'
printf 'Time: %s\n' "$(date -Is)"
printf 'User: %s\n' "$(whoami)"
printf 'HOME: %s\n' "$HOME"
printf 'Target: %s\n' "$target_root"

printf '\n===== OS =====\n'
if [[ -f /etc/os-release ]]; then
  cat /etc/os-release
fi
uname -a

printf '\n===== GPU =====\n'
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
else
  printf 'nvidia-smi: MISSING\n'
fi

printf '\n===== STORAGE =====\n'
df -hT /
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS

printf '\n===== ISAAC SIM CANDIDATES =====\n'
found_isaac=0
report_isaac_candidate() {
  local launcher="$1"
  local install_root
  local version_file

  install_root="$(dirname "$launcher")"
  printf 'Launcher: %s\n' "$launcher"
  for version_file in \
    "$install_root/VERSION" \
    "$install_root/VERSION.txt" \
    "$install_root/version.txt" \
    "$install_root/build_info.json"
  do
    if [[ -f "$version_file" ]]; then
      printf 'Version metadata: %s\n' "$version_file"
      sed -n '1,20p' "$version_file" 2>/dev/null || true
    fi
  done
}

for candidate in \
  "$HOME/issac-sim/isaac-sim/isaac-sim.sh" \
  "$HOME/isaac-sim/isaac-sim/isaac-sim.sh" \
  "/opt/issac-sim/isaac-sim/isaac-sim.sh" \
  "/opt/isaac-sim/isaac-sim.sh"
do
  if [[ -f "$candidate" ]]; then
    report_isaac_candidate "$candidate"
    found_isaac=1
  fi
done
if [[ "$found_isaac" -eq 0 ]]; then
  while IFS= read -r candidate; do
    report_isaac_candidate "$candidate"
    found_isaac=1
  done < <(find "$HOME" /opt -maxdepth 5 -type f -name 'isaac-sim.sh' -print 2>/dev/null || true)
fi
if [[ "$found_isaac" -eq 0 ]]; then
  printf 'Isaac Sim launcher: NOT FOUND\n'
fi

printf '\n===== DEVELOPMENT TOOLS =====\n'
for command_name in git python3 cmake colcon ros2 docker codex; do
  if command -v "$command_name" >/dev/null 2>&1; then
    printf '%-10s PRESENT: %s\n' "$command_name" "$(command -v "$command_name")"
  else
    printf '%-10s MISSING\n' "$command_name"
  fi
done
if command -v codex >/dev/null 2>&1; then
  codex --version 2>&1 || true
fi

printf '\n===== PROJECT =====\n'
for required_path in \
  "$workspace" \
  "$workspace/tools/integration/run_sentinel_gui.sh" \
  "$workspace/tools/integration/sentry_teleop.sh" \
  "$usd_project/output/Sentry_stage5c_joint_drives.usda" \
  "$usd_project/output/Sentry_stage5d_swerve.usda"
do
  if [[ -e "$required_path" ]]; then
    printf 'PRESENT: %s\n' "$required_path"
  else
    printf 'MISSING: %s\n' "$required_path"
  fi
done

stage5c="$usd_project/output/Sentry_stage5c_joint_drives.usda"
if [[ -f "$stage5c" ]]; then
  printf '\nStage5C SHA256:\n'
  sha256sum "$stage5c"
fi

printf '\n===== COMPATIBILITY NOTE =====\n'
version_id=""
if [[ -f /etc/os-release ]]; then
  version_id="$(. /etc/os-release; printf '%s' "${VERSION_ID:-}")"
fi
if [[ "$version_id" == "22.04" ]]; then
  printf 'Ubuntu 22.04 detected. Original Sentinel baseline is Ubuntu 24.04 + ROS 2 Jazzy.\n'
  printf 'Do not assume /opt/ros/jazzy exists. Use the NVIDIA Ubuntu 22.04/Jazzy Docker or source-build path.\n'
else
  printf 'Ubuntu version: %s\n' "${version_id:-unknown}"
fi
