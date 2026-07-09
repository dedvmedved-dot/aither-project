#!/bin/bash
# 02-api.sh — функциональные тесты API
set -e
PASS=0; FAIL=0
check() { if [ "$1" = "0" ]; then echo "✅ $2"; PASS=$((PASS+1)); else echo "❌ $2 ($3)"; FAIL=$((FAIL+1)); fi; }

echo "=== API tests ==="

# Models (публичный)
curl -sf http://localhost/api/v1/models | python3 -c "import sys,json; d=json.load(sys.stdin); assert len(d.get('data',[]))>=2" 2>/dev/null
check $? "GET /api/v1/models returns >=2 models"

# Health
curl -sf http://localhost/api/v1/health | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='ok'" 2>/dev/null
check $? "GET /api/v1/health returns ok"

# Auth required
CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/v1/orgs)
[ "$CODE" = "401" ]; check $? "GET /api/v1/orgs requires auth (401)" "$CODE"

echo "---"
echo "Результат: $PASS/$((PASS+FAIL))"
[ "$FAIL" -eq 0 ] || exit 1
