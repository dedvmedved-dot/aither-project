#!/bin/bash
# Aither Gateway 32B — Comprehensive Diagnostic Script
# Usage: bash scripts/check-gateway-32b.sh [namespace]
#
# Performs all checks required by Stage 10 Part 2 acceptance:
#   - K8s Service, Deployment, Pods
#   - DNS policy and upstream consistency (5 levels)
#   - nginx syntax and config
#   - API behaviour (auth, unsupported, authenticated E2E)
#   - Git/runtime/running config equality
#
# Requires: kubectl, curl, base64, grep, awk, sed
#
# Token sources (in priority):
#   1. GATEWAY_TOKEN environment variable
#   2. Kubernetes Secret aither-bff-auth / BFF_32B_GATEWAY_AUTH_TOKEN
#
# Exit semantics: FAIL > 0 → exit 1; otherwise exit 0
set -euo pipefail

NS="${1:-aither-inference}"
GATEWAY_SECRET_NAME="${GATEWAY_SECRET_NAME:-aither-bff-auth}"
MANIFEST_DIR="manifests/mvp-roadmap/04-gateway"
MANIFEST_FILE="${MANIFEST_DIR}/nginx-gateway-32b-hardened.yaml"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

pass()  { echo -e "${GREEN}✓${NC} $1"; PASS=$((PASS+1)); }
fail()  { echo -e "${RED}✗${NC} $1"; FAIL=$((FAIL+1)); }
warn()  { echo -e "${YELLOW}⚠${NC} $1"; WARN=$((WARN+1)); }

# Validates that completion response model matches requested model.
# Called with: validate_response_model "$requested_model" "$response_model"
# Exported so it can be tested independently.
validate_response_model() {
    local requested="$1"
    local response="$2"

    if [ -z "$response" ]; then
        fail "Completion response model field is missing"
    elif [ "$response" = "$requested" ]; then
        pass "Completion response model matches requested model: $response"
    else
        fail "Completion model mismatch: requested=$requested response=$response"
    fi
}

# Self-test mode: when MODEL_VALIDATION_SELFTEST=1, runs model validation
# self-tests and exits, skipping production checks.
if [ "${MODEL_VALIDATION_SELFTEST:-0}" = "1" ]; then
    echo "═══ Model Validation Self-Test ═══"

    echo -e "\n--- Case A: mismatch ---"
    validate_response_model "qwen-32b-base" "wrong-model"

    echo -e "\n--- Case B: missing model ---"
    validate_response_model "qwen-32b-base" ""

    echo -e "\n--- Case C: match ---"
    validate_response_model "qwen-32b-base" "qwen-32b-base"

    echo ""
    echo "═══════════════════════════════════"
    echo -e "${GREEN}Passed: $PASS${NC}  ${RED}Failed: $FAIL${NC}  ${YELLOW}Warnings: $WARN${NC}"
    echo "═══════════════════════════════════"
    if [ "$FAIL" -gt 0 ]; then exit 1; fi
    exit 0
fi

echo "══════════════════════════════════════════════════════"
echo "  Aither Gateway 32B — Comprehensive Diagnostic Check"
echo "  Namespace: $NS"
echo "  $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "══════════════════════════════════════════════════════"

# ============================================================
# Dependency check
# ============================================================
echo -e "\n── Dependency Check ──"
DEPS_OK=0
for cmd in kubectl curl base64 grep awk sed; do
    if command -v "$cmd" &>/dev/null; then
        : # pass silently
    else
        echo -e "  ${RED}✗${NC} Missing required command: $cmd"
        DEPS_OK=$((DEPS_OK+1))
    fi
done
if [ "$DEPS_OK" -gt 0 ]; then
    fail "Missing $DEPS_OK required command(s)"
else
    pass "All required commands available"
fi

# ============================================================
# Token resolution
# ============================================================
echo -e "\n── Authentication Token ──"
GATEWAY_TOKEN="${GATEWAY_TOKEN:-}"

