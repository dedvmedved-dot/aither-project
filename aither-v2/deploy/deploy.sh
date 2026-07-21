#!/usr/bin/env bash
# Aither / AI Hermes MVP — Automated Deployment Orchestrator
# Stage 14: Automated Deployment
#
# Single entry point for deploying the entire Aither / AI Hermes MVP
# from a clean Kubernetes cluster.
#
# Usage:
#   bash deploy/deploy.sh            # Full deployment
#   bash deploy/deploy.sh --check    # Pre-check only
#   bash deploy/deploy.sh --help     # Show usage
#
# The orchestrator runs four sequential stages:
#   10-precheck.sh       — validate environment
#   20-infrastructure.sh — create namespaces, SA, PVCs, config
#   30-services.sh       — deploy all application manifests
#   40-validation.sh     — run post-deployment checks
#
# Each stage is idempotent and independently executable.
#
# Exit codes:
#   0 — full deployment successful
#   1 — pre-check failed
#   2 — infrastructure stage failed
#   3 — services stage failed
#   4 — validation stage failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="${SCRIPT_DIR}/deploy.log"
START_TS="$(date '+%Y-%m-%d %H:%M:%S %Z')"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# --- Help ---
show_help() {
  echo "Aither / AI Hermes MVP — Automated Deployment Orchestrator"
  echo ""
  echo "Usage:"
  echo "  bash deploy/deploy.sh              Full deployment (all 4 stages)"
  echo "  bash deploy/deploy.sh --check      Pre-check only (stage 10)"
  echo "  bash deploy/deploy.sh --help       Show this help"
  echo ""
  echo "Stages:"
  echo "  10-precheck.sh         Environment validation"
  echo "  20-infrastructure.sh   Namespace, SA, PVCs, RuntimeClass"
  echo "  30-services.sh         vLLM, Gateway, Redis, BFF, Portal"
  echo "  40-validation.sh       Post-deployment diagnostic checks"
  echo ""
  echo "All stages are idempotent. Logs are written to: ${LOG}"
  exit 0
}

# --- Parse arguments ---
RUN_CHECK_ONLY=false
if [ $# -gt 0 ]; then
  case "$1" in
    --check) RUN_CHECK_ONLY=true ;;
    --help)  show_help ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      echo "Usage: bash deploy/deploy.sh [--check|--help]"
      exit 1
      ;;
  esac
fi

# --- Initialize log ---
echo "" > "${LOG}"
echo "══════════════════════════════════════════════════════════════" | tee -a "${LOG}"
echo "  Aither / AI Hermes MVP — Automated Deployment" | tee -a "${LOG}"
echo "  Started: ${START_TS}" | tee -a "${LOG}"
echo "  Directory: ${SCRIPT_DIR}" | tee -a "${LOG}"
echo "══════════════════════════════════════════════════════════════" | tee -a "${LOG}"

# --- Stage 10: Pre-check ---
echo "" | tee -a "${LOG}"
echo -e "${CYAN}[deploy] Stage 10: Environment Pre-check${NC}" | tee -a "${LOG}"
echo "────────────────────────────────────────────────────" | tee -a "${LOG}"

if bash "${SCRIPT_DIR}/10-precheck.sh"; then
  echo -e "${GREEN}[deploy] Stage 10 PASSED${NC}" | tee -a "${LOG}"
else
  echo -e "${RED}[deploy] Stage 10 FAILED — aborting deployment${NC}" | tee -a "${LOG}"
  exit 1
fi

# Exit after pre-check if --check was specified
if [ "${RUN_CHECK_ONLY}" = true ]; then
  echo "" | tee -a "${LOG}"
  echo -e "${GREEN}[deploy] Pre-check only mode — deployment skipped.${NC}" | tee -a "${LOG}"
  echo "[deploy] Run without --check to perform full deployment." | tee -a "${LOG}"
  exit 0
fi

# --- Stage 20: Infrastructure ---
echo "" | tee -a "${LOG}"
echo -e "${CYAN}[deploy] Stage 20: Infrastructure Setup${NC}" | tee -a "${LOG}"
echo "────────────────────────────────────────────────────" | tee -a "${LOG}"

if bash "${SCRIPT_DIR}/20-infrastructure.sh"; then
  echo -e "${GREEN}[deploy] Stage 20 PASSED${NC}" | tee -a "${LOG}"
else
  echo -e "${RED}[deploy] Stage 20 FAILED — aborting deployment${NC}" | tee -a "${LOG}"
  exit 2
fi

# --- Stage 30: Services ---
echo "" | tee -a "${LOG}"
echo -e "${CYAN}[deploy] Stage 30: Service Deployment${NC}" | tee -a "${LOG}"
echo "────────────────────────────────────────────────────" | tee -a "${LOG}"

if bash "${SCRIPT_DIR}/30-services.sh"; then
  echo -e "${GREEN}[deploy] Stage 30 PASSED${NC}" | tee -a "${LOG}"
else
  echo -e "${RED}[deploy] Stage 30 FAILED — aborting deployment${NC}" | tee -a "${LOG}"
  exit 3
fi

# --- Stage 40: Validation ---
echo "" | tee -a "${LOG}"
echo -e "${CYAN}[deploy] Stage 40: Post-deployment Validation${NC}" | tee -a "${LOG}"
echo "────────────────────────────────────────────────────" | tee -a "${LOG}"

if bash "${SCRIPT_DIR}/40-validation.sh"; then
  echo -e "${GREEN}[deploy] Stage 40 PASSED${NC}" | tee -a "${LOG}"
else
  echo -e "${RED}[deploy] Stage 40 FAILED — deployment may be incomplete${NC}" | tee -a "${LOG}"
  exit 4
fi

# --- Complete ---
END_TS="$(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "" | tee -a "${LOG}"
echo "══════════════════════════════════════════════════════════════" | tee -a "${LOG}"
echo -e "${GREEN}  DEPLOYMENT COMPLETE${NC}" | tee -a "${LOG}"
echo "  Started: ${START_TS}" | tee -a "${LOG}"
echo "  Ended:   ${END_TS}" | tee -a "${LOG}"
echo "  Log:     ${LOG}" | tee -a "${LOG}"
echo "══════════════════════════════════════════════════════════════" | tee -a "${LOG}"

exit 0
