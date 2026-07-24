#!/usr/bin/env bash
# Stage 18A — Deploy all Aither services to Kubernetes
# Usage: ./scripts/stage18a-deploy-services.sh
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"
NAMESPACE="${NAMESPACE:-aither-inference}"
MANIFESTS=(
  "services/identity/k8s/identity.yaml"
  "services/portal-backend/k8s/portal-backend.yaml"
  "services/ai-platform/k8s/ai-platform.yaml"
)

# ── Preflight checks ──

echo "[deploy] Running preflight checks..."

# Check kubectl exists
if ! command -v kubectl &>/dev/null; then
  echo "[deploy] ERROR: kubectl not found in PATH"
  exit 1
fi

# Show current context
echo "[deploy] Current kubectl context: $(kubectl config current-context 2>&1 || echo 'UNAVAILABLE')"

# Check cluster reachable
if ! kubectl cluster-info --request-timeout=5s 2>&1 | head -1 >/dev/null; then
  echo "[deploy] ERROR: Kubernetes cluster is not reachable"
  exit 1
fi

# Check namespace exists
if ! kubectl get namespace "${NAMESPACE}" &>/dev/null; then
  echo "[deploy] ERROR: Namespace '${NAMESPACE}' does not exist"
  exit 1
fi

# Check required Secret exists
if ! kubectl get secret aither-identity-secret -n "${NAMESPACE}" &>/dev/null; then
  echo "[deploy] ERROR: Secret 'aither-identity-secret' not found in namespace '${NAMESPACE}'"
  echo "[deploy]   Create it from services/identity/k8s/identity-secret.example.yaml"
  echo "[deploy]   DO NOT commit or apply the example file with placeholder values."
  exit 1
fi

# Check manifest files exist
for mf in "${MANIFESTS[@]}"; do
  if [ ! -f "${mf}" ]; then
    echo "[deploy] ERROR: Manifest file not found: ${mf}"
    exit 1
  fi
done

echo "[deploy] Preflight checks passed."
echo ""

# ── Deploy ──

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

DEPLOYMENTS=("aither-identity" "aither-portal-backend" "aither-ai-platform")
ROLLOUT_FAILED=0

for dep in "${DEPLOYMENTS[@]}"; do
  echo "[deploy]   Waiting for ${dep}..."
  if ! kubectl rollout status "deployment/${dep}" -n "${NAMESPACE}" --timeout=120s; then
    echo "[deploy]   ERROR: Rollout failed for ${dep}"
    echo "[deploy]   --- Deployment status ---"
    kubectl get deployment "${dep}" -n "${NAMESPACE}" -o wide 2>&1 || true
    echo "[deploy]   --- Pod status ---"
    kubectl get pods -n "${NAMESPACE}" -l "app=${dep}" -o wide 2>&1 || true
    ROLLOUT_FAILED=1
  fi
done

if [ "${ROLLOUT_FAILED}" -eq 1 ]; then
  echo "[deploy] ERROR: One or more rollouts failed. Exiting."
  exit 1
fi

echo ""
echo "[deploy] Pod status:"
kubectl get pods -n "${NAMESPACE}" -o wide | grep -E "aither-identity|aither-portal-backend|aither-ai-platform"

echo "[deploy] Done."
