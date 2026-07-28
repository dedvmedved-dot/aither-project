# FRONTEND-INTEGRATION-FINAL — R7-R5-EMG-FE-02
# ================================================
# Date: 2026-07-28
# Repository: dedvmedved-dot/aither-project
# Branch: aither-v2
# SHA: 9cefeb5

## Sections Completed

| Section | Description | Status |
|---------|-------------|--------|
| S2 | Runtime→Git reconciliation | COMPLETE |
| S3 | BFF source tree (bff-prod SUPERSEDED) | COMPLETE |
| S4 | API key store → delegation JWT (Variant A) | COMPLETE |
| S5 | Authoritative identity model (org_id, scopes, disabled) | COMPLETE |
| S6 | Delegation JWT fix (iss/aud/scopes, TTL≤60s) | COMPLETE |
| S7 | Billing/Usage — daily/models endpoints | COMPLETE |
| S8 | Admin CRUD — users + orgs | COMPLETE |
| S9 | RAG ingest endpoints | COMPLETE |
| S10 | Monitoring endpoints (models/security/billing/dependencies) | COMPLETE |
| S11 | Frontend pages (Usage/RAG/Monitoring) | COMPLETE |
| S12 | Nginx verification | COMPLETE |
| S13 | RBAC testing | COMPLETE |
| S14 | Evidence + reports | COMPLETE |

## Key Architecture Changes

### Credential Storage (S4)
- REMOVED: `_user_api_keys: dict[str, str] = {}` in-memory cache
- REMOVED: Automatic API key creation on cache miss
- ADDED: Delegation JWT for chat (Browser → Portal Backend → Gateway → AI Platform)
- No raw API keys stored in process memory

### Identity Model (S5)
- ADDED: `organisations` table (tier, status, balance, quota)
- ADDED: `org_id`, `scopes` columns to users (migration-aware)
- `/v1/identity/me` returns: id, username, role, org_id, scopes, disabled
- Disabled user check in `_get_user_from_token`

### Delegation JWT (S6)
- `iss`: aither-bff
- `aud`: aither-gateway
- `org_id`: from identity (not "unknown")
- `scopes`: from identity (not hardcoded global)
- `tier`: from billing config
- TTL: 60 seconds

## RBAC Test Matrix

| Test | Result |
|------|--------|
| ANONYMOUS → 401 | PASS |
| ADMIN → admin/users (200) | PASS |
| ADMIN → billing/me (200) | PASS |
| ADMIN → usage/me (200) | PASS |
| ADMIN → monitoring/summary (200) | PASS |
| ADMIN → chat (200) — delegation JWT | PASS |
| ADMIN → identity/me (org_id+scopes) | PASS |

## Commit Chain (append-only)
```
9cefeb5 feat(frontend): Usage, RAG, Monitoring pages + nav visibility (S11)
fd81dee feat: S7-S10 — usage/models, monitoring endpoints, admin CRUD, RAG ingest
e9b804c feat: delegation JWT auth (S4) + authoritative identity model (S5) + JWT claims fix (S6)
b177eef chore: BFF source tree reconciliation — mark bff-prod SUPERSEDED
92b3b8b feat(frontend): Admin + Billing dashboards, monitoring summary endpoint
d986d34 feat: billing/usage/RAG endpoints + gateway schema fix
```

## Pending
- Gateway /admin/organisations endpoint (404 expected — not implemented yet)
- RAG query requires rag:query scope in delegation JWT
- Organisation isolation E2E tests (requires multi-user)
- Browser E2E full suite (S13)
