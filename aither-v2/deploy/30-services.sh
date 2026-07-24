#!/usr/bin/env bash
# Aither / AI Hermes MVP — Automated Deployment
# Stage 30: Services — Deploy MVP Application Manifests
#
# Applies all Kubernetes manifests in the correct dependency order.
# Idempotent: uses kubectl apply for all resources.
#
# Dependency order:
#   1. vLLM model deployment (foundation service)
#   2. Network policies
#   3. Gateway (depends on vLLM)
#   4. Redis rate limiting
#   5. BFF backend
#   6. Portal frontend
#   7. Benchmark/test manifests (optional)
#
# Exit codes:
#   0 — all services deployed/verified
#   1 — one or more services failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG="${SCRIPT_DIR}/deploy.log"

echo "[30-services] Starting service deployment..." | tee -a "${LOG}"

PASS=0
FAIL=0
WARN=0

# --- Helper: apply manifest with dependency label ---
apply_manifest() {
  local file="$1"
  local description="$2"

  if [ ! -f "${file}" ]; then
    echo "  WARN: ${description} — manifest not found at ${file}" | tee -a "${LOG}"
    WARN=$((WARN + 1))
    return 0
  fi

  echo "  Applying: ${description} (${file})..." | tee -a "${LOG}"
  if kubectl apply -f "${file}" 2>&1 | tee -a "${LOG}"; then
    echo "    PASS: ${description} applied" | tee -a "${LOG}"
    PASS=$((PASS + 1))
  else
    local exit_code=$?
    echo "    FAIL: ${description} failed (exit ${exit_code})" | tee -a "${LOG}"
    FAIL=$((FAIL + 1))
  fi
}

# === Order 1: vLLM Service ===
echo "[30-services] === Phase 1: vLLM Inference Services ===" | tee -a "${LOG}"

# vLLM network policy first (defines ingress rules)
apply_manifest \
  "${PROJECT_ROOT}/03-vllm-14b-deploy/manifests/vllm-network-policy.yaml" \
  "vLLM NetworkPolicy"

# vLLM service (ClusterIP)
apply_manifest \
  "${PROJECT_ROOT}/03-vllm-14b-deploy/manifests/vllm-service.yaml" \
  "vLLM Service"

# vLLM deployment (the model itself)
apply_manifest \
  "${PROJECT_ROOT}/03-vllm-14b-deploy/manifests/vllm-deployment.yaml" \
  "vLLM Deployment"

# === Order 2: Gateway ===
echo "[30-services] === Phase 2: Gateway ===" | tee -a "${LOG}"

apply_manifest \
  "${PROJECT_ROOT}/manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml" \
  "Gateway (nginx-gateway-32b)"

# === Order 3: Redis Rate Limiting ===
echo "[30-services] === Phase 3: Redis Rate Limiting ===" | tee -a "${LOG}"

apply_manifest \
  "${PROJECT_ROOT}/manifests/mvp-roadmap/06-rate-limiting/redis-rate-limit.yaml" \
  "Redis Rate Limiting"

# === Order 4: Identity Service ===
echo "[30-services] === Phase 4: Identity Service (Stage 15) ===" | tee -a "${LOG}"

apply_manifest \
  "${PROJECT_ROOT}/services/identity/k8s/identity.yaml" \
  "Identity Service"

# === Order 5: Portal Backend ===

# === Order 5: Portal Backend (BFF) ===
echo "[30-services] === Phase 5: Portal Backend (BFF) ===" | tee -a "${LOG}"

apply_manifest \
  "${PROJECT_ROOT}/services/portal-backend/k8s/portal-backend.yaml" \
  "Portal Backend (BFF)"

# === Order 6: Portal Frontend ===
echo "[30-services] === Phase 6: Portal Frontend ===" | tee -a "${LOG}"

apply_manifest \
  "${PROJECT_ROOT}/services/portal-frontend/k8s/portal-frontend.yaml" \
  "Portal Frontend"

# === Order 7: AI Platform Service ===
echo "[30-services] === Phase 7: AI Platform (Stage 16) ===" | tee -a "${LOG}"

apply_manifest \
  "${PROJECT_ROOT}/services/ai-platform/k8s/ai-platform.yaml" \
  "AI Platform Service"

# === Order 8: Optional -- Benchmarks & Diagnostics ===
echo "[30-services] === Phase 8: Optional Diagnostics ===" | tee -a "${LOG}"

apply_manifest \
  "${PROJECT_ROOT}/manifests/mvp-roadmap/01-cluster-gpu/gpu-runtime-test.yaml" \
  "GPU Runtime Test (optional)"

apply_manifest \
  "${PROJECT_ROOT}/manifests/mvp-roadmap/02-inference-acceptance/benchmark-smoke.yaml" \
  "Benchmark Smoke (optional)"

apply_manifest \
  "${PROJECT_ROOT}/manifests/mvp-roadmap/02-inference-acceptance/benchmark-streaming-ttft.yaml" \
  "Benchmark Streaming TTFT (optional)"

apply_manifest \
  "${PROJECT_ROOT}/03-vllm-14b-deploy/manifests/benchmark-job.yaml" \
  "Benchmark Job (optional)"

# --- Pod readiness check (Gateway + vLLM) ---
echo "[30-services] Waiting for critical pods to be ready..." | tee -a "${LOG}"

for deployment in "vllm-14b-instruct" "nginx-gateway-32b" "aither-redis-rate-limit" "aither-identity" "aither-portal-backend" "aither-portal-frontend" "aither-ai-platform"; do
  if kubectl rollout status deployment/"${deployment}" -n aither-inference --timeout=120s 2>&1 | tee -a "${LOG}"; then
    echo "  PASS: ${deployment} is ready" | tee -a "${LOG}"
    PASS=$((PASS + 1))
  else
    echo "  WARN: ${deployment} rollout not completed within timeout" | tee -a "${LOG}"
    WARN=$((WARN + 1))
  fi
done

# --- Summary ---
echo "" | tee -a "${LOG}"
echo "[30-services] ========================================" | tee -a "${LOG}"
echo "[30-services]  Passed: ${PASS}  Failed: ${FAIL}  Warnings: ${WARN}" | tee -a "${LOG}"
echo "[30-services] ========================================" | tee -a "${LOG}"

if [ "${FAIL}" -gt 0 ]; then
  echo "[30-services] FAILED: ${FAIL} service(s) failed." | tee -a "${LOG}"
  exit 1
fi

echo "[30-services] PASSED" | tee -a "${LOG}"
exit 0
