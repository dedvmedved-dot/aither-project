# FRONTEND-INTEGRATION-FE04-FINAL
# ================================
# R7-R5-EMG-FE-04 | 2026-07-28
# Repository: dedvmedved-dot/aither-project
# Branch: aither-v2

## Status
IMPLEMENTATION COMPLETE — DEPLOYED + VERIFIED

## Sections Completed

| S | Description | Status |
|---|-------------|--------|
| S1 | Model scope enforcement in direct chat (14B/32B) | DONE |
| S2 | Identity /me returns tier, org_status, org_name | DONE |
| S3 | Entitlement fallbacks removed (COALESCE, default org, LDAP auto) | DONE |
| S4 | get_current_user() loads fresh DB rights + role-change revoke | DONE |
| S5 | Portal→Gateway facade restored (tier in delegation JWT) | DONE |
| S7 | Non-working facade routes removed (usage daily/models, admin orgs) | DONE |
| S8 | RAG exact scope enforcement (query/ingest/wiki-admin) | DONE |
| S9 | BFF Dockerfile fixed — authoritative source copy | DONE |
| S10 | Canonical image digests synchronized | DONE |
| S11 | Test gate: Session 7/7, RBAC 5/5, Facade 4/4, Entitlement 8/8 | DONE |
| S12 | Evidence: test matrix, session security report | DONE |

## Key Fixes

### Model Scope Enforcement (S1)
- Chat route: org active + tier + model-specific scope required
- 14B → requires `model:14b:chat`
- 32B → requires `model:32b:chat-adapter`
- Unknown model → 400
- Missing scope → 403 BEFORE upstream request

### Identity /me (S2)
- Now returns: org_id, org_name, org_status, tier, scopes
- Inactive org → 403
- Missing tier → 403

### Entitlement Fallbacks Removed (S3)
- No `COALESCE(o.tier, 'free')` in any login flow
- No automatic org assignment at init
- LDAP no longer auto-creates users with default org/scopes
- OAuth users without provisioning → PENDING ENTITLEMENT
- Bootstrap admin created with explicit org_id + scopes

### Fresh DB Rights (S4)
- `get_current_user()` loads role/scopes/org/tier from DB each request
- Role change → immediate session revocation (all sessions revoked)
- Disabled user → all sessions revoked
- Token payload no longer authoritative for authorization

### Facade Cleanup (S7)
- Removed: `/api/v1/usage/me/daily`, `/api/v1/usage/me/models` (Gateway missing)
- Removed: 5 `/api/v1/admin/orgs/*` routes (Gateway missing)
- Fixed: `monitoring_models()` now passes `X-Admin-Key`

### RAG Enforcement (S8)
- Exact scope checks: `rag:query`, `rag:ingest`, `rag:wiki-admin`
- wiki-ingest requires admin role
- Enforced at portal-backend BEFORE proxying to Gateway

## Deployed Image Digests

| Service | Digest |
|---------|--------|
| aither-identity | sha256:3a916b25666faf5e2d8d4a98b6965698796a8f87c77eaa6b6d5a39df6a2cafb1 |
| aither-portal-backend | sha256:286eea31b95374f6f28cdcb1a8d205db9b22a9b11aa9d1167b9fadc84f815dab |

## Test Gate: 24/24 PASSED

```
SESSION: 7/7
  SESSION-001 Login + /me = 200
  SESSION-002 Logout = 200
  SESSION-003 /me after logout = 401
  SESSION-004 Chat after logout = 401
  SESSION-005 Login disabled = 403
  SESSION-006 Old token after disable = 401
  SESSION-008 Demoted admin old token = 401

RBAC: 5/5
  RBAC-001 Anonymous = 401
  RBAC-002 User→admin = 403
  RBAC-003 Admin→admin = 200
  RBAC-008a User 14B scope = 200
  RBAC-008b User no 32B scope = 403

FACADE: 4/4
  Billing /me = 200
  Usage /me = 200
  Monitoring = 200
  Chat 14B direct = 200

ENTITLEMENT: 8/8
  tier, org_status, org_id, scopes in /me
  Model scope enforcement
  Role change revoke
  Disabled user revoke
```

## Acceptable Outcome
```
R7-R5-EMG-FE-04: IMPLEMENTATION COMPLETE
PRODUCTION CHAT: DIRECT ROUTE (PRESERVED)
CHANGE-0022: REMAINS DEFERRED
GATEWAY MODEL CUTOVER: NOT PERFORMED
PENDING EXTERNAL CONNECTOR AUDIT
```