if [ -z "$GATEWAY_TOKEN" ]; then
    GATEWAY_TOKEN="$(
        kubectl -n "$NS" get secret "$GATEWAY_SECRET_NAME" \
            -o jsonpath='{.data.BFF_32B_GATEWAY_AUTH_TOKEN}' \
            2>/dev/null | base64 -d || echo ""
    )"
fi

if [ -z "$GATEWAY_TOKEN" ]; then
    fail "Gateway authentication token unavailable; authenticated acceptance tests cannot run"
else
    TOKEN_LEN=${#GATEWAY_TOKEN}
    pass "Gateway authentication token resolved (${TOKEN_LEN} chars)"
fi

# ============================================================
# SECTION 1: Kubernetes Services
# ============================================================
echo -e "\n── 1. Kubernetes Services ──"

# 1.1 Service vllm-32b-gptq exists
SVC_CIDR=$(kubectl -n "$NS" get svc vllm-32b-gptq -o jsonpath='{.spec.clusterIP}' 2>/dev/null || echo "")
if [ -n "$SVC_CIDR" ]; then
    pass "vllm-32b-gptq Service exists (ClusterIP: $SVC_CIDR)"
else
    fail "vllm-32b-gptq Service not found"
fi

# 1.2 Service has non-empty ClusterIP
if [ -n "$SVC_CIDR" ] && [ "$SVC_CIDR" != "None" ]; then
    pass "vllm-32b-gptq ClusterIP is valid ($SVC_CIDR)"
else
    fail "vllm-32b-gptq ClusterIP is empty or None"
fi

# 1.3 Service has ready endpoints
EP_RAW=$(kubectl -n "$NS" get endpoints vllm-32b-gptq -o jsonpath='{.subsets[0].addresses}' 2>/dev/null || echo "")
if [ -n "$EP_RAW" ] && [ "$EP_RAW" != "[]" ]; then
    EP_COUNT=$(echo "$EP_RAW" | grep -o '"ip"' | wc -l)
    pass "vllm-32b-gptq has $EP_COUNT ready endpoint(s)"
else
    fail "vllm-32b-gptq has NO ready endpoints"
fi

# 1.4 Gateway Service exists
GW_SVC_CIDR=$(kubectl -n "$NS" get svc nginx-gateway-32b -o jsonpath='{.spec.clusterIP}' 2>/dev/null || echo "")
if [ -n "$GW_SVC_CIDR" ]; then
    pass "nginx-gateway-32b Service exists (ClusterIP: $GW_SVC_CIDR)"
else
    fail "nginx-gateway-32b Service not found"
fi

# ============================================================
# SECTION 2: Deployment
# ============================================================
echo -e "\n── 2. Deployment ──"

# 2.5 Deployment exists
DEP_EXISTS=$(kubectl -n "$NS" get deployment nginx-gateway-32b -o name 2>/dev/null || echo "")
if [ -n "$DEP_EXISTS" ]; then
    pass "Gateway Deployment exists"
else
    fail "Gateway Deployment not found"
fi

# 2.6 spec.replicas equals expected
SPEC_REPLICAS=$(kubectl -n "$NS" get deployment nginx-gateway-32b -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")
READY_REPLICAS=$(kubectl -n "$NS" get deployment nginx-gateway-32b -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
if [ "$SPEC_REPLICAS" -ge 2 ]; then
    pass "spec.replicas = $SPEC_REPLICAS (expected >= 2)"
else
    fail "spec.replicas = $SPEC_REPLICAS (expected >= 2)"
fi

# 2.7 readyReplicas == spec.replicas
if [ "$READY_REPLICAS" = "$SPEC_REPLICAS" ] && [ "$SPEC_REPLICAS" -gt 0 ]; then
    pass "readyReplicas ($READY_REPLICAS) == spec.replicas ($SPEC_REPLICAS)"
else
    fail "readyReplicas ($READY_REPLICAS) != spec.replicas ($SPEC_REPLICAS)"
fi

# 2.8 Gateway pod on n7
GWPOD_N7=$(kubectl -n "$NS" get pods -l app=nginx-gateway -o wide 2>/dev/null | grep "n7" | awk '{print $1}' || echo "")
if [ -n "$GWPOD_N7" ]; then
    pass "Gateway pod on n7 found: $GWPOD_N7"
else
    fail "No gateway pod on n7"
fi

# 2.9 Gateway pod on n8
GWPOD_N8=$(kubectl -n "$NS" get pods -l app=nginx-gateway -o wide 2>/dev/null | grep "n8" | awk '{print $1}' || echo "")
if [ -n "$GWPOD_N8" ]; then
    pass "Gateway pod on n8 found: $GWPOD_N8"
else
    fail "No gateway pod on n8"
fi

# 2.10 Pod phase + Ready condition
echo -e "\n── Pod Readiness ──"
for pod in "$GWPOD_N7" "$GWPOD_N8"; do
    [ -z "$pod" ] && continue
    P_NODE=$(kubectl -n "$NS" get pod "$pod" -o jsonpath='{.spec.nodeName}' 2>/dev/null || echo "unknown")
    P_PHASE=$(kubectl -n "$NS" get pod "$pod" -o jsonpath='{.status.phase}' 2>/dev/null || echo "")
    P_READY=$(kubectl -n "$NS" get pod "$pod" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "")
    if [ "$P_PHASE" = "Running" ] && [ "$P_READY" = "True" ]; then
        pass "Gateway pod on $P_NODE: phase=$P_PHASE, Ready=$P_READY"
    else
        fail "Gateway pod on $P_NODE: phase=$P_PHASE, Ready=$P_READY (expected Running + True)"
    fi
done

# ============================================================
# SECTION 3: DNS and Upstream Consistency (5 levels)
# ============================================================
echo -e "\n── 3. DNS/Upstream Consistency ──"

# 3.11 dnsPolicy (fail-closed: only ClusterFirst passes)
DNSPOLICY=""
if ! DNSPOLICY=$(kubectl -n "$NS" get deployment nginx-gateway-32b \
    -o jsonpath='{.spec.template.spec.dnsPolicy}' 2>/dev/null); then
    fail "Could not read Gateway dnsPolicy (kubectl error)"
elif [ -z "$DNSPOLICY" ]; then
    fail "dnsPolicy is empty (expected ClusterFirst)"
elif [ "$DNSPOLICY" = "ClusterFirst" ]; then
    pass "dnsPolicy: ClusterFirst"
elif [ "$DNSPOLICY" = "Default" ]; then
    fail "dnsPolicy: Default workaround is not allowed after DNS-N7-01 remediation"
else
    fail "dnsPolicy: $DNSPOLICY (expected ClusterFirst)"
fi

# Level 1: Service ClusterIP
SVC_UPSTREAM="${SVC_CIDR}:8000"

# Level 2: Git manifest upstream (for /v1/completions)
GIT_UPSTREAM=""
if [ -f "$MANIFEST_FILE" ]; then
    GIT_UPSTREAM=$(awk '/location \/v1\/completions/,/}/' "$MANIFEST_FILE" | grep proxy_pass | sed 's/.*http:\/\///;s/;.*//')
fi
if [ -n "$GIT_UPSTREAM" ]; then
    pass "Git manifest upstream: $GIT_UPSTREAM"
else
    fail "Could not extract Git manifest upstream"
fi

# Level 3: Runtime ConfigMap upstream
RUNTIME_UPSTREAM=$(kubectl -n "$NS" get configmap nginx-gateway-32b -o jsonpath='{.data.nginx\.conf}' 2>/dev/null | awk '/location \/v1\/completions/,/}/' | grep proxy_pass | sed 's/.*http:\/\///;s/;.*//')
if [ -n "$RUNTIME_UPSTREAM" ]; then
    pass "Runtime ConfigMap upstream: $RUNTIME_UPSTREAM"
else
    fail "Could not extract Runtime ConfigMap upstream"
fi

# Level 4: Running nginx config on both pods (nginx -T)
NGINX_UPSTREAM_N7=""
NGINX_UPSTREAM_N8=""
if [ -n "$GWPOD_N7" ]; then
    NGINX_UPSTREAM_N7=$(kubectl -n "$NS" exec "$GWPOD_N7" -- nginx -T 2>/dev/null | awk '/location \/v1\/completions/,/}/' | grep proxy_pass | sed 's/.*http:\/\///;s/;.*//' || echo "")
fi
if [ -n "$GWPOD_N8" ]; then
    NGINX_UPSTREAM_N8=$(kubectl -n "$NS" exec "$GWPOD_N8" -- nginx -T 2>/dev/null | awk '/location \/v1\/completions/,/}/' | grep proxy_pass | sed 's/.*http:\/\///;s/;.*//' || echo "")
fi

[ -n "$NGINX_UPSTREAM_N7" ] && pass "Running nginx upstream (n7): $NGINX_UPSTREAM_N7" || fail "Could not extract running nginx upstream from n7"
[ -n "$NGINX_UPSTREAM_N8" ] && pass "Running nginx upstream (n8): $NGINX_UPSTREAM_N8" || fail "Could not extract running nginx upstream from n8"

# Acceptance: all 5 values must match
ALL_UPSTREAMS=("$SVC_UPSTREAM" "$GIT_UPSTREAM" "$RUNTIME_UPSTREAM" "$NGINX_UPSTREAM_N7" "$NGINX_UPSTREAM_N8")
UNIQUE_UPSTREAMS=$(printf '%s\n' "${ALL_UPSTREAMS[@]}" | sort -u | grep -v '^$' | wc -l)
if [ "$UNIQUE_UPSTREAMS" -eq 1 ] && [ -n "$SVC_UPSTREAM" ]; then
    pass "Upstream consistency: ALL 5 levels match ($SVC_UPSTREAM)"
else
    fail "Upstream MISMATCH — unique values: $UNIQUE_UPSTREAMS (expected 1)"
    echo -e "  ${YELLOW}Service CIP:    $SVC_UPSTREAM${NC}"
    echo -e "  ${YELLOW}Git manifest:   $GIT_UPSTREAM${NC}"
    echo -e "  ${YELLOW}Runtime CM:     $RUNTIME_UPSTREAM${NC}"
    echo -e "  ${YELLOW}Running n7:     ${NGINX_UPSTREAM_N7:-N/A}${NC}"
    echo -e "  ${YELLOW}Running n8:     ${NGINX_UPSTREAM_N8:-N/A}${NC}"
fi

# ============================================================
# SECTION 4: nginx Configuration Validation
# ============================================================
echo -e "\n── 4. nginx Config ──"

for pod in "$GWPOD_N7" "$GWPOD_N8"; do
    [ -z "$pod" ] && continue
    GW_NODE=$(kubectl -n "$NS" get pod "$pod" -o jsonpath='{.spec.nodeName}' 2>/dev/null || echo "unknown")
    NGINX_OK=$(kubectl -n "$NS" exec "$pod" -- nginx -t 2>&1 | grep -c "successful" || true)
    if [ "$NGINX_OK" -ge 1 ]; then
        pass "nginx -t on $GW_NODE: OK"
    else
        fail "nginx -t on $GW_NODE: FAILED"
    fi
done

# 4.20 Health endpoints — both /healthz (local) and /health (upstream)
echo -e "\n── Health Checks ──"
for pod in "$GWPOD_N7" "$GWPOD_N8"; do
    [ -z "$pod" ] && continue
    GW_NODE=$(kubectl -n "$NS" get pod "$pod" -o jsonpath='{.spec.nodeName}' 2>/dev/null || echo "unknown")

    # /healthz (local nginx, no upstream dependency)
    HZ_CODE=$(kubectl -n "$NS" exec "$pod" -- sh -c 'curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/healthz --connect-timeout 5 --max-time 10' 2>/dev/null || echo "FAIL")
    if [ "$HZ_CODE" = "200" ]; then
        pass "Gateway /healthz on $GW_NODE: $HZ_CODE"
    else
        fail "Gateway /healthz on $GW_NODE: expected 200, got ${HZ_CODE}"
    fi

    # /health (upstream proxy to vLLM)
    H_CODE=$(kubectl -n "$NS" exec "$pod" -- sh -c 'curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health --connect-timeout 10 --max-time 30' 2>/dev/null || echo "FAIL")
    if [ "$H_CODE" = "200" ]; then
        pass "Gateway /health on $GW_NODE: $H_CODE"
    else
        fail "Gateway /health on $GW_NODE: expected 200, got ${H_CODE}"
    fi
done

# ============================================================
# SECTION 5: API Behaviour — Unauthenticated
# ============================================================
echo -e "\n── 5. API Tests (Unauthenticated) ──"

# 5.x No auth → 401
for pod in "$GWPOD_N7" "$GWPOD_N8"; do
    [ -z "$pod" ] && continue
    GW_NODE=$(kubectl -n "$NS" get pod "$pod" -o jsonpath='{.spec.nodeName}' 2>/dev/null || echo "unknown")
    STATUS=$(kubectl -n "$NS" exec "$pod" -- sh -c '
        curl -s -o /dev/null -w "%{http_code}" \
            -X POST http://localhost:8000/v1/completions \
            -H "Content-Type: application/json" \
            -d "{\"model\":\"qwen-32b-base\",\"prompt\":\"test\",\"max_tokens\":1}" \
            --connect-timeout 5 --max-time 10' 2>/dev/null || echo "ERR")
    if [ "$STATUS" = "401" ]; then
        pass "Gateway on $GW_NODE: returns 401 without auth token"
    elif [ "$STATUS" = "ERR" ]; then
        fail "Gateway on $GW_NODE: could not test auth (VPN)"
    else
        fail "Gateway on $GW_NODE: expected 401, got $STATUS"
    fi
done

# 5.x Unsupported /v1/chat/completions → 422
for pod in "$GWPOD_N7" "$GWPOD_N8"; do
    [ -z "$pod" ] && continue
    GW_NODE=$(kubectl -n "$NS" get pod "$pod" -o jsonpath='{.spec.nodeName}' 2>/dev/null || echo "unknown")
    STATUS=$(kubectl -n "$NS" exec "$pod" -- sh -c '
        curl -s -o /dev/null -w "%{http_code}" \
            -X POST http://localhost:8000/v1/chat/completions \
            -H "Content-Type: application/json" \
            -d "{}" --connect-timeout 5 --max-time 10' 2>/dev/null || echo "ERR")
    if [ "$STATUS" = "422" ]; then
        pass "Gateway on $GW_NODE: blocks /v1/chat/completions (422)"
    elif [ "$STATUS" = "ERR" ]; then
        fail "Gateway on $GW_NODE: could not test unsupported endpoint (VPN)"
    else
        fail "Gateway on $GW_NODE: expected 422, got $STATUS"
    fi
done

# ============================================================
# SECTION 6: Authenticated Tests (mandatory)
# ============================================================
echo -e "\n── 6. Authenticated Tests (mandatory) ──"
ACTUAL_MODEL_ID=""

do_authed_request() {
    local pod="$1" url="$2" method="${3:-GET}" data="${4:-}"
    local token="$5"

    local result result_code
    if [ "$method" = "GET" ]; then
        result_code=0
        result=$(kubectl -n "$NS" exec "$pod" -- sh -c "curl -s -w '\\nSTATUS:%{http_code}' '${url}' -H 'Authorization: Bearer ${token}' --connect-timeout 10 --max-time 30" 2>/dev/null) || result_code=$?
    else
        result_code=0
        result=$(kubectl -n "$NS" exec "$pod" -- sh -c "curl -s -w '\\nSTATUS:%{http_code}' -X POST '${url}' -H 'Content-Type: application/json' -H 'Authorization: Bearer ${token}' -d '${data}' --connect-timeout 30 --max-time 120" 2>/dev/null) || result_code=$?
    fi

    if [ "$result_code" -ne 0 ]; then
        echo "ERR||"
        return
    fi
    local http_code
    http_code=$(echo "$result" | grep 'STATUS:' | sed 's/STATUS://')
    local body
    body=$(echo "$result" | sed '/STATUS:/d')
    echo "${http_code}||${body}"
}

# 6.1 /v1/models through Gateway
echo -e "\n--- /v1/models ---"
R1=$(do_authed_request "$GWPOD_N7" "http://localhost:8000/v1/models" "GET" "" "$GATEWAY_TOKEN")
MODELS_HTTP=$(echo "$R1" | cut -d'|' -f1)
MODELS_BODY=$(echo "$R1" | cut -d'|' -f2-)

if [ "$MODELS_HTTP" = "200" ]; then
    ACTUAL_MODEL_ID=$(echo "$MODELS_BODY" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
    if [ -n "$ACTUAL_MODEL_ID" ]; then
        pass "Gateway /v1/models: HTTP 200, model ID: $ACTUAL_MODEL_ID"
    else
        fail "Gateway /v1/models: HTTP 200 but could not extract model ID"
    fi
else
    fail "Gateway /v1/models: expected 200, got ${MODELS_HTTP:-ERR}"
fi

# 6.2 /v1/completions through Gateway
COMP_MODEL="${ACTUAL_MODEL_ID:-qwen-32b-base}"
echo -e "\n--- /v1/completions (model: $COMP_MODEL) ---"

R2=$(do_authed_request "$GWPOD_N7" "http://localhost:8000/v1/completions" "POST" \
    "{\"model\":\"${COMP_MODEL}\",\"prompt\":\"Return exactly the word READY\",\"max_tokens\":8,\"temperature\":0}" \
    "$GATEWAY_TOKEN")
COMP_HTTP=$(echo "$R2" | cut -d'|' -f1)
COMP_BODY=$(echo "$R2" | cut -d'|' -f2-)

if [ "$COMP_HTTP" = "200" ]; then
    CHOICE_TEXT=$(echo "$COMP_BODY" | grep -o '"text":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
    RESP_MODEL=$(echo "$COMP_BODY" | grep -o '"model":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
    if [ -n "$CHOICE_TEXT" ]; then
        pass "Gateway /v1/completions: HTTP 200, text=\"$(echo "$CHOICE_TEXT" | head -c 50)\""
    else
        fail "Gateway /v1/completions: HTTP 200 but empty completion"
    fi

    # Check for auth/model errors in response
    ERROR_CHECK=$(echo "$COMP_BODY" | grep -oiE 'not found|unauthorized|forbidden|authentication|invalid token' || true)
    if [ -z "$ERROR_CHECK" ]; then
        pass "Response does not contain auth/model errors"
    else
        fail "Response contains error: $ERROR_CHECK"
    fi

    # Validate completion response model matches requested model
    validate_response_model "$COMP_MODEL" "$RESP_MODEL"
elif [ "$COMP_HTTP" = "ERR" ]; then
    fail "Gateway /v1/completions: could not test (VPN)"
else
    fail "Gateway /v1/completions: expected 200, got ${COMP_HTTP}"
fi

# ============================================================
# FINAL SUMMARY
# ============================================================
echo ""
echo "══════════════════════════════════════════════════════"
echo -e "${GREEN}Passed: $PASS${NC}  ${RED}Failed: $FAIL${NC}  ${YELLOW}Warnings: $WARN${NC}"
echo "══════════════════════════════════════════════════════"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
