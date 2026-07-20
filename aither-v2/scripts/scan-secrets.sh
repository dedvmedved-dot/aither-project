#!/bin/bash
# Aither Portal — Secret Scanner
# Usage: bash scripts/scan-secrets.sh
# Scans working tree for obvious hardcoded production secrets
# Intended for CI and local pre-commit use

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

check() {
    local desc="$1" pattern="$2" path="${3:-.}"
    local tmpfile
    tmpfile=$(mktemp)
    rg -n --color=never "$pattern" "$path" 2>/dev/null | grep -v '.env.example' | grep -v 'REPLACE_ME' | grep -v '.gitignore' > "$tmpfile" || true
    if [ -s "$tmpfile" ]; then
        echo -e "${RED}FAIL${NC} $desc"
        head -10 "$tmpfile"
        FAIL=$((FAIL + 1))
    else
        echo -e "${GREEN}PASS${NC} $desc"
        PASS=$((PASS + 1))
    fi
    rm -f "$tmpfile"
}

echo "════════════════════════════════════════"
echo "  Aither Secret Scanner"
echo "════════════════════════════════════════"

# Check 1: Hardcoded JWT secrets in typeScript files
check "Hardcoded JWT secret (portal/bff/)" \
    'JWT_SEC[[:space:]]*=[[:space:]]*\"[a-z]' portal/bff/

# Check 2: Hardcoded ADMIN_JWT_SECRET fallback
check "Hardcoded ADMIN_JWT_SECRET fallback" \
    "ADMIN_JWT_SECRET[[:space:]]*=.*\\|\\| \"[a-z]" portal/

# Check 3: docker-compose inline secrets (must use ${...})
check "docker-compose inline secrets (JWT/INVITE)" \
    'JWT_SECRET:\s*"[^$]|INVITE_CODE:\s*"[^$]' portal/docker-compose.yml

# Check 4: Hardcoded passwords in compose (must use ${...})
check "Hardcoded PG_PASSWORD in compose" \
    'PG_PASSWORD:\s*"[^$]' portal/docker-compose.yml

# Check 5: Any remaining 'REPLACE_ME' warnings
check "REPLACE_ME placeholder used as value" \
    'REPLACE_ME' . --glob '!*.example.*'

# Check 6: Check .env is gitignored
if grep -q '^\.env$' .gitignore 2>/dev/null; then
    echo -e "${GREEN}PASS${NC} .env is gitignored"
    PASS=$((PASS + 1))
else
    echo -e "${RED}FAIL${NC} .env is NOT gitignored"
    FAIL=$((FAIL + 1))
fi

echo ""
echo "════════════════════════════════════════"
echo -e "${GREEN}Passed: $PASS${NC}"
echo -e "${RED}Failed: $FAIL${NC}"
echo "════════════════════════════════════════"

exit $FAIL
