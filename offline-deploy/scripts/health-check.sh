#!/bin/bash
# Aither Platform — health check (актуально 10.07.2026)
# Проверяет все компоненты платформы одной командой
set -euo pipefail

RED="\033[31m"; GREEN="\033[32m"; YELLOW="\033[33m"; NC="\033[0m"
PASS="${GREEN}✓${NC}"; FAIL="${RED}✗${NC}"; WARN="${YELLOW}⚠${NC}"

# ── Конфигурация ──
VPS1_IP="${VPS1_IP:-170.168.91.95}"
VPS2_IP="${VPS2_IP:-130.17.1.90}"
GATEWAY_PORT="${GATEWAY_PORT:-30900}"
GRAFANA_PORT="${GRAFANA_PORT:-30300}"
PORTAL_URL="${PORTAL_URL:-https://fb1.spb.ru:10443}"

echo "=== Aither Health Check ==="
echo ""

# ── 1. VPS1: nginx ──
echo "── VPS1 ──"
if curl -sk --connect-timeout 5 "${PORTAL_URL}/health" > /dev/null 2>&1; then
  echo "  ${PASS} nginx (${PORTAL_URL})"
else
  echo "  ${FAIL} nginx (${PORTAL_URL})"
fi

# ── 2. Gateway ──
GW=$(curl -sk --connect-timeout 5 "http://${VPS1_IP}:${GATEWAY_PORT}/health" 2>/dev/null)
if echo "$GW" | grep -q status:ok; then
  echo "  ${PASS} Gateway (:${GATEWAY_PORT})"
else
  echo "  ${FAIL} Gateway (:${GATEWAY_PORT}) — $GW"
fi

# ── 3. vLLM models ──
MODELS=$(curl -sk --connect-timeout 5 "http://${VPS1_IP}:${GATEWAY_PORT}/v1/models" 2>/dev/null)
if echo "$MODELS" | grep -q "Qwen2.5-14B"; then
  echo "  ${PASS} vLLM 14B"
else
  echo "  ${FAIL} vLLM 14B"
fi
if echo "$MODELS" | grep -q "Qwen2.5-32B" || echo "$MODELS" | grep -q "astra"; then
  echo "  ${PASS} vLLM 32B (или LoRA)"
else
  echo "  ${WARN} vLLM 32B — не обнаружена"
fi

# ── 4. Grafana ──
if curl -sk --connect-timeout 5 "http://${VPS1_IP}:${GRAFANA_PORT}/grafana/api/health" > /dev/null 2>&1; then
  echo "  ${PASS} Grafana (:${GRAFANA_PORT})"
else
  echo "  ${WARN} Grafana (:${GRAFANA_PORT}) — недоступна"
fi

# ── 5. VPS2: Portal BFF ──
echo ""
echo "── VPS2 ──"
ssh -o ConnectTimeout=5 root@${VPS2_IP} "systemctl is-active aither-bff" 2>/dev/null && \
  echo "  ${PASS} BFF (systemd) — active" || \
  echo "  ${FAIL} BFF — не отвечает"

# ── 6. PostgreSQL (Docker) ──
ssh -o ConnectTimeout=5 root@${VPS2_IP} "docker exec aither-portal-portal-db-1 pg_isready -U portal" 2>/dev/null && \
  echo "  ${PASS} PostgreSQL (Docker)" || \
  echo "  ${WARN} PostgreSQL — проверьте"

# ── 7. Nginx (Docker) ──
ssh -o ConnectTimeout=5 root@${VPS2_IP} "docker ps --filter name=nginx --format {{.Status}} | grep -q Up" 2>/dev/null && \
  echo "  ${PASS} nginx (Docker)" || \
  echo "  ${WARN} nginx (Docker) — проверьте"

# ── Итого ──
echo ""
echo "── Портал ──"
PORTAL=$(curl -sk --connect-timeout 5 "${PORTAL_URL}/api/v1/status" 2>/dev/null)
if echo "$PORTAL" | grep -q "active_api_keys"; then
  echo "  ${PASS} Портал API — OK"
else
  echo "  ${FAIL} Портал API — $PORTAL"
fi

echo ""
echo "Готово."
