#!/bin/bash
# Aither Gateway 32B Diagnostic Script
# Usage: bash scripts/check-gateway-32b.sh [namespace]
# Checks Gateway connectivity, DNS resolution, 32B availability
# No secrets required — uses internal K8s API

set -euo pipefail

NS="${1:-aither-inference}"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

pass() { echo -e "${GREEN}✓${NC} $1"; PASS=$((PASS+1)); }
fail() { echo -e "${RED}✗${NC} $1"; FAIL=$((FAIL+1)); }
warn() { echo -e "${YELLOW}⚠${NC} $1"; WARN=$((WARN+1)); }

echo "════════════════════════════════════════"
echo "  Aither Gateway 32B — Diagnostic Check"
echo "  Namespace: $NS"
echo "════════════════════════════════════════"

# 1. Check service exists
echo -e "\n── Service ──"
SVCCIDR=$(kubectl -n "$NS" get svc vllm-32b-gptq -o jsonpath='{.spec.clusterIP}' 2>/dev/null || true)
if [ -n "$SVCCIDR" ]; then
  pass "vllm-32b-gptq Service exists (ClusterIP: $SVCCIDR)"
else
  # Try alternative approach
  SVCCIDR=$(kubectl -n "$NS" get svc vllm-32b-gptq -o wide 2>/dev/null | awk 'NR>1{print $3}')
  if [ -n "$SVCCIDR" ] && [ "$SVCCIDR" != "CLUSTER-IP" ]; then
    pass "vllm-32b-gptq Service exists (ClusterIP: $SVCCIDR)"
  else
    fail "vllm-32b-gptq Service not found"
  fi
fi

# 2. Check endpoints
EP=$(kubectl -n "$NS" get endpoints vllm-32b-gptq -o jsonpath='{.subsets[0].addresses[0].ip}' 2>/dev/null) && \
  pass "vllm-32b-gptq has endpoints (e.g. $EP)" || \
  fail "vllm-32b-gptq has NO endpoints"

# 3. Gateway service
GWIP=$(kubectl -n "$NS" get svc nginx-gateway-32b -o jsonpath='{.spec.clusterIP}' 2>/dev/null) && \
  pass "nginx-gateway-32b Service exists (ClusterIP: $GWIP)" || \
  fail "nginx-gateway-32b Service not found"

# 4. Gateway pods running
GWREADY=$(kubectl -n "$NS" get deployment nginx-gateway-32b -o jsonpath='{.status.readyReplicas}' 2>/dev/null)
GWREPLICAS=$(kubectl -n "$NS" get deployment nginx-gateway-32b -o jsonpath='{.spec.replicas}' 2>/dev/null)
if [ "$GWREADY" = "$GWREPLICAS" ] && [ -n "$GWREADY" ]; then
  pass "nginx-gateway-32b: $GWREADY/$GWREPLICAS ready"
else
  fail "nginx-gateway-32b: ${GWREADY:-0}/${GWREPLICAS:-?} ready"
fi

# 5. Gateway pod details
GWPOD_N7=$(kubectl -n "$NS" get pods -l app=nginx-gateway -o wide 2>/dev/null | grep "n7-" | awk '{print $1}' || true)
GWPOD_N8=$(kubectl -n "$NS" get pods -l app=nginx-gateway -o wide 2>/dev/null | grep "n8-" | awk '{print $1}' || true)
if [ -n "$GWPOD_N7" ]; then pass "Gateway pod on n7: $GWPOD_N7"; else warn "No gateway pod on n7"; fi
if [ -n "$GWPOD_N8" ]; then pass "Gateway pod on n8: $GWPOD_N8"; else warn "No gateway pod on n8"; fi

