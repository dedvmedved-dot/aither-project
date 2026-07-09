#!/bin/bash
# 03-security.sh — тесты безопасности
set -e
PASS=0; FAIL=0
check() { if [ "$1" = "0" ]; then echo "✅ $2"; PASS=$((PASS+1)); else echo "❌ $2 ($3)"; FAIL=$((FAIL+1)); fi; }

echo "=== Security tests ==="

# Dev login отключён
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost/api/v1/auth/dev/login -H "Content-Type: application/json" -d '{"email":"test"}')
[ "$CODE" = "404" ]; check $? "Dev login disabled (404)" "$CODE"

# SQLi защита (должен быть 401, не 500)
CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost/api/v1/orgs?search='+OR+1=1--")
[ "$CODE" = "401" ]; check $? "SQLi attempt returns 401 (not 500)" "$CODE"

# XSS защита
CODE=$(curl -s -o /dev/null -w "%{http_code}" 'http://localhost/api/v1/orgs?name=<script>alert(1)</script>')
[ "$CODE" = "401" ]; check $? "XSS attempt returns 401 (not 500)" "$CODE"

echo "---"
echo "Результат: $PASS/$((PASS+FAIL))"
[ "$FAIL" -eq 0 ] || exit 1
