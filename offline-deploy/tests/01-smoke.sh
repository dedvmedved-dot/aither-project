#!/bin/bash
# 01-smoke.sh — дымовые тесты (все компоненты живы?)
set -e
PASS=0; FAIL=0
check() { if [ "$1" = "0" ]; then echo "✅ $2"; PASS=$((PASS+1)); else echo "❌ $2"; FAIL=$((FAIL+1)); fi; }

echo "=== Smoke tests ==="
curl -sf http://localhost:30900/health &>/dev/null; check $? "Gateway :30900 health"
curl -sf http://localhost:32293/health &>/dev/null; check $? "vLLM 14B :32293 health"
curl -sf http://localhost:32294/health &>/dev/null; check $? "vLLM 32B :32294 health"
curl -sf http://localhost/api/v1/health &>/dev/null; check $? "Portal :80 health"
curl -sf http://localhost/api/v1/models &>/dev/null; check $? "Portal models endpoint"
echo "---"
echo "Результат: $PASS/$((PASS+FAIL))"
[ "$FAIL" -eq 0 ] || exit 1
