#!/bin/bash
# Aither Gateway 32B — Authenticated End-to-End Test
# Usage: bash scripts/test-gateway-32b-e2e.sh [namespace]
#
# Performs authenticated E2E completion through Gateway, verifying:
#   - Gateway /v1/models returns actual API model ID
#   - Gateway /v1/completions returns HTTP 200 with non-empty completion
#   - No auth errors, no model-not-found errors
#
# Requires: kubectl, curl, base64
# Token is read from Kubernetes Secret (not printed or committed)
set -euo pipefail

NS="${1:-aither-inference}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

pass() { echo -e "${GREEN}✓${NC} $1"; PASS=$((PASS+1)); }
fail() { echo -e "${RED}✗${NC} $1"; FAIL=$((FAIL+1)); }

echo "══════════════════════════════════════════════════════"
echo "  Aither Gateway 32B — Authenticated E2E Test"
echo "  Namespace: $NS"
echo "  $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "══════════════════════════════════════════════════════"

# Get auth token from env or K8s Secret (never printed)
GATEWAY_TOKEN="${GATEWAY_TOKEN:-}"
if [ -z "$GATEWAY_TOKEN" ]; then
    GATEWAY_TOKEN=$(kubectl get secret -n "$NS" aither-bff-auth \
        -o jsonpath='{.data.BFF_32B_GATEWAY_AUTH_TOKEN}' 2>/dev/null | base64 -d || echo "")
fi
if [ -z "$GATEWAY_TOKEN" ]; then
    fail "Gateway authentication token unavailable"
    echo ""
    echo "══════════════════════════════════════════════════════"
    echo -e "${RED}Passed: $PASS  Failed: $FAIL${NC}"
    echo "══════════════════════════════════════════════════════"
    exit "$FAIL"
fi

# Find a gateway pod
GWPOD=$(kubectl -n "$NS" get pods -l app=nginx-gateway -o wide 2>/dev/null | grep " n7" | awk '{print $1}' | head -1)
if [ -z "$GWPOD" ]; then
    GWPOD=$(kubectl -n "$NS" get pods -l app=nginx-gateway -o name 2>/dev/null | head -1 | sed 's|pod/||')
fi

if [ -z "$GWPOD" ]; then
    fail "No gateway pod found"
    exit "$FAIL"
fi
echo -e "\nUsing gateway pod: $GWPOD"

# --- Test 1: /v1/models ---
echo -e "\n── Test 1: /v1/models through Gateway ──"
MODELS_RESPONSE=$(kubectl -n "$NS" exec "$GWPOD" -- sh -c "curl -s -w '\nHTTP_CODE:%{http_code}' http://localhost:8000/v1/models -H 'Authorization: Bearer ${GATEWAY_TOKEN}' --connect-timeout 10 --max-time 30" 2>/dev/null || echo "ERR")
MODELS_HTTP=$(echo "$MODELS_RESPONSE" | grep 'HTTP_CODE:' | sed 's/HTTP_CODE://')
MODELS_BODY=$(echo "$MODELS_RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$MODELS_HTTP" = "200" ]; then
    ACTUAL_MODEL_ID=$(echo "$MODELS_BODY" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "unknown")
    if [ -n "$ACTUAL_MODEL_ID" ] && [ "$ACTUAL_MODEL_ID" != "null" ]; then
        pass "/v1/models: HTTP 200, model ID: $ACTUAL_MODEL_ID"
    else
        fail "/v1/models: HTTP 200 but no model ID"
    fi
else
    fail "/v1/models: expected 200, got ${MODELS_HTTP:-ERR}"
fi

# --- Test 2: /v1/completions through Gateway ---
echo -e "\n── Test 2: /v1/completions through Gateway ──"
COMP_MODEL="${ACTUAL_MODEL_ID:-qwen-32b-base}"

COMP_RESPONSE=$(kubectl -n "$NS" exec "$GWPOD" -- sh -c "curl -s -w '\nHTTP_CODE:%{http_code}' -X POST http://localhost:8000/v1/completions -H 'Content-Type: application/json' -H 'Authorization: Bearer ${GATEWAY_TOKEN}' -d '{\"model\":\"${COMP_MODEL}\",\"prompt\":\"Return exactly the word READY\",\"max_tokens\":8,\"temperature\":0}' --connect-timeout 30 --max-time 120" 2>/dev/null || echo "ERR")

COMP_HTTP=$(echo "$COMP_RESPONSE" | grep 'HTTP_CODE:' | sed 's/HTTP_CODE://')
COMP_BODY=$(echo "$COMP_RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$COMP_HTTP" = "200" ]; then
    CHOICE_TEXT=$(echo "$COMP_BODY" | grep -o '"text":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
    RESP_MODEL=$(echo "$COMP_BODY" | grep -o '"model":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
    if [ -n "$CHOICE_TEXT" ]; then
        pass "/v1/completions: HTTP 200, text=\"$(echo "$CHOICE_TEXT" | head -c 50)\""
    else
        fail "/v1/completions: HTTP 200 but empty completion"
    fi
    # Check for model error
    if echo "$COMP_BODY" | grep -qi 'not found'; then
        fail "Response contains 'not found' error"
    else
        pass "No model errors in response"
    fi
    # Check response model consistency
    if [ -z "$RESP_MODEL" ]; then
        fail "Response model field is missing"
    elif [ "$RESP_MODEL" = "$COMP_MODEL" ]; then
        pass "Response model matches requested model: $RESP_MODEL"
    else
        fail "Model mismatch: requested=$COMP_MODEL response=$RESP_MODEL"
    fi
else
    fail "/v1/completions: expected 200, got ${COMP_HTTP:-ERR}"
fi

# --- Summary ---
echo ""
echo "══════════════════════════════════════════════════════"
echo -e "${GREEN}Passed: $PASS${NC}  ${RED}Failed: $FAIL${NC}"
echo "══════════════════════════════════════════════════════"
exit "$FAIL"