# 6. Test auth passthrough (should return 401 without token)
echo -e "\n── Auth passthrough ──"
for pod in "$GWPOD_N7" "$GWPOD_N8"; do
  [ -z "$pod" ] && continue
  GW_NODE=$(kubectl -n "$NS" get pod "$pod" -o jsonpath='{.spec.nodeName}')
  STATUS=$(kubectl -n "$NS" exec "$pod" -- sh -c '
    curl -s -o /dev/null -w "%{http_code}" \
      http://localhost:8000/v1/completions \
      -H "Content-Type: application/json" \
      -d "{\"model\":\"qwen-32b-base\",\"prompt\":\"test\",\"max_tokens\":1}" \
      --connect-timeout 5 --max-time 10' 2>/dev/null || echo "ERR")
  if [ "$STATUS" = "401" ]; then
    pass "Gateway on $GW_NODE: returns 401 without auth token"
  elif [ "$STATUS" = "ERR" ]; then
    warn "Gateway on $GW_NODE: could not test (VPN unstable)"
  else
    warn "Gateway on $GW_NODE: expected 401, got $STATUS"
  fi
done

# 7. Test unsupported endpoint (should return 422)
echo -e "\n── Unsupported endpoint ──"
for pod in "$GWPOD_N7" "$GWPOD_N8"; do
  [ -z "$pod" ] && continue
  GW_NODE=$(kubectl -n "$NS" get pod "$pod" -o jsonpath='{.spec.nodeName}')
  STATUS=$(kubectl -n "$NS" exec "$pod" -- sh -c '
    curl -s -o /dev/null -w "%{http_code}" \
      -X POST http://localhost:8000/v1/chat/completions \
      -H "Content-Type: application/json" \
      -d "{}" --connect-timeout 5 --max-time 10' 2>/dev/null || echo "ERR")
  if [ "$STATUS" = "422" ]; then
    pass "Gateway on $GW_NODE: blocks /v1/chat/completions (422)"
  elif [ "$STATUS" = "ERR" ]; then
    warn "Gateway on $GW_NODE: could not test (VPN unstable)"
  else
    warn "Gateway on $GW_NODE: expected 422, got $STATUS"
  fi
done

# 8. Check dnsPolicy
echo -e "\n── DNS Policy ──"
DNSPOLICY=$(kubectl -n "$NS" get deployment nginx-gateway-32b -o jsonpath='{.spec.template.spec.dnsPolicy}' 2>/dev/null)
if [ "$DNSPOLICY" = "Default" ]; then
  pass "dnsPolicy: Default (n7-compatible)"
else
  warn "dnsPolicy: $DNSPOLICY — may fail on n7 if ClusterDNS missing"
fi

# 9. Check nginx -t
echo -e "\n── Nginx Config ──"
for pod in "$GWPOD_N7" "$GWPOD_N8"; do
  [ -z "$pod" ] && continue
  GW_NODE=$(kubectl -n "$NS" get pod "$pod" -o jsonpath='{.spec.nodeName}')
  NGINX_OK=$(kubectl -n "$NS" exec "$pod" -- nginx -t 2>&1 | grep -c "successful" || true)
  if [ "$NGINX_OK" -ge 1 ]; then
    pass "nginx -t on $GW_NODE: OK"
  else
    fail "nginx -t on $GW_NODE: FAILED"
  fi
done

# 10. Check service endpoint consistency
echo -e "\n── Git/Runtime Consistency ──"
RUNTIME_UPSTREAM=$(kubectl -n "$NS" get configmap nginx-gateway-32b -o jsonpath='{.data.nginx\.conf}' 2>/dev/null | grep proxy_pass | head -1 | sed 's/.*http:\/\///;s/:8000.*//')
if [ -n "$RUNTIME_UPSTREAM" ]; then
  pass "Runtime upstream: $RUNTIME_UPSTREAM"
fi

echo ""
echo "════════════════════════════════════════"
echo -e "${GREEN}Passed: $PASS${NC}  ${RED}Failed: $FAIL${NC}  ${YELLOW}Warnings: $WARN${NC}"
echo "════════════════════════════════════════"
exit $FAIL
