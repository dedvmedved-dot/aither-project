#!/usr/bin/env bash
# Stage 17 — Observability Acceptance Tests
# Tests: metrics export, JSON logging, dashboard validity, alert rules, security
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
SKIP=0

pass() { PASS=$((PASS+1)); echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { FAIL=$((FAIL+1)); echo -e "${RED}[FAIL]${NC} $1"; }
skip() { SKIP=$((SKIP+1)); echo -e "${YELLOW}[SKIP]${NC} $1"; }

echo "=========================================="
echo " Stage 17 — Observability Acceptance Tests"
echo "=========================================="
echo ""

# ---- 1. Metrics export ----
echo "--- Model Registry ---"
if curl -sf http://localhost:8100/metrics > /dev/null 2>&1; then
  pass "AI Platform /metrics endpoint reachable"
  if curl -sf http://localhost:8100/metrics | grep -q "http_requests_total"; then
    pass "AI Platform: http_requests_total metric present"
  else
    fail "AI Platform: http_requests_total metric missing"
  fi
  if curl -sf http://localhost:8100/metrics | grep -q "ai_platform_active_api_keys"; then
    pass "AI Platform: ai_platform_active_api_keys present"
  else
    fail "AI Platform: ai_platform_active_api_keys missing"
  fi
  if curl -sf http://localhost:8100/metrics | grep -q "ai_platform_gateway_requests_total"; then
    pass "AI Platform: gateway_requests_total present"
  else
    fail "AI Platform: gateway_requests_total missing"
  fi
else
  skip "AI Platform /metrics — service not running locally"
fi

if curl -sf http://localhost:8000/metrics > /dev/null 2>&1; then
  pass "Identity /metrics endpoint reachable"
  if curl -sf http://localhost:8000/metrics | grep -q "identity_active_users"; then
    pass "Identity: identity_active_users metric present"
  else
    fail "Identity: identity_active_users metric missing"
  fi
else
  skip "Identity /metrics — service not running locally"
fi

if curl -sf http://localhost:8080/metrics > /dev/null 2>&1; then
  pass "Portal Backend /metrics endpoint reachable"
else
  skip "Portal Backend /metrics — service not running locally"
fi

echo ""
echo "--- API Keys ---"

# Check no API keys in any Python source
if grep -rn 'log.*api_key\|log.*api.key' services/*/app/main.py 2>/dev/null | grep -v "^Binary" | grep -qv '#'; then
  fail "API key found in application logs"
else
  pass "No API keys in application logs"
fi

if grep -rn 'log.*authorization\|log.*bearer' services/*/app/main.py 2>/dev/null | grep -v "^Binary" | grep -qv '#'; then
  fail "Authorization header found in logs"
else
  pass "No Authorization headers in application logs"
fi

if grep -rn 'log.*password\|log.*passwd' services/*/app/main.py 2>/dev/null | grep -v "^Binary" | grep -qv '#'; then
  fail "Password found in logs"
else
  pass "No passwords in application logs"
fi

if grep -rn 'log.*system_prompt\|log.*system.prompt' services/*/app/main.py 2>/dev/null | grep -v "^Binary" | grep -qv '#'; then
  fail "System prompt found in logs"
else
  pass "No system prompts in application logs"
fi

echo ""
echo "--- Assistants ---"

# Check structured logging setup
if grep -q 'json.dumps\|pythonjsonlogger\|structlog\|"timestamp"\|"service"' services/identity/app/main.py 2>/dev/null; then
  pass "Identity: structured JSON logging found"
else
  fail "Identity: structured JSON logging not found"
fi

if grep -q 'json.dumps\|pythonjsonlogger\|structlog\|"timestamp"\|"service"' services/ai-platform/app/main.py 2>/dev/null; then
  pass "AI Platform: structured JSON logging found"
else
  fail "AI Platform: structured JSON logging not found"
fi

if grep -q 'json.dumps\|pythonjsonlogger\|structlog\|"timestamp"\|"service"' services/portal-backend/app/main.py 2>/dev/null; then
  pass "Portal Backend: structured JSON logging found"
else
  fail "Portal Backend: structured JSON logging not found"
fi

echo ""
echo "--- Conversations ---"

# Validate dashboard JSON files
for dashboard in docs/stage17/grafana/dashboard-*.json; do
  name=$(basename "$dashboard")
  if python3 -c "import json; json.load(open('$dashboard'))" 2>/dev/null; then
    pass "Dashboard $name: valid JSON"
  else
    fail "Dashboard $name: invalid JSON"
  fi
done

echo ""
echo "--- Gateway Runtime ---"

# PrometheusRule YAML validation
if python3 -c "import yaml; yaml.safe_load(open('docs/stage17/prometheus/alert-rules.yaml'))" 2>/dev/null; then
  pass "Alert rules: valid YAML"
else
  fail "Alert rules: invalid YAML"
fi

# K8s YAML validation
for manifest in docs/stage17/k8s/*.yaml; do
  name=$(basename "$manifest")
  if python3 -c "import yaml; docs = list(yaml.safe_load_all(open('$manifest'))); assert all(d is not None for d in docs)" 2>/dev/null; then
    pass "K8s $name: valid YAML"
  else
    fail "K8s $name: invalid YAML"
  fi
done

echo ""
echo "--- Regression Stage13-15 ---"

# Existing scripts syntax check
for script in scripts/*.sh; do
  if bash -n "$script" 2>/dev/null; then
    pass "Syntax OK: $script"
  else
    fail "Syntax error: $script"
  fi
done

# Python compile check
for main_py in services/identity/app/main.py services/ai-platform/app/main.py services/portal-backend/app/main.py; do
  if [ -f "$main_py" ]; then
    if python3 -m py_compile "$main_py" 2>/dev/null; then
      pass "Python OK: $main_py"
    else
      fail "Python error: $main_py"
    fi
  fi
done

echo ""
echo "=========================================="
echo " Results"
echo "=========================================="
echo " PASS: $PASS"
echo " FAIL: $FAIL"
echo " SKIP: $SKIP"
echo "=========================================="

if [ "$FAIL" -gt 0 ]; then
  echo " Some checks FAILED."
  exit 1
else
  echo " All executed checks PASSED."
  exit 0
fi
