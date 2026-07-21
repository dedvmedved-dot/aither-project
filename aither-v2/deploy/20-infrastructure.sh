#!/usr/bin/env bash
# Aither / AI Hermes MVP — Automated Deployment
# Stage 20: Infrastructure — Namespaces, ServiceAccounts, PVCs, Config
#
# Creates base infrastructure resources that services depend on.
# Idempotent: uses kubectl apply for all resources.
#
# Exit codes:
#   0 — all infrastructure created/verified
#   1 — one or more resources failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG="${SCRIPT_DIR}/deploy.log"

echo "[20-infrastructure] Starting infrastructure setup..." | tee -a "${LOG}"

PASS=0
FAIL=0

# --- Namespace ---
echo "[20-infrastructure] Creating namespace aither-inference..." | tee -a "${LOG}"
cat <<'EOF' | kubectl apply -f - 2>&1 | tee -a "${LOG}"
apiVersion: v1
kind: Namespace
metadata:
  name: aither-inference
EOF
if [ "${PIPESTATUS[0]}" -eq 0 ]; then
  echo "  PASS: Namespace aither-inference ready" | tee -a "${LOG}"
  PASS=$((PASS + 1))
else
  echo "  FAIL: Namespace creation failed" | tee -a "${LOG}"
  FAIL=$((FAIL + 1))
fi

# --- ServiceAccount ---
echo "[20-infrastructure] Creating ServiceAccount vllm-sa..." | tee -a "${LOG}"
if [ -f "${PROJECT_ROOT}/03-vllm-14b-deploy/manifests/vllm-sa.yaml" ]; then
  kubectl apply -f "${PROJECT_ROOT}/03-vllm-14b-deploy/manifests/vllm-sa.yaml" 2>&1 | tee -a "${LOG}"
  echo "  PASS: ServiceAccount vllm-sa applied" | tee -a "${LOG}"
  PASS=$((PASS + 1))
else
  echo "  WARN: vllm-sa.yaml not found — skipping" | tee -a "${LOG}"
fi

# --- RuntimeClass ---
echo "[20-infrastructure] Creating RuntimeClass nvidia..." | tee -a "${LOG}"
if [ -f "${PROJECT_ROOT}/02-containerd-nvidia-runtime/manifests/runtimeclass-nvidia.yaml" ]; then
  kubectl apply -f "${PROJECT_ROOT}/02-containerd-nvidia-runtime/manifests/runtimeclass-nvidia.yaml" 2>&1 | tee -a "${LOG}"
  echo "  PASS: RuntimeClass nvidia applied" | tee -a "${LOG}"
  PASS=$((PASS + 1))
else
  echo "  WARN: runtimeclass-nvidia.yaml not found — skipping" | tee -a "${LOG}"
fi

# --- Model PVC ---
echo "[20-infrastructure] Creating PersistentVolumeClaim model-storage..." | tee -a "${LOG}"
if [ -f "${PROJECT_ROOT}/03-vllm-14b-deploy/manifests/model-pvc.yaml" ]; then
  kubectl apply -f "${PROJECT_ROOT}/03-vllm-14b-deploy/manifests/model-pvc.yaml" 2>&1 | tee -a "${LOG}"
  echo "  PASS: PVC model-storage applied" | tee -a "${LOG}"
  PASS=$((PASS + 1))
else
  echo "  WARN: model-pvc.yaml not found — skipping" | tee -a "${LOG}"
fi

# --- Identity PVC ---
echo "[20-infrastructure] Creating PersistentVolumeClaim aither-identity-data..." | tee -a "${LOG}"
if [ -f "${PROJECT_ROOT}/services/identity/k8s/identity.yaml" ]; then
  # Extract and apply only the PVC from identity.yaml
  python3 -c "
import yaml
for doc in yaml.safe_all(open('${PROJECT_ROOT}/services/identity/k8s/identity.yaml')):
    if doc and doc.get('kind') == 'PersistentVolumeClaim':
        print(yaml.dump(doc))
" 2>/dev/null | kubectl apply -f - 2>&1 | tee -a "${LOG}"
  echo "  PASS: PVC aither-identity-data applied" | tee -a "${LOG}"
  PASS=$((PASS + 1))
else
  echo "  WARN: identity.yaml not found — skipping Identity PVC" | tee -a "${LOG}"
fi

# --- AI Platform PVC ---
echo "[20-infrastructure] Creating PersistentVolumeClaim aither-ai-platform-data..." | tee -a "${LOG}"
if [ -f "${PROJECT_ROOT}/services/ai-platform/k8s/ai-platform.yaml" ]; then
  python3 -c "
import yaml
for doc in yaml.safe_all(open('${PROJECT_ROOT}/services/ai-platform/k8s/ai-platform.yaml')):
    if doc and doc.get('kind') == 'PersistentVolumeClaim':
        print(yaml.dump(doc))
" 2>/dev/null | kubectl apply -f - 2>&1 | tee -a "${LOG}"
  echo "  PASS: PVC aither-ai-platform-data applied" | tee -a "${LOG}"
  PASS=$((PASS + 1))
else
  echo "  WARN: ai-platform.yaml not found — skipping AI Platform PVC" | tee -a "${LOG}"
fi

# --- BFF Auth Secret (template only — requires manual REPLACE_ME fill) ---
echo "[20-infrastructure] Checking BFF auth secret..." | tee -a "${LOG}"
if kubectl get secret aither-bff-auth -n aither-inference &>/dev/null; then
  echo "  PASS: Secret aither-bff-auth already exists" | tee -a "${LOG}"
  PASS=$((PASS + 1))
else
  echo "  WARN: Secret aither-bff-auth does not exist." | tee -a "${LOG}"
  echo "  WARN: Create it manually from manifests/mvp-roadmap/07-auth-api/bff-auth-secret.example.yaml" | tee -a "${LOG}"
  echo "  WARN: Replace all REPLACE_ME values before deployment." | tee -a "${LOG}"
fi

# --- Summary ---
echo "" | tee -a "${LOG}"
echo "[20-infrastructure] ========================================" | tee -a "${LOG}"
echo "[20-infrastructure]  Passed: ${PASS}  Failed: ${FAIL}" | tee -a "${LOG}"
echo "[20-infrastructure] ========================================" | tee -a "${LOG}"

if [ "${FAIL}" -gt 0 ]; then
  echo "[20-infrastructure] FAILED: ${FAIL} resource(s) failed." | tee -a "${LOG}"
  exit 1
fi

echo "[20-infrastructure] PASSED" | tee -a "${LOG}"
exit 0
