# Aither Portal — Acceptance Report

## Stage 07.2 — Portal UI with Auth, Token Management and Chat Access

### Summary

| Area | Status |
|---|---|
| Portal deployment | ✅ PASSED — 1/1 Running |
| Portal service | ✅ PASSED — :80 ClusterIP |
| Portal → BFF proxy | ✅ PASSED — /health, /api/v1/* routes |
| Login (admin session) | ✅ PASSED |
| Me (session check) | ✅ PASSED |
| Logout | ✅ PASSED |
| Token create | ✅ PASSED — raw token shown once |
| Token list | ✅ PASSED — metadata only, no raw token |
| Token revoke | ✅ PASSED |
| Models list (auth) | ✅ PASSED |
| Chat 14B (BFF flow) | ✅ PASSED / UPSTREAM AUTH NOT TESTED |
| Chat 32B adapter (BFF flow) | ✅ PASSED / UPSTREAM AUTH NOT TESTED |
| BFF-only access | ✅ PASSED — no direct vLLM/Gateway |
| Token not persisted | ✅ PASSED — no localStorage/sessionStorage |
| No secrets committed | ✅ PASSED |
| Forbidden scopes | ✅ PASSED |
| 32B not claimed native | ✅ PASSED — labeled as adapter |
| Source/ConfigMap alignment | ✅ PASSED — all 4 files MATCH |

### Evidence Inventory

| Evidence | Status |
|---|---|
| portal-manifest-dry-run.txt | PASSED |
| portal-rollout-status.txt | PASSED |
| portal-pods-after.txt | PASSED |
| portal-service-after.yaml | PASSED |
| portal-configmap-source-alignment.txt | PASSED |
| portal-health-via-proxy.txt | PASSED |
| portal-login-page-load.txt | PASSED |
| portal-auth-login-success.txt | PASSED |
| portal-auth-me-success.txt | PASSED |
| portal-auth-logout.txt | PASSED |
| portal-token-create-once-redacted.txt | PASSED |
| portal-token-list-no-raw-token.txt | PASSED |
| portal-token-revoke.txt | PASSED |
| portal-models-list-auth.txt | PASSED |
| portal-chat-14b-request.txt | PASSED / UPSTREAM AUTH NOT TESTED |
| portal-chat-32b-adapter-request.txt | PASSED / UPSTREAM AUTH NOT TESTED |
| portal-32b-native-not-claimed.txt | PASSED |
| portal-bff-only-access-check.txt | PASSED |
| portal-token-not-persisted-check.txt | PASSED |
| portal-no-secret-leak-check.txt | PASSED |
| portal-forbidden-scope-check.txt | PASSED |
| **portal-ui-token-list-render-check.txt** | PASSED |
| **portal-ui-model-select-render-check.txt** | PASSED |
| **portal-ui-navigation-check.txt** | PASSED |

### Key Findings

1. **Source/ConfigMap alignment restored** — ConfigMap in portal-mvp.yaml now matches tools/portal/* exactly (SHA256 verified, all 4 files MATCH).
2. **Raw token security** — token shown once, no localStorage/sessionStorage persistence.
3. **BFF-only architecture** — portal routes exclusively through BFF; no direct vLLM/Gateway URLs.
4. **32B chat correctly labeled** as "chat adapter over completion" — no native claim.
5. **Upstream auth not tested** — internal upstream tokens remain test-only (AUTH-UPSTREAM-VALID-01 PARTIAL).

### Gate

```
Stage 07.2: PASSED WITH FINDINGS / CONNECTOR VERIFIED
Stage 08: NOT APPROVED
```

### External Audit Decision

```
Date: 2026-07-20
Commit audited: 03b1a1bf604fbfb15ab798d61c9867de5cba35d2
Method: GitHub connector
Decision:
- Stage 07.2 Corrective 2: PASSED / CONNECTOR VERIFIED
- PORTAL-CM-ALIGN-01: PASSED / CONNECTOR VERIFIED
- Stage 07.2 Portal: PASSED WITH FINDINGS / CONNECTOR VERIFIED
- Stage 08: NOT APPROVED
Accepted evidence:
1. Portal deployed and accessible.
2. Portal uses BFF-only reverse proxy.
3. Login/logout/me work through BFF.
4. Token create/list/revoke UI works.
5. Raw token shown once and not persisted.
6. Token list renders from BFF {"tokens":[...]}.
7. Model selector renders from BFF {"models":[...]}.
8. Navigation works via App.showPage().
9. 32B is labeled as chat adapter over completion.
10. portal-mvp.yaml inline ConfigMap matches tools/portal/*.
11. SHA256 alignment: index.html/app.js/styles.css/nginx.conf all MATCH.
12. Forbidden runtime areas were not modified.
Remaining findings (unchanged):
- AUTH-UPSTREAM-VALID-01 — PARTIAL
- AUTH-REDIS-FAIL-01 — PARTIAL
- AUTH-TOKEN-PERSIST-01 — PARTIAL
- AUTH-OAUTH-01 — OUT OF SCOPE / FUTURE
- BFF-RL-REDIS-FAIL-01 — PARTIAL
- BFF-RL-RESET-TTL-01 — MINOR FINDING
- BFF-TOKEN-01 — NOT COLLECTED
- BFF-AUTH-01 — PARTIAL
- PROD-READY-01 — OPEN
```
