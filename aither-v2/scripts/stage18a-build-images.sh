#!/usr/bin/env bash
# Stage 18A — Build Aither service images with immutable tags
# Usage: ./scripts/stage18a-build-images.sh [registry_host]
#   registry_host: target registry (default: 127.0.0.1:5000)
set -euo pipefail

REGISTRY="${1:-127.0.0.1:5000}"
GIT_SHA="${2:-$(git rev-parse --short HEAD)}"
TAG="stage18a-${GIT_SHA}"

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "[build] Building images with tag: ${TAG}"
echo "[build] Target registry: ${REGISTRY}"

# Build identity
echo "[build] Building aither-identity..."
docker build \
  -t "${REGISTRY}/aither-identity:${TAG}" \
  -f services/identity/Dockerfile \
  services/identity/

# Build portal-backend
echo "[build] Building aither-portal-backend..."
docker build \
  -t "${REGISTRY}/aither-portal-backend:${TAG}" \
  -f services/portal-backend/Dockerfile \
  services/portal-backend/

# Build ai-platform
echo "[build] Building aither-ai-platform..."
docker build \
  -t "${REGISTRY}/aither-ai-platform:${TAG}" \
  -f services/ai-platform/Dockerfile \
  services/ai-platform/

echo "[build] All images built successfully."
echo "[build] Tags: ${TAG}"

# Verify ownership in images
echo "[build] Verifying UID ownership..."
for img in aither-identity aither-portal-backend aither-ai-platform; do
  echo "[build]   ${img}: $(docker run --rm "${REGISTRY}/${img}:${TAG}" id 2>/dev/null || echo 'UID check skipped')"
done

echo "[build] Done."
