# FRONTEND-INTEGRATION-TEST-MATRIX
# ================================
# R7-R5-EMG-FE-02 | 2026-07-28 | SHA: 4726172

## RBAC Tests

| ID | Test | Target | Expected | Actual | Status |
|----|------|--------|----------|--------|--------|
| RBAC-001 | Anonymous → /auth/me | portal | 401 | 401 | PASS |
| RBAC-002 | Admin → /admin/users | portal | 200 | 200 | PASS |
| RBAC-003 | Admin → /billing/me | portal | 200 | 200 | PASS |
| RBAC-004 | Admin → /usage/me | portal | 200 | 200 | PASS |
| RBAC-005 | Admin → /monitoring/summary | portal | 200 | 200 | PASS |
| RBAC-006 | Admin → /chat (delegation JWT) | portal | 200 | 200 | PASS |

## Identity Tests

| ID | Test | Result |
|----|------|--------|
| ID-001 | /me returns org_id | PASS (org_id=1) |
| ID-002 | /me returns scopes | PASS |
| ID-003 | /me returns disabled | PASS (false) |
| ID-004 | Disabled user → 403 | NOT TESTED (no disabled user) |

## Deployment Tests

| ID | Test | Result |
|----|------|--------|
| DEP-001 | Identity 2/2 Ready | PASS |
| DEP-002 | Portal Backend 2/2 Ready | PASS |
| DEP-003 | Portal Frontend Ready | PASS |
| DEP-004 | Gateway remains not-primary | PASS |
| DEP-005 | Nginx config valid | PASS |
| DEP-006 | Gateway ClusterIP only | PASS |

## Security Tests

| ID | Test | Result |
|----|------|--------|
| SEC-001 | No raw API keys in portal-backend code | PASS |
| SEC-002 | Chat uses delegation JWT | PASS |
| SEC-003 | Gateway not exposed externally | PASS |
| SEC-004 | Working tree CLEAN | PASS |
