# FRONTEND-INTEGRATION-FE04-TEST-MATRIX
# =====================================
# R7-R5-EMG-FE-04 | 2026-07-28
# Repository: dedvmedved-dot/aither-project
# Branch: aither-v2

## Session Tests

| Test ID | Description | Expected | Actual | Status |
|---------|-------------|----------|--------|--------|
| SESSION-001 | Login + /me | 200 | 200 | PASS |
| SESSION-002 | Logout | 200 | 200 | PASS |
| SESSION-003 | /me after logout | 401 | 401 | PASS |
| SESSION-004 | Chat after logout | 401 | 401 | PASS |
| SESSION-005 | Login disabled user | 403 | 403 | PASS |
| SESSION-006 | Old token after disable | 401 | 401 | PASS |
| SESSION-008 | Demoted admin old token → admin API | 401 | 401 | PASS |

## RBAC Tests

| Test ID | Description | Expected | Actual | Status |
|---------|-------------|----------|--------|--------|
| RBAC-001 | Anonymous → admin/users | 401 | 401 | PASS |
| RBAC-002 | User → admin/users | 403 | 403 | PASS |
| RBAC-003 | Admin → admin/users | 200 | 200 | PASS |
| RBAC-008a | User with model:14b:chat → chat 14B | 200 | 200 | PASS |
| RBAC-008b | User without 32B scope → chat 32B | 403 | 403 | PASS |

## Facade Tests

| Test ID | Description | Expected | Actual | Status |
|---------|-------------|----------|--------|--------|
| FACADE-001 | Billing /me | 200 | 200 | PASS |
| FACADE-002 | Usage /me | 200 | 200 | PASS |
| FACADE-003 | Monitoring summary (admin) | 200 | 200 | PASS |
| CHAT-14B | Direct chat 14B | 200 | 200 | PASS |

## Entitlement Verification

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| tier in /me response | present | free | PASS |
| org_status in /me response | present | active | PASS |
| org_id in /me response | present | 1 | PASS |
| scopes in /me response | present | model:14b:chat,... | PASS |
| Model scope enforcement (14B) | scope required | enforced | PASS |
| Model scope enforcement (32B) | scope required | enforced | PASS |
| Role change revokes sessions | immediate | 401 | PASS |
| Disabled user sessions revoked | immediate | 403/401 | PASS |

## Summary

Session: 7/7 PASSED
RBAC: 5/5 PASSED
Facade: 4/4 PASSED
Entitlement: 8/8 PASSED
**Total: 24/24 PASSED**
