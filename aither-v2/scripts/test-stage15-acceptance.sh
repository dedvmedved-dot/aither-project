#!/usr/bin/env bash
# Aither Stage 15 — Acceptance Tests
#
# Tests the Identity and Portal Backend services.
# Requires:
#   - IDENTITY_URL (default: http://localhost:8000) — Identity service
#   - PORTAL_URL (default: http://localhost:8001) — Portal Backend
#   - bcrypt (python3) for password hashing
#
# Run:
#   bash scripts/test-stage15-acceptance.sh
#
# Exit codes:
#   0 — all tests passed
#   1 — one or more tests failed

set -euo pipefail

IDENTITY_URL="${IDENTITY_URL:-http://localhost:8000}"
PORTAL_URL="${PORTAL_URL:-http://localhost:8001}"
PASS=0
FAIL=0
AUTH_TOKEN=""
TEST_USER="testuser-stage15"
TEST_PASS="testpass123"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "═══════════════════════════════════════════════════"
echo "  Aither Stage 15 — Acceptance Tests"
echo "═══════════════════════════════════════════════════"
echo "  Identity: ${IDENTITY_URL}"
echo "  Portal:   ${PORTAL_URL}"
echo ""

check() {
    local desc="$1" result="$2"
    if [ "$result" = "PASS" ]; then
        echo -e "  ${GREEN}PASS${NC} ${desc}"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}FAIL${NC} ${desc} — $3"
        FAIL=$((FAIL + 1))
    fi
}

# ── 1. Health check (Identity) ──
echo "--- 1. Health / Ready / Version ---"
HEALTH=$(curl -sf "${IDENTITY_URL}/health" 2>&1 || echo "FAILED")
check "GET /health (identity)" \
    $(echo "$HEALTH" | grep -q '"ok"' && echo "PASS" || echo "FAIL") \
    "$HEALTH"

READY=$(curl -sf "${IDENTITY_URL}/ready" 2>&1 || echo "FAILED")
check "GET /ready (identity)" \
    $(echo "$READY" | grep -q '"ok"' && echo "PASS" || echo "FAIL") \
    "$READY"

VERSION=$(curl -sf "${IDENTITY_URL}/version" 2>&1 || echo "FAILED")
check "GET /version (identity)" \
    $(echo "$VERSION" | grep -q '"1.0.0"' && echo "PASS" || echo "FAIL") \
    "$VERSION"

# ── 2. Portal Backend health ──
echo "--- 2. Portal Backend Health ---"
PHEALTH=$(curl -sf "${PORTAL_URL}/health" 2>&1 || echo "FAILED")
check "GET /health (portal-backend)" \
    $(echo "$PHEALTH" | grep -q '"ok"' && echo "PASS" || echo "FAIL") \
    "$PHEALTH"

PVERSION=$(curl -sf "${PORTAL_URL}/version" 2>&1 || echo "FAILED")
check "GET /version (portal-backend)" \
    $(echo "$PVERSION" | grep -q '"1.0.0"' && echo "PASS" || echo "FAIL") \
    "$PVERSION"

# ── 3. Bootstrap admin ──
echo "--- 3. Bootstrap Administrator ---"
ADMIN_PASS_HASH=$(python3 -c "import bcrypt; print(bcrypt.hashpw('adminpass123'.encode(), bcrypt.gensalt(rounds=12)).decode())" 2>/dev/null || echo "")

if [ -z "$ADMIN_PASS_HASH" ]; then
    check "Create initial admin (bootstrap)" "FAIL" "bcrypt not available"
else
    BOOTSTRAP=$(curl -sf -X POST "${IDENTITY_URL}/v1/identity/bootstrap" \
        -H "Content-Type: application/json" \
        -d "{\"username\": \"admin\", \"password_hash\": \"${ADMIN_PASS_HASH}\"}" 2>&1 || echo "FAILED")
    # May fail if already bootstrapped — ok
    check "Create initial admin" \
        $(echo "$BOOTSTRAP" | grep -q -E '(created|already|exists)' && echo "PASS" || echo "FAIL") \
        "$BOOTSTRAP"
fi

# ── 4. Login as admin ──
echo "--- 4. Authentication ---"
LOGIN=$(curl -sf -X POST "${IDENTITY_URL}/v1/identity/auth" \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "adminpass123"}' 2>&1 || echo "FAILED")
check "Admin login (valid credentials)" \
    $(echo "$LOGIN" | grep -q '"token"' && echo "PASS" || echo "FAIL") \
    "$LOGIN"

AUTH_TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null || echo "")
check "Extract auth token" \
    $( [ -n "$AUTH_TOKEN" ] && echo "PASS" || echo "FAIL") \
    "No token returned"

# ── 5. Login with wrong password ──
echo "--- 5. Negative Auth ---"
WRONG_LOGIN=$(curl -sf -X POST "${IDENTITY_URL}/v1/identity/auth" \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "wrongpassword123"}' 2>&1 || echo "FAILED")
check "Login with wrong password (should fail)" \
    $(echo "$WRONG_LOGIN" | grep -qi 'invalid' && echo "PASS" || echo "FAIL") \
    "$WRONG_LOGIN"

# ── 6. Get current user (me) ──
echo "--- 6. User Info ---"
ME=$(curl -sf "${IDENTITY_URL}/v1/identity/me" \
    -H "Authorization: Bearer ${AUTH_TOKEN}" 2>&1 || echo "FAILED")
check "GET /me (authenticated)" \
    $(echo "$ME" | grep -q '"username"' && echo "PASS" || echo "FAIL") \
    "$ME"

check "Role is administrator" \
    $(echo "$ME" | grep -q '"administrator"' && echo "PASS" || echo "FAIL") \
    "$ME"

# ── 7. Portal Backend proxy (login via BFF) ──
echo "--- 7. Portal Backend Proxy ---"
BFF_LOGIN=$(curl -sf -X POST "${PORTAL_URL}/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "adminpass123"}' 2>&1 || echo "FAILED")
check "Portal Backend login proxy" \
    $(echo "$BFF_LOGIN" | grep -q '"token"' && echo "PASS" || echo "FAIL") \
    "$BFF_LOGIN"

BFF_ME=$(curl -sf "${PORTAL_URL}/api/v1/auth/me" \
    -H "Authorization: Bearer $(echo $BFF_LOGIN | python3 -c 'import sys,json; print(json.load(sys.stdin).get(\"token\",\"\"))' 2>/dev/null)" 2>&1 || echo "FAILED")
check "Portal Backend /me proxy" \
    $(echo "$BFF_ME" | grep -q '"username"' && echo "PASS" || echo "FAIL") \
    "$BFF_ME"

# ── 8. Portal Backend /api/v1/status ──
echo "--- 8. Portal Backend Status ---"
STATUS=$(curl -sf "${PORTAL_URL}/api/v1/status" 2>&1 || echo "FAILED")
check "GET /api/v1/status (portal)" \
    $(echo "$STATUS" | grep -q '"operational"' && echo "PASS" || echo "FAIL") \
    "$STATUS"

# ── 9. Portal Backend /ready ──
echo "--- 9. Portal Backend Ready ---"
PREADY=$(curl -sf "${PORTAL_URL}/ready" 2>&1 || echo "FAILED")
check "GET /ready (portal-backend)" \
    $(echo "$PREADY" | grep -q '"ok"' && echo "PASS" || echo "FAIL") \
    "$PREADY"

# ── Summary ──
echo ""
echo "═══════════════════════════════════════════════════"
echo "  Results: ${PASS} PASS, ${FAIL} FAIL"
echo "═══════════════════════════════════════════════════"

exit $FAIL
