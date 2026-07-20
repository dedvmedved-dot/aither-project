#!/bin/bash
# Aither Gateway 32B — Comprehensive Diagnostic Script
# Usage: bash scripts/check-gateway-32b.sh [namespace]
#
# Performs all checks required by Stage 10 Part 2 acceptance:
#   - K8s Service, Deployment, Pods
#   - DNS policy and upstream consistency (4 levels)
#   - nginx syntax and config
#   - API behaviour (auth, unsupported, authenticated E2E)
#   - Git/runtime/running config equality
#
# Requires: kubectl, curl, jq
# Secrets: GATEWAY_TOKEN env var for authenticated tests (not printed)
set -euo pipefail

NS="${1:-aither-inference}"
MANIFEST_DIR="manifests/mvp-roadmap/04-gateway"
MANIFEST_FILE="${MANIFEST_DIR}/nginx-gateway-32b-hardened.yaml"
GIT_ROOT="."

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

cleanup_pods() {
    local tmp_pods=$(kubectl -n "$NS" get pods -l temp-diag=true -o name 2>/dev/null)
    if [ -n "$tmp_pods" ]; then
        kubectl -n "$NS" delete pod $tmp_pods --grace-period=1 --wait=false 2>/dev/null || true
    fi
}

echo "══════════════════════════════════════════════════════"
echo "  Aither Gateway 32B — Comprehensive Diagnostic Check"
echo "  Namespace: $NS"
echo "  $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "══════════════════════════════════════════════════════"

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
SPEC_REPLICAS=$(kubectl -n "$NS" get deployment nginx-gateway-32b -o jsonpath='{.spec.replicas}' 2>/dev/null || echo 0)
READY_REPLICAS=$(kubectl -n "$NS" get deployment nginx-gateway-32b -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo 0)
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
    pass "Gateway pod on n7: $GWPOD_N7"
else
    fail "No gateway pod on n7"
fi

# 2.9 Gateway pod on n8
GWPOD_N8=$(kubectl -n "$NS" get pods -l app=nginx-gateway -o wide 2>/dev/null | grep "n8" | awk '{print $1}' || echo "")
if [ -n "$GWPOD_N8" ]; then
    pass "Gateway pod on n8: $GWPOD_N8"
else
    fail "No gateway pod on n8"
fi

# 2.10 Both pods Ready
POD_PHASE_N7=$(kubectl -n "$NS" get pod "$GWPOD_N7" -o jsonpath='{.status.phase}' 2>/dev/null || echo "")
POD_PHASE_N8=$(kubectl -n "$NS" get pod "$GWPOD_N8" -o jsonpath='{.status.phase}' 2>/dev/null || echo "")
if [ "$POD_PHASE_N7" = "Running" ] && [ "$POD_PHASE_N8" = "Running" ]; then
    pass "Both gateway pods Running (n7: $POD_PHASE_N7, n8: $POD_PHASE_N8)"
else
    fail "Gateway pods not Running (n7: ${POD_PHASE_N7:-N/A}, n8: ${POD_PHASE_N8:-N/A})"
fi

# ============================================================
# SECTION 3: DNS and Upstream Consistency (4 levels)
# ============================================================
echo -e "\n── 3. DNS/Upstream Consistency ──"

# 3.11 dnsPolicy
DNSPOLICY=$(kubectl -n "$NS" get deployment nginx-gateway-32b -o jsonpath='{.spec.template.spec.dnsPolicy}' 2>/dev/null || echo "ClusterFirst")
if [ "$DNSPOLICY" = "Default" ]; then
    pass "dnsPolicy: Default (n7-compatible workaround)"
else
    fail "dnsPolicy: $DNSPOLICY (expected Default for n7 compatibility)"
fi

# Extract upstreams
# Level 1: Service ClusterIP
SVC_UPSTREAM="${SVC_CIDR}:8000"

# Level 2: Git manifest upstream (for /v1/completions)
GIT_UPSTREAM=""
if [ -f "$MANIFEST_FILE" ]; then
    # Use awk to extract the proxy_pass for location /v1/completions
    GIT_UPSTREAM=$(awk '/location \/v1\/completions/,/}/' "$MANIFEST_FILE" | grep proxy_pass | sed 's/.*http:\/\///;s/;.*//')
fi
if [ -n "$GIT_UPSTREAM" ]; then
    pass "Git manifest upstream: $GIT_UPSTREAM"
else
    fail "Could not extract Git manifest upstream"
fi

# Level 3: Runtime ConfigMap upstream
RUNTIME_UPSTREAM=""
for pod in "$GWPOD_N7"; do
    [ -z "$pod" ] || [ "$pod" = "" ] && continue
    RUNTIME_UPSTREAM=$(kubectl -n "$NS" get configmap nginx-gateway-32b -o jsonpath='{.data.nginx\.conf}' 2>/dev/null | awk '/location \/v1\/completions/,/}/' | grep proxy_pass | sed 's/.*http:\/\///;s/;.*//')
    break
done
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

# 4.20 Health endpoint (/healthz local)
for pod in "$GWPOD_N7" "$GWPOD_N8"; do
    [ -z "$pod" ] && continue
    GW_NODE=$(kubectl -n "$NS" get pod "$pod" -o jsonpath='{.spec.nodeName}' 2>/dev/null || echo "unknown")
    HZ=$(kubectl -n "$NS" exec "$pod" -- sh -c 'curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/healthz --connect-timeout 5 --max-time 10' 2>/dev/null || echo "ERR")
    if [ "$HZ" = "200" ]; then
        pass "Gateway /healthz on $GW_NODE: $HZ"
    elif [ "$HZ" = "ERR" ]; then
        warn "Gateway /healthz on $GW_NODE: could not test"
    else
        fail "Gateway /healthz on $GW_NODE: expected 200, got $HZ"
    fi
