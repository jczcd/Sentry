#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
ROS_THIRD_PARTY="$ROOT/ros2_ws/src/third_party"
FIRMWARE_VENDOR="$ROOT/firmware/vendor"
TRAINING_VENDOR="$ROOT/training"
PATCH="$ROOT/dependencies/patches/livox_ros_driver2-sibling-sdk.patch"

usage() {
  echo "Usage: $0 {ros|training|firmware|all}" >&2
  exit 2
}

die() {
  echo "dependency fetch: ERROR: $*" >&2
  exit 1
}

clone_at() {
  local url="$1" ref="$2" commit="$3" dest="$4"
  if [[ -e "$dest" && ! -d "$dest/.git" ]]; then
    die "$dest exists but is not a Git checkout; move it aside and retry"
  fi
  if [[ ! -e "$dest" ]]; then
    mkdir -p "$(dirname -- "$dest")"
    git clone --no-checkout "$url" "$dest"
  fi
  git -C "$dest" fetch --tags --prune origin "$ref"
  git -C "$dest" cat-file -e "$commit^{commit}" || die "$dest cannot resolve pinned commit $commit"
  local current
  current="$(git -C "$dest" rev-parse HEAD 2>/dev/null || true)"
  if [[ "$current" != "$commit" ]]; then
    if [[ -n "$(git -C "$dest" status --porcelain)" ]]; then
      die "$dest has local changes and is not at pinned commit $commit"
    fi
    git -C "$dest" checkout --detach "$commit"
  fi
}

fetch_ros() {
  clone_at \
    "https://github.com/SMBU-PolarBear-Robotics-Team/point_lio.git" \
    "RM2025_SMBU_auto_sentry" \
    "e85e79558cf746f6699888a54285fe48b3b0ac71" \
    "$ROS_THIRD_PARTY/point_lio"
  clone_at \
    "https://github.com/Livox-SDK/livox_ros_driver2.git" \
    "master" \
    "4a1def929e5b59c7a8122d19fce6efba581ce9f7" \
    "$ROS_THIRD_PARTY/livox_ros_driver2"
  clone_at \
    "https://github.com/Livox-SDK/Livox-SDK2.git" \
    "master" \
    "08f523c930b2f0ba1e98a6afaa8d7476bf479908" \
    "$ROS_THIRD_PARTY/Livox-SDK2"

  if git -C "$ROS_THIRD_PARTY/livox_ros_driver2" apply --reverse --check "$PATCH" >/dev/null 2>&1; then
    echo "livox_ros_driver2: sibling SDK patch already applied"
  elif git -C "$ROS_THIRD_PARTY/livox_ros_driver2" apply --check "$PATCH" >/dev/null 2>&1; then
    git -C "$ROS_THIRD_PARTY/livox_ros_driver2" apply "$PATCH"
    echo "livox_ros_driver2: applied sibling SDK patch"
  else
    die "livox_ros_driver2: sibling SDK patch does not apply cleanly"
  fi
  touch "$ROS_THIRD_PARTY/Livox-SDK2/COLCON_IGNORE"
}

fetch_training() {
  clone_at \
    "https://github.com/Harkerbest/RMUC-OfflineRL.git" \
    "f0d54521caa5b5701665b97f87df309ab2ed8f87" \
    "f0d54521caa5b5701665b97f87df309ab2ed8f87" \
    "$TRAINING_VENDOR/RMUC-OfflineRL"
}

fetch_firmware() {
  clone_at \
    "https://github.com/KaminDeng/dp_sdk_core.git" \
    "master" \
    "9ba1a81a7bd9b7c7a89baccba7d1f53dbe3d52ee" \
    "$FIRMWARE_VENDOR/dp_sdk_core"
}

case "${1:-}" in
  ros) fetch_ros ;;
  training) fetch_training ;;
  firmware) fetch_firmware ;;
  all) fetch_ros; fetch_training; fetch_firmware ;;
  *) usage ;;
esac

echo "dependency fetch: OK"
