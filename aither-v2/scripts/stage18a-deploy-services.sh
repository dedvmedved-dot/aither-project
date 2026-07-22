#!/usr/bin/env bash
# Stage 18A — Deploy all Aither services to Kubernetes
# Usage: ./scripts/stage18a-deploy-services.sh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"
NAMESPACE="aither-inference"
MANIFESTS=(
  "services/identity/k8s/identity.yaml"
  "services/portal-backend/k8s/portal-backend.yaml"
  "services/ai-platform/k8s/ai-platform.yaml"
)

echo "[deploy] Dry run — validating manifests..."
for mf in "${MANIFESTS[@]}"; do
  echo "[deploy]   Validating ${mf}..."
  kubectl apply --dry-run=client -f "${mf}"
done

echo ""
echo "[deploy] Diff — showing pending changes..."
for mf in "${MANIFESTS[@]}"; do
  echo "[deploy]   ${mf}:"
  kubectl diff -f "${mf}" 2>&1 || true
done

echo ""
echo "[deploy] Applying manifests..."
for mf in "${MANIFESTS[@]}"; do
  echo "[deploy]   Applying ${mf}..."
  kubectl apply -f "${mf}"
done

echo ""
echo "[deploy] Waiting for rollout..."
for dep in aither-identity aither-portal-backend aither-ai-platform; do
  echo "[deploy]   Waiting for ${dep}..."
  kubectl rollout status "deployment/${dep}" -n "${NAMESPACE}" --timeout=120s || \
    echo "[deploy]   WARNING: ${dep} rollout timed out — check pods manually"
done

echo ""
echo "[deploy] Pod status:"
kubectl get pods -n "${NAMESPACE}" -o wide | grep -E "aither-identity|aither-portal-backend|aither-ai-platform"

echo "[deploy] Done."