done

# ============================================================
# SECTION 5: API Behaviour
# ============================================================
echo -e "\n── 5. API Tests ──"

# 5.21 No auth → 401
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

# 5.22 Unsupported /v1/chat/completions → 422
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

# 5.23 Authenticated /v1/models through Gateway
echo -e "\n── 6. Authenticated Tests ──"

# Get token from environment or skip
GATEWAY_TOKEN="${GATEWAY_TOKEN:-}"
if [ -z "$GATEWAY_TOKEN" ]; then
    warn "GATEWAY_TOKEN not set — skipping authenticated tests (set GATEWAY_TOKEN=xxx to enable)"
else
    # 5.23 Models list
    MODELS_RESPONSE=""
    for pod in "$GWPOD_N7" "$GWPOD_N8"; do
        [ -z "$pod" ] && continue
        GW_NODE=$(kubectl -n "$NS" get pod "$pod" -o jsonpath='{.spec.nodeName}' 2>/dev/null || echo "unknown")
        MODELS_RESPONSE=$(kubectl -n "$NS" exec "$pod" -- sh -c "
            curl -s -w '\n%{http_code}' \
                http://localhost:8000/v1/models \
                -H 'Authorization: Bearer ${GATEWAY_TOKEN}' \
                --connect-timeout 10 --max-time 30" 2>/dev/null || echo "ERR")
        MODELS_HTTP=$(echo "$MODELS_RESPONSE" | tail -1)
        MODELS_BODY=$(echo "$MODELS_RESPONSE" | head -n -1)
        if [ "$MODELS_HTTP" = "200" ]; then
        ACTUAL_MODEL_ID=$(echo "$MODELS_BODY" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4 2>/dev/null || echo "unknown")
            if [ -n "$ACTUAL_MODEL_ID" ] && [ "$ACTUAL_MODEL_ID" != "null" ]; then
                pass "Gateway /v1/models on $GW_NODE: HTTP 200, model ID: $ACTUAL_MODEL_ID"
            else
                warn "Gateway /v1/models on $GW_NODE: HTTP 200 but no model ID in response"
            fi
        elif [ "$MODELS_HTTP" = "ERR" ]; then
            fail "Gateway /v1/models on $GW_NODE: could not test (VPN)"
        else
            fail "Gateway /v1/models on $GW_NODE: expected 200, got $MODELS_HTTP"
        fi
        if [ -n "$ACTUAL_MODEL_ID" ] && [ "$ACTUAL_MODEL_ID" != "null" ]; then
            break
        fi
    done

    # 5.24 Authenticated completion
    for pod in "$GWPOD_N7" "$GWPOD_N8"; do
        [ -z "$pod" ] && continue
        GW_NODE=$(kubectl -n "$NS" get pod "$pod" -o jsonpath='{.spec.nodeName}' 2>/dev/null || echo "unknown")

        # Use actual model ID from /v1/models (fallback to qwen-32b-base)
        COMP_MODEL_ID="${ACTUAL_MODEL_ID:-qwen-32b-base}"

        COMP_RESPONSE=$(kubectl -n "$NS" exec "$pod" -- sh -c "
            curl -s -w '\n%{http_code}' \
                -X POST http://localhost:8000/v1/completions \
                -H 'Content-Type: application/json' \
                -H 'Authorization: Bearer ${GATEWAY_TOKEN}' \
                -d '{\"model\":\"${COMP_MODEL_ID}\",\"prompt\":\"Return exactly the word READY\",\"max_tokens\":8,\"temperature\":0}' \
                --connect-timeout 30 --max-time 120" 2>/dev/null || echo "ERR")
        COMP_HTTP=$(echo "$COMP_RESPONSE" | tail -1)
        COMP_BODY=$(echo "$COMP_RESPONSE" | head -n -1)

        if [ "$COMP_HTTP" = "200" ]; then
            # Check for non-empty choices
            CHOICES_LEN=$(echo "$COMP_BODY" | grep -o '"text":"' | wc -l 2>/dev/null || echo 0)
            CHOICE_TEXT=$(echo "$COMP_BODY" | grep -o '"text":"[^"]*"' | head -1 | cut -d'"' -f4 2>/dev/null || echo "")
            RESP_MODEL=$(echo "$COMP_BODY" | grep -o '"model":"[^"]*"' | head -1 | cut -d'"' -f4 2>/dev/null || echo "")
            if [ "$CHOICES_LEN" -gt 0 ] && [ -n "$CHOICE_TEXT" ]; then
                pass "Gateway /v1/completions on $GW_NODE: HTTP 200, choices=$CHOICES_LEN, text=\"$(echo "$CHOICE_TEXT" | head -c 50)\""
                # 5.25 No auth/model error
                if echo "$CHOICE_TEXT" | grep -qi "not found"; then
                    fail "Response contains 'not found' — possible model ID error"
                else
                    pass "Response does not contain model errors"
                fi
            else
                fail "Gateway /v1/completions on $GW_NODE: HTTP 200 but empty choices"
            fi
            break
        elif [ "$COMP_HTTP" = "ERR" ]; then
            fail "Gateway /v1/completions on $GW_NODE: could not test (VPN)"
        else
            fail "Gateway /v1/completions on $GW_NODE: expected 200, got $COMP_HTTP"
        fi
    done
fi

# ============================================================
# FINAL SUMMARY
# ============================================================
echo ""
echo "══════════════════════════════════════════════════════"
echo -e "${GREEN}Passed: $PASS${NC}  ${RED}Failed: $FAIL${NC}  ${YELLOW}Warnings: $WARN${NC}"
echo "══════════════════════════════════════════════════════"
exit "$FAIL"
