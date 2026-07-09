#!/bin/bash
# Aither Platform — Production Health Check
# Запуск: ./health-check.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; }

echo "════════════════════════════════════════"
echo "  Aither Health Check — $(date '+%Y-%m-%d %H:%M')"
echo "════════════════════════════════════════"

echo -e "\n── Nodes ──"
kubectl get nodes -o wide 2>/dev/null && pass "All nodes Ready" || fail "Node check failed"

echo -e "\n── Resources ──"
kubectl top nodes 2>/dev/null && pass "Metrics available" || warn "Metrics API not available"

echo -e "\n── Pods (non-Running) ──"
PROBLEM=$(kubectl get pods -A --field-selector=status.phase!=Running 2>/dev/null | grep -v -E 'Completed|NAME')
if [ -z "$PROBLEM" ]; then
    pass "All pods healthy"
else
    warn "Non-running pods found:"
    echo "$PROBLEM"
fi

echo -e "\n── GPU ──"
kubectl describe nodes 2>/dev/null | grep -B1 'nvidia.com/gpu:' | grep -v '^--$' | grep -v 'nvidia.com/gpu\.' && pass "GPU detected" || fail "GPU check failed"

echo -e "\n── Endpoints ──"
HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:30900/health 2>/dev/null)
[ "$HTTP_CODE" = "200" ] && pass "Gateway  :30900" || fail "Gateway  :30900 ($HTTP_CODE)"

HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/api/v1/health 2>/dev/null)
[ "$HTTP_CODE" = "200" ] && pass "Portal   :3000" || warn "Portal   :3000 ($HTTP_CODE)"

echo -e "\n── Storage ──"
kubectl exec deploy/postgres -- psql -U aither -d aither_billing -c "SELECT count(*) as users FROM portal_users;" 2>/dev/null && pass "PostgreSQL" || fail "PostgreSQL"
kubectl exec deploy/redis -- redis-cli ping 2>/dev/null | grep -q PONG && pass "Redis" || fail "Redis"

echo -e "\n── Done ──"
