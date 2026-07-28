# FRONTEND-INTEGRATION-FE05-TEST-MATRIX
# ======================================
# R7-R5-EMG-FE-05 | 2026-07-28

## Model Allowlist (S2)

| Test ID | Description | Expected | Actual | Status |
|---------|-------------|----------|--------|--------|
| ALLOW-001 | Unknown model 'gpt-4' | 400 | 400 | PASS |
| ALLOW-002 | Unknown model 'qwen-32b' | 400 | 400 | PASS |
| ALLOW-003 | Valid model qwen-14b | 200 | 200 | PASS |
| ALLOW-004 | Valid model qwen-32b-base | 200+ | 200 | PASS |

## Operator RBAC (S5)

| Test ID | Description | Expected | Actual | Status |
|---------|-------------|----------|--------|--------|
| OP-001 | Operator → monitoring/summary | 200 | 200 | PASS |
| OP-002 | Operator → admin/users | 403 | 403 | PASS |
| OP-003 | Operator → drain model | 403 | 403 | PASS |
| OP-004 | User → monitoring/summary | 403 | 403 | PASS |

## Session

| Test ID | Description | Expected | Actual | Status |
|---------|-------------|----------|--------|--------|
| SESSION-001 | Login + /me | 200 | 200 | PASS |
| SESSION-002 | Logout | 200 | 200 | PASS |
| SESSION-003 | /me after logout | 401 | 401 | PASS |
| SESSION-004 | Chat after logout | 401 | 401 | PASS |
| SESSION-005 | Login disabled user | 403 | 403 | PASS |
| SESSION-008 | Demoted admin old token | 401 | 401 | PASS |

## Summary
Model Allowlist: 4/4 PASSED
Operator RBAC: 4/4 PASSED
Session: 6/6 PASSED
Total: 14/14 PASSED
