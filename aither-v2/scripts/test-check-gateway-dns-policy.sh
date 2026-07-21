#!/bin/bash
# Aither Gateway dnsPolicy — Acceptance Gate Negative Tests
# Tests the dnsPolicy validation logic from check-gateway-32b.sh in isolation.
# Does NOT require a live cluster.
#
# Usage: bash scripts/test-check-gateway-dns-policy.sh
# Exit code: 0 = all tests pass, 1 = any test fails

set -uo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

PASS=0
FAIL=0

pass() { echo -e "${GREEN}PASS${NC} $1"; PASS=$((PASS+1)); }
fail() { echo -e "${RED}FAIL${NC} $1"; FAIL=$((FAIL+1)); }

echo "══════════════════════════════════════════════════════"
echo "  Aither Gateway — dnsPolicy Acceptance Gate Tests"
echo "══════════════════════════════════════════════════════"

# This function reproduces the exact fail-closed logic from check-gateway-32b.sh
# Parameters:
#   $1 — simulated dnsPolicy value
#   $2 — simulated kubectl error (1 = error, 0 = success)
# Returns: 0 = PASS, 1 = FAIL
validate_dns_policy() {
    local value="$1"
    local kubectl_error="${2:-0}"

    # Simulate kubectl error
    if [ "$kubectl_error" = "1" ]; then
        return 1  # fail "Could not read Gateway dnsPolicy (kubectl error)"
    fi

    # Empty value
    if [ -z "$value" ]; then
        return 1  # fail "dnsPolicy is empty (expected ClusterFirst)"
    fi

    # ClusterFirst — the only valid value
    if [ "$value" = "ClusterFirst" ]; then
        return 0  # pass "dnsPolicy: ClusterFirst"
    fi

    # Default — explicitly rejected
    if [ "$value" = "Default" ]; then
        return 1  # fail "dnsPolicy: Default workaround is not allowed..."
    fi

    # Everything else
    return 1  # fail "dnsPolicy: $value (expected ClusterFirst)"
}

echo ""
echo "── Negative Tests ──"

# Case 1: ClusterFirst — must PASS
echo ""
echo "--- Case 1: ClusterFirst ---"
if validate_dns_policy "ClusterFirst" 0; then
    pass "ClusterFirst → PASS (expected)"
else
    fail "ClusterFirst → FAIL (expected PASS)"
fi

# Case 2: Default — must FAIL
echo "--- Case 2: Default ---"
if validate_dns_policy "Default" 0; then
    fail "Default → PASS (expected FAIL)"
else
    pass "Default → FAIL (expected)"
fi

# Case 3: kubectl error — must FAIL
echo "--- Case 3: kubectl error ---"
if validate_dns_policy "" 1; then
    fail "kubectl error → PASS (expected FAIL)"
else
    pass "kubectl error → FAIL (expected)"
fi

# Case 4: empty value — must FAIL
echo "--- Case 4: empty value ---"
if validate_dns_policy "" 0; then
    fail "empty → PASS (expected FAIL)"
else
    pass "empty → FAIL (expected)"
fi

# Case 5: unexpected value — must FAIL
echo "--- Case 5: unexpected value (None) ---"
if validate_dns_policy "None" 0; then
    fail "None → PASS (expected FAIL)"
else
    pass "None → FAIL (expected)"
fi

# Case 6: ClusterFirstWithHostNet — must FAIL
echo "--- Case 6: unexpected value (ClusterFirstWithHostNet) ---"
if validate_dns_policy "ClusterFirstWithHostNet" 0; then
    fail "ClusterFirstWithHostNet → PASS (expected FAIL)"
else
    pass "ClusterFirstWithHostNet → FAIL (expected)"
fi

# Summary
echo ""
echo "══════════════════════════════════════════════════════"
if [ "$FAIL" -gt 0 ]; then
    echo -e "${RED}Passed: $PASS  Failed: $FAIL${NC}"
    exit 1
else
    echo -e "${GREEN}Passed: $PASS  Failed: $FAIL${NC}"
    exit 0
fi
