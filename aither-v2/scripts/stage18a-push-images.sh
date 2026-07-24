#!/usr/bin/env bash
# Stage 18A — Import and push images into persistent registry on n8
# Usage: ./scripts/stage18a-push-images.sh [n8_host] [registry_port]
set -Eeuo pipefail

N8_HOST="${1:-10.129.13.78}"
REGISTRY="${2:-localhost:5000}"
SSH_KEY="${3:-}"
SSH_OPTS="-o ConnectTimeout=30 -o ServerAliveInterval=15 -o ServerAliveCountMax=3"
[ -n "$SSH_KEY" ] && SSH_OPTS="${SSH_OPTS} -i ${SSH_KEY}"

SOURCE_DIR="/tmp/stage18e"
IMG_LIST="aither-identity aither-portal-backend aither-ai-platform"
TAG="${3:-stage18a-82fe433}"

echo "[push] Importing images into containerd on ${N8_HOST}..."
for img in ${IMG_LIST}; do
  echo "[push]   Importing ${img}..."
  ssh ${SSH_OPTS} "root@${N8_HOST}" \
    "zstd -dc ${SOURCE_DIR}/${img}.tar.zst | sudo ctr -n k8s.io images import -"
done

echo "[push] Tagging and pushing to registry ${REGISTRY}..."
for img in ${IMG_LIST}; do
  echo "[push]   Processing ${img}:${TAG}..."
  ssh ${SSH_OPTS} "root@${N8_HOST}" \
    "sudo ctr -n k8s.io images tag ${img}:${TAG} ${REGISTRY}/${img}:${TAG} && \
     sudo ctr -n k8s.io images push --plain-http ${REGISTRY}/${img}:${TAG}"
done

echo "[push] Verifying registry catalog..."
ssh ${SSH_OPTS} "root@${N8_HOST}" \
  "curl -fsS http://${REGISTRY}/v2/_catalog"

echo "[push] Done."
