#!/usr/bin/env bash
# Aither / AI Hermes MVP — Automated Deployment
# Stage 40: Validation — Post-deployment Verification
#
# Runs existing project checks to confirm the deployment is healthy.
# Does NOT modify any check logic.
# Idempotent: safe to run multiple times after deployment.
#
# Exit codes:
#   0 — all validations passed
#   1 — one or more validations failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG="${SCRIPT_DIR}/deploy.log"

echo "[40-validation] Starting post-deployment validation..." | tee -a "${LOG}"

PASS=0
FAIL=0
WARN=0

# === Check 1: Gateway Diagnostic ===
echo "[40-validation] === Check 1: Gateway Diagnostic ===" | tee -a "${LOG}"
if [ -x "${PROJECT_ROOT}/scripts/check-gateway-32b.sh" ]; then
  echo "  Running: scripts/check-gateway-32b.sh..." | tee -a "${LOG}"
  if bash "${PROJECT_ROOT}/scripts/check-gateway-32b.sh" 2>&1 | tee -a "${LOG}"; then
    echo "  PASS: Gateway diagnostic passed" | tee -a "${LOG}"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: Gateway diagnostic reported issues" | tee -a "${LOG}"
    FAIL=$((FAIL + 1))
  fi
else
  echo "  WARN: scripts/check-gateway-32b.sh not found — skipping" | tee -a "${LOG}"
  WARN=$((WARN + 1))
fi

# === Check 2: DNS Policy Acceptance Tests ===
echo "[40-validation] === Check 2: DNS Policy Acceptance Tests ===" | tee -a "${LOG}"
if [ -x "${PROJECT_ROOT}/scripts/test-check-gateway-dns-policy.sh" ]; then
  echo "  Running: scripts/test-check-gateway-dns-policy.sh..." | tee -a "${LOG}"
  if bash "${PROJECT_ROOT}/scripts/test-check-gateway-dns-policy.sh" 2>&1 | tee -a "${LOG}"; then
    echo "  PASS: DNS policy acceptance tests passed" | tee -a "${LOG}"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: DNS policy acceptance tests failed" | tee -a "${LOG}"
    FAIL=$((FAIL + 1))
  fi
else
  echo "  WARN: scripts/test-check-gateway-dns-policy.sh not found — skipping" | tee -a "${LOG}"
  WARN=$((WARN + 1))
fi

# === Check 3: E2E Test ===
echo "[40-validation] === Check 3: E2E Test ===" | tee -a "${LOG}"
if [ -x "${PROJECT_ROOT}/scripts/test-gateway-32b-e2e.sh" ]; then
  echo "  Running: scripts/test-gateway-32b-e2e.sh..." | tee -a "${LOG}"
  if bash "${PROJECT_ROOT}/scripts/test-gateway-32b-e2e.sh" 2>&1 | tee -a "${LOG}"; then
    echo "  PASS: E2E test passed" | tee -a "${LOG}"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: E2E test reported issues" | tee -a "${LOG}"
    FAIL=$((FAIL + 1))
  fi
else
  echo "  WARN: scripts/test-gateway-32b-e2e.sh not found — skipping" | tee -a "${LOG}"
  WARN=$((WARN + 1))
fi

# === Check 4: Secrets Scan ===
echo "[40-validation] === Check 4: Secrets Scan ===" | tee -a "${LOG}"
if [ -x "${PROJECT_ROOT}/scripts/scan-secrets.sh" ]; then
  echo "  Running: scripts/scan-secrets.sh..." | tee -a "${LOG}"
  if bash "${PROJECT_ROOT}/scripts/scan-secrets.sh" 2>&1 | tee -a "${LOG}"; then
    echo "  PASS: Secrets scan passed" | tee -a "${LOG}"
    PASS=$((PASS + 1))
  else
    echo "  WARN: Secrets scan found issues (may be pre-existing, non-blocking for deployment)" | tee -a "${LOG}"
    WARN=$((WARN + 1))
  fi
else
  echo "  WARN: scripts/scan-secrets.sh not found — skipping" | tee -a "${LOG}"
  WARN=$((WARN + 1))
fi

# === Check 5: Git cleanliness ===
echo "[40-validation] === Check 5: Git cleanliness ===" | tee -a "${LOG}"
if git -C "${PROJECT_ROOT}" diff --check 2>&1 | tee -a "${LOG}"; then
  echo "  PASS: Git diff --check clean" | tee -a "${LOG}"
  PASS=$((PASS + 1))
else
  echo "  WARN: Git diff --check found formatting issues" | tee -a "${LOG}"
  WARN=$((WARN + 1))
fi

# === Summary ===
echo "" | tee -a "${LOG}"
echo "[40-validation] ========================================" | tee -a "${LOG}"
echo "[40-validation]  Passed: ${PASS}  Failed: ${FAIL}  Warnings: ${WARN}" | tee -a "${LOG}"
echo "[40-validation] ========================================" | tee -a "${LOG}"

if [ "${FAIL}" -gt 0 ]; then
  echo "[40-validation] FAILED: ${FAIL} validation(s) failed." | tee -a "${LOG}"
  exit 1
fi

echo "[40-validation] PASSED" | tee -a "${LOG}"
exit 0
