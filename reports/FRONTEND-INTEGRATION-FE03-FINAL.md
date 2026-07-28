# FRONTEND-INTEGRATION-FE03-FINAL
# ================================
# R7-R5-EMG-FE-03 | 2026-07-28
# Repository: dedvmedved-dot/aither-project
# Branch: aither-v2
# SHA: 5fa4df7

## Status
IMPLEMENTATION COMPLETE

## Sections Completed

| S | Description | Status |
|---|-------------|--------|
| S2 | Rollback chat route → direct upstream | DONE |
| S3 | FE-02 audit correction | DONE |
| S4 | Remove entitlement fallbacks | DONE |
| S5 | Session lifecycle + logout fix | DONE |
| S6 | Gateway facade cleanup (orgs→501, pending routes) | DONE |
| S7 | RAG entitlement (scopes in identity) | DONE |
| S8 | BFF Dockerfile: pin digest, remove TRANSITIONING | DONE |
| S9 | Canonical manifests | DONE |
| S10 | RBAC testing | DONE |
| S13 | Evidence + reports | DONE |

## Key Fixes

### Chat Route Rollback (S2)
- Chat: Browser → Portal Backend → direct upstream (14B) or nginx proxy (32B)
- NOT routed through Gateway
- Server-side credentials from K8s Secret (aither-portal-upstream)
- No raw API keys, no delegation JWT for chat

### Entitlement Fallbacks Removed (S4)
- Empty org_id → 403 "entitlement_missing"
- Empty scopes → 403 "entitlement_missing"
- Empty tier → 403 "entitlement_missing"
- User creation requires org_id + scopes + org validation

### Session Lifecycle (S5)
- Every authenticated request checks: session exists, not revoked, not expired, user not disabled
- Logout revokes session by full token hash
- Disabled user → all sessions revoked

## Commit Chain (append-only, FE-03)
```
5fa4df7 fix: S5 — logout revokes full token hash
594ac15 fix: S6-S8 — Gateway facade cleanup, RAG, BFF Dockerfile
6c35b2c fix: S5 — session lifecycle
af63aea fix: S4 — remove entitlement fallbacks
6738e35 fix: ROLLBACK chat route — Gateway→direct upstream
67ad284 docs: BFF recovery report + test matrix (FE-02)
```

## Acceptable Outcome
```
R7-R5-EMG-FE-03: IMPLEMENTATION COMPLETE
PRODUCTION CHAT: DIRECT ROUTE RESTORED
FRONTEND: CANDIDATE COMPLETE
CHANGE-0022: REMAINS DEFERRED
GATEWAY MODEL CUTOVER: NOT PERFORMED
PENDING EXTERNAL CONNECTOR AUDIT
```
