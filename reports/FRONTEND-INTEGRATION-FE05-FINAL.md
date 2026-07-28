# FRONTEND-INTEGRATION-FE05-FINAL
# ================================
# R7-R5-EMG-FE-05 | 2026-07-28
# Repository: dedvmedved-dot/aither-project
# Branch: aither-v2

## Status
IMPLEMENTATION COMPLETE — DEPLOYED + VERIFIED

## Sections Completed

| S | Description | Status |
|---|-------------|--------|
| S2 | Strict model allowlist (qwen-14b, qwen-32b-base) | DONE |
| S3 | Usage dashboard — dead models card removed | DONE |
| S4 | Monitoring — security/billing removed (Gateway missing) | DONE |
| S5 | Operator RBAC — _require_monitoring_role() | DONE |
| S6 | RAG defense-in-depth — portal-backend enforcement | DONE |
| S7 | Reproducible build — --require-hashes lock file | DONE |
| S8 | Canonical Deployment manifests — all pinned | DONE |
| S9 | Frontend alignment — pages array, operator nav, dead UI removed | DONE |
| S10 | Test gate — 14/14 PASSED | DONE |
| S11 | Evidence — test matrix + final report | DONE |

## Key Fixes

### Model Allowlist (S2)
- Strict: only qwen-14b and qwen-32b-base
- Unknown model → 400 BEFORE upstream
- Upstream call count = 0 for unknown models

### Operator RBAC (S5)
- `_require_monitoring_role()`: admin + operator → 200, user → 403
- `_require_admin()`: admin only → for drain/undrain/user CRUD
- Nav: operator sees Monitoring, not Admin

### Frontend Alignment (S9)
- Pages array includes admin, billing, usage, rag, monitoring
- Operator role badge: "Operator"
- Nav shows Monitoring for operator
- Removed: /usage/me/models call
- Removed: monitoring/security, monitoring/billing calls
- Error states: explicit messages instead of silent catch

### Reproducible Build (S7)
- requirements.lock with exact versions + SHA256 hashes
- Dockerfile: `pip install --require-hashes -r requirements.lock`
- All direct + transitive dependencies pinned

## Deployed Image Digests

| Service | Digest |
|---------|--------|
| aither-portal-backend | sha256:5a43355cd2603b9c44e6b9c5f6c1ddb2ff5af15e24b67d3cc722e199506faa15 |
| aither-portal-frontend | sha256:8275e4073ee159e275d111df76a937e77957bbc8a3ac9e125f7eab41c004175c |
| aither-identity | sha256:3a916b25666faf5e2d8d4a98b6965698796a8f87c77eaa6b6d5a39df6a2cafb1 |

## Test Gate: 14/14 PASSED

- Model allowlist: 4/4
- Operator RBAC: 4/4
- Session: 6/6

## Acceptable Outcome
```
R7-R5-EMG-FE-05: IMPLEMENTATION COMPLETE
PRODUCTION CHAT: DIRECT ROUTE (PRESERVED)
FRONTEND INTEGRATION: CANDIDATE COMPLETE
CHANGE-0022: REMAINS DEFERRED
GATEWAY MODEL CUTOVER: NOT PERFORMED
PENDING EXTERNAL CONNECTOR AUDIT
```
