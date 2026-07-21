#!/usr/bin/env bash
# Aither — Bootstrap Initial Administrator
#
# Creates the first administrator account for the Identity service.
# Requires bcrypt to be installed.
#
# Usage:
#   bash scripts/bootstrap-admin.sh
#
# Environment variables:
#   AITHER_IDENTITY_URL   — Identity service URL (default: http://localhost:8000)
#   AITHER_ADMIN_USER     — Admin username (default: admin)
#   AITHER_ADMIN_PASS     — Admin password (prompted if not set)
#
# After bootstrap:
#   1. Change the default password immediately after first login.
#   2. Do not commit admin credentials to the repository.

set -euo pipefail

IDENTITY_URL="${AITHER_IDENTITY_URL:-http://localhost:8000}"
ADMIN_USER="${AITHER_ADMIN_USER:-admin}"

echo "═══════════════════════════════════════════════════"
echo "  Aither — Bootstrap Initial Administrator"
echo "═══════════════════════════════════════════════════"
echo ""
echo "Identity Service: ${IDENTITY_URL}"
echo "Admin Username:   ${ADMIN_USER}"
echo ""

# ── Check prerequisites ──
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 is required for password hashing"
    exit 1
fi

if ! command -v curl &>/dev/null; then
    echo "ERROR: curl is required for API calls"
    exit 1
fi

# ── Get password ──
if [ -z "${AITHER_ADMIN_PASS:-}" ]; then
    read -s -p "Enter admin password (min 8 chars): " ADMIN_PASS
    echo ""
    read -s -p "Confirm admin password: " ADMIN_PASS_CONFIRM
    echo ""
    if [ "${ADMIN_PASS}" != "${ADMIN_PASS_CONFIRM}" ]; then
        echo "ERROR: Passwords do not match"
        exit 1
    fi
    if [ ${#ADMIN_PASS} -lt 8 ]; then
        echo "ERROR: Password must be at least 8 characters"
        exit 1
    fi
else
    ADMIN_PASS="${AITHER_ADMIN_PASS}"
fi

# ── Hash password ──
echo ""
echo "Hashing password with bcrypt..."
PASS_HASH=$(python3 -c "
import bcrypt
print(bcrypt.hashpw('${ADMIN_PASS}'.encode(), bcrypt.gensalt(rounds=12)).decode())
")

if [ -z "${PASS_HASH}" ]; then
    echo "ERROR: Failed to hash password"
    exit 1
fi

# ── Check identity service health ──
echo "Checking Identity service health..."
if ! curl -sf "${IDENTITY_URL}/health" > /dev/null 2>&1; then
    echo "ERROR: Identity service is not reachable at ${IDENTITY_URL}"
    echo "  Make sure the service is running and try again."
    exit 1
fi
echo "  Identity service is healthy."

# ── Bootstrap ──
echo "Creating initial administrator '${ADMIN_USER}'..."
HTTP_CODE=$(curl -s -o /tmp/aither-bootstrap-response.json -w "%{http_code}" \
    -X POST "${IDENTITY_URL}/v1/identity/bootstrap" \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"${ADMIN_USER}\", \"password_hash\": \"${PASS_HASH}\"}")

if [ "${HTTP_CODE}" = "201" ]; then
    echo ""
    echo "✅ SUCCESS: Administrator '${ADMIN_USER}' created."
    echo ""
    echo "  You can now log in at the Portal with:"
    echo "    Username: ${ADMIN_USER}"
    echo "    Password: <the password you entered>"
    echo ""
    echo "  ⚠️  IMPORTANT: Change the password after first login."
    echo "  ⚠️  Never commit credentials to the repository."
    echo ""
    cat /tmp/aither-bootstrap-response.json
elif [ "${HTTP_CODE}" = "400" ]; then
    echo "⚠️  Bootstrap already completed or misconfigured."
    cat /tmp/aither-bootstrap-response.json
    echo ""
    echo "  If an administrator already exists, use the login page."
    echo "  To reset, delete the identity database and restart the service."
else
    echo "❌ FAILED (HTTP ${HTTP_CODE})"
    cat /tmp/aither-bootstrap-response.json
    echo ""
    exit 1
fi

rm -f /tmp/aither-bootstrap-response.json
