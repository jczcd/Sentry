#!/usr/bin/env bash
set -euo pipefail

# 在实际 Sentinel 电脑上运行。
# 生成“可迁移完整源码包”：包含软件仓库 + Isaac/USD 工程，
# 排除 build/install/log/cache 等可重建的大文件，避免把机器相关产物带到新电脑。

STAMP="$(date +%Y%m%d_%H%M%S)"
BASE="${HOME}/RoboMaster/Sentinel"
WORK="${BASE}/SentinelWorkspace/workspace"
SIM="${BASE}/sentinelusd/Sentry_IsaacSim_Linux"
OUT="${HOME}/Sentinel_FULL_SOURCE_${STAMP}.zip"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

[[ -d "$WORK" ]] || { echo "Missing: $WORK"; exit 1; }
[[ -d "$SIM" ]] || { echo "Missing: $SIM"; exit 1; }

mkdir -p "$TMP/SentinelPackage/SentinelWorkspace" "$TMP/SentinelPackage/sentinelusd"

echo "[1/4] Copy workspace..."
rsync -a \
  --exclude='ros2_ws/build/' \
  --exclude='ros2_ws/install/' \
  --exclude='ros2_ws/log/' \
  --exclude='logs/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  "$WORK/" "$TMP/SentinelPackage/SentinelWorkspace/workspace/"

echo "[2/4] Copy Isaac/USD project..."
rsync -a \
  --exclude='logs/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  "$SIM/" "$TMP/SentinelPackage/sentinelusd/Sentry_IsaacSim_Linux/"

echo "[3/4] Record machine report..."
{
  echo "===== SENTINEL MIGRATION REPORT ====="
  date -Is
  uname -a
  echo
  cat /etc/os-release
  echo
  lscpu
  echo
  free -h
  echo
  nvidia-smi || true
  echo
  if [[ -f "$SIM/output/Sentry_stage5c_joint_drives.usda" ]]; then
    sha256sum "$SIM/output/Sentry_stage5c_joint_drives.usda"
  fi
} > "$TMP/SentinelPackage/MACHINE_REPORT.txt" 2>&1

echo "[4/4] Zip..."
(
  cd "$TMP"
  zip -qr "$OUT" SentinelPackage
)

sha256sum "$OUT" | tee "${OUT}.sha256"

echo
echo "DONE:"
echo "$OUT"
echo "${OUT}.sha256"
echo
echo "这个包是源码/配置/当前USD迁移包，不包含 ros2 build/install/log 等可重建缓存。"
