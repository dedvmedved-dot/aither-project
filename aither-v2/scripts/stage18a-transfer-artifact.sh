#!/usr/bin/env bash
# Stage 18A — Transfer images to n8 via rsync + SSH
# Usage: ./scripts/stage18a-transfer-artifact.sh <source_host> <dest_host>
#   source_host: build host SSH hostname/IP
#   dest_host: target node SSH hostname/IP (default: n8)
set -euo pipefail

SOURCE="${1:-build-host}"
DEST="${2:-n8}"
SSH_KEY="${3:-}"
SSH_OPTS="-o ConnectTimeout=30 -o ServerAliveInterval=15 -o ServerAliveCountMax=3"
[ -n "$SSH_KEY" ] && SSH_OPTS="${SSH_OPTS} -i ${SSH_KEY}"

DEST_DIR="/tmp/stage18e"
IMG_LIST="aither-identity aither-portal-backend aither-ai-platform"

echo "[transfer] Preparing image archives on ${SOURCE}..."
for img in ${IMG_LIST}; do
  echo "[transfer]   Saving ${img}..."
  docker save "${img}:stage18a-$(git rev-parse --short HEAD)" | \
    zstd -19 -T0 -o "/tmp/stage18e/${img}.tar.zst"
done

echo "[transfer] Transferring to ${DEST}..."
rsync --partial --append-verify \
  --progress \
  --timeout=180 \
  -e "ssh ${SSH_OPTS}" \
  /tmp/stage18e/*.tar.zst \
  "${DEST}:${DEST_DIR}/"

echo "[transfer] Verifying SHA-256 on destination..."
for img in ${IMG_LIST}; do
  SHA_SRC=$(sha256sum "/tmp/stage18e/${img}.tar.zst" | cut -d' ' -f1)
  SHA_DST=$(ssh ${SSH_OPTS} "${DEST}" "sha256sum ${DEST_DIR}/${img}.tar.zst" | cut -d' ' -f1)
  if [ "${SHA_SRC}" = "${SHA_DST}" ]; then
    echo "[transfer]   ${img}: SHA-256 MATCH"
  else
    echo "[transfer]   ${img}: SHA-256 MISMATCH!"
    exit 1
  fi
done

echo "[transfer] Done."
