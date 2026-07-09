#!/bin/bash
# portal-security-check.sh — автоматизированная проверка безопасности портала
# Использование: bash portal-security-check.sh http://<TARGET>/

set -euo pipefail

TARGET="${1:-}"
if [ -z "$TARGET" ]; then
  echo "Usage: $0 http://<TARGET>/"
  echo "Example: $0 http://130.17.1.90/"
  exit 1
fi

# Убираем trailing slash
TARGET="${TARGET%/}"

PASS=0
FAIL=0
WARN=0

green() { echo -e "\033[32m$1\033[0m"; }
red()   { echo -e "\033[31m$1\033[0m"; }
yellow(){ echo -e "\033[33m$1\033[0m"; }
bold()  { echo -e "\033[1m$1\033[0m"; }

check() {
  local desc="$1"; shift
  local expected="$1"; shift
  local actual
  actual="$("$@")" 2>/dev/null || actual="ERROR"
  if [ "$actual" = "$expected" ]; then
    green "  ✅ $desc"
    PASS=$((PASS + 1))
  elif [ -n "$expected" ]; then
    red "  ❌ $desc — expected '$expected', got '$actual'"
    FAIL=$((FAIL + 1))
  else
    yellow "  ⚠️  $desc — $actual"
    WARN=$((WARN + 1))
  fi
}

echo
bold "=== Security Check: $TARGET ==="
echo

# ──────────────────────────────────────────────
# 1. API endpoints without auth
# ──────────────────────────────────────────────
bold "── API endpoints (unauthorized)"
for ep in /api/v1/users /api/v1/chats /api/v1/orgs; do
  check "$ep → 401" "401" curl -s -o /dev/null -w "%{http_code}" "$TARGET$ep"
done

# 2. Dev-login
bold "── Dev-login"
check "/auth/dev/login → 403" "403" curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d '{"name":"test"}' "$TARGET/auth/dev/login"

# 3. Port 3000
bold "── Direct BFF access"
if timeout 3 bash -c "echo >/dev/tcp/${TARGET#http://}/3000" 2>/dev/null; then
  red "  ❌ Port 3000 → OPEN (should be closed or localhost-only)"
  FAIL=$((FAIL + 1))
else
  PASS=$((PASS + 1))
  green "  ✅ Port 3000 → filtered/closed"
fi

# 4. Security headers
bold "── Security headers"
HEADERS=$(curl -sI "$TARGET/" 2>/dev/null)
for hdr in "X-Frame-Options: DENY" "X-Content-Type-Options: nosniff"; do
  expected_val="${hdr#*: }"
  hdr_name="${hdr%%:*}"
  actual_val=$(echo "$HEADERS" | grep -i "^$hdr_name:" | head -1 | sed "s/^[^:]*: *//; s///" || echo "")
  if echo "$actual_val" | grep -qi "$expected_val"; then
    green "  ✅ $hdr"
    PASS=$((PASS + 1))
  else
    red "  ❌ $hdr — missing or wrong ($actual_val)"
    FAIL=$((FAIL + 1))
  fi
done

# 5. CORS
bold "── CORS"
CORS_ACTUAL=$(curl -sI -H "Origin: https://evil.com" "$TARGET/api/v1/status" 2>/dev/null | grep -i "^Access-Control-Allow-Origin:" | sed 's/.*: *//; s///')
if [ "$CORS_ACTUAL" = "*" ]; then
  red "  ❌ CORS → * (wildcard — cross-origin attack possible)"
  FAIL=$((FAIL + 1))
elif [ -n "$CORS_ACTUAL" ]; then
  green "  ✅ CORS → $CORS_ACTUAL (restricted)"
  PASS=$((PASS + 1))
else
  yellow "  ⚠️  CORS header not present"
  WARN=$((WARN + 1))
fi

# 6. CSP
bold "── Content-Security-Policy"
CSP=$(echo "$HEADERS" | grep -i "^Content-Security-Policy:" | head -1 || true)
if [ -n "$CSP" ]; then
  green "  ✅ CSP present"
  PASS=$((PASS + 1))
else
  yellow "  ⚠️  CSP missing (XSS risk)"
  WARN=$((WARN + 1))
fi

# ──────────────────────────────────────────────
# RESULTS
# ──────────────────────────────────────────────
echo
bold "=== Summary ==="
green "  Passed: $PASS"
red "  Failed: $FAIL"
yellow "  Warnings: $WARN"
echo

if [ "$FAIL" -gt 0 ]; then
  red "❌ SECURITY ISSUES FOUND — action required"
  exit 1
else
  green "✅ All critical checks passed"
  exit 0
fi
