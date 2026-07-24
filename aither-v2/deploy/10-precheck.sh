#!/usr/bin/env bash
# Aither / AI Hermes MVP — Automated Deployment
# Stage 10: Pre-check — Environment Validation
#
# Verifies all required tools and prerequisites before deployment.
# Idempotent: safe to run multiple times.
#
# Exit codes:
#   0 — all checks passed
#   1 — one or more mandatory checks failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG="${SCRIPT_DIR}/deploy.log"

echo "[10-precheck] Starting environment validation..." | tee -a "${LOG}"

PASS=0
FAIL=0
WARN=0

# --- Required tools ---
REQUIRED_TOOLS=(
  "docker:docker:Docker Engine"
  "kubectl:kubectl:Kubernetes CLI (kubectl)"
  "git:git:Git"
  "bash:bash:Bash"
  "curl:curl:cURL"
  "openssl:openssl:OpenSSL"
)

echo "[10-precheck] Checking required tools..." | tee -a "${LOG}"

for entry in "${REQUIRED_TOOLS[@]}"; do
  IFS=':' read -r binary tool_name description <<< "${entry}"
  if command -v "${binary}" &>/dev/null; then
    echo "  PASS: ${description} found ($(command -v "${binary}"))" | tee -a "${LOG}"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: ${description} is NOT installed" | tee -a "${LOG}"
    FAIL=$((FAIL + 1))
  fi
done

# --- Optional tools ---
OPTIONAL_TOOLS=(
  "helm:helm:Helm"
  "docker-compose:docker-compose / docker compose:Docker Compose"
)

echo "[10-precheck] Checking optional tools..." | tee -a "${LOG}"

for entry in "${OPTIONAL_TOOLS[@]}"; do
  IFS=':' read -r binary tool_name description <<< "${entry}"
  if command -v "${binary}" &>/dev/null; then
    echo "  PASS: ${description} found ($(command -v "${binary}"))" | tee -a "${LOG}"
  else
    # docker-compose may be a docker subcommand
    if [ "${binary}" = "docker-compose" ] && docker compose version &>/dev/null 2>&1; then
      echo "  PASS: ${description} found (docker compose plugin)" | tee -a "${LOG}"
    else
      echo "  WARN: ${description} not found (optional)" | tee -a "${LOG}"
      WARN=$((WARN + 1))
    fi
  fi
done

# --- Kubernetes cluster check ---
echo "[10-precheck] Checking Kubernetes connectivity..." | tee -a "${LOG}"
if kubectl cluster-info --request-timeout=5s &>/dev/null; then
  echo "  PASS: Kubernetes cluster is reachable" | tee -a "${LOG}"
  PASS=$((PASS + 1))
else
  echo "  FAIL: Kubernetes cluster is NOT reachable" | tee -a "${LOG}"
  FAIL=$((FAIL + 1))
fi

# --- Git repository check ---
echo "[10-precheck] Checking Git repository..." | tee -a "${LOG}"
if git -C "${PROJECT_ROOT}" rev-parse --git-dir &>/dev/null; then
  echo "  PASS: Git repository found" | tee -a "${LOG}"
  PASS=$((PASS + 1))
else
  echo "  FAIL: Not a Git repository" | tee -a "${LOG}"
  FAIL=$((FAIL + 1))
fi

# --- Project structure check ---
echo "[10-precheck] Checking project structure..." | tee -a "${LOG}"
REQUIRED_DIRS=(
  "${PROJECT_ROOT}/manifests"
  "${PROJECT_ROOT}/scripts"
)

for dir in "${REQUIRED_DIRS[@]}"; do
  if [ -d "${dir}" ]; then
    echo "  PASS: Directory ${dir} exists" | tee -a "${LOG}"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: Directory ${dir} is missing" | tee -a "${LOG}"
    FAIL=$((FAIL + 1))
  fi
done

# --- Summary ---
echo "" | tee -a "${LOG}"
echo "[10-precheck] ========================================" | tee -a "${LOG}"
echo "[10-precheck]  Passed: ${PASS}  Failed: ${FAIL}  Warnings: ${WARN}" | tee -a "${LOG}"
echo "[10-precheck] ========================================" | tee -a "${LOG}"

if [ "${FAIL}" -gt 0 ]; then
  echo "[10-precheck] FAILED: ${FAIL} mandatory check(s) failed." | tee -a "${LOG}"
  exit 1
fi

echo "[10-precheck] PASSED" | tee -a "${LOG}"
exit 0
