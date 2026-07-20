# E2E Acceptance Report

## Stage 08 — MVP End-to-End Runtime Acceptance

### Summary

| Area | Result |
|---|---|
| Portal deployment & health | ✅ PASSED — 1/1 Running, /health → 200 |
| Login (admin session) | ✅ PASSED |
| Token create (raw token once) | ✅ PASSED |
| Token list (metadata only) | ✅ PASSED |
| Models with Bearer token | ✅ PASSED — HTTP 200 |
| 14B chat (BFF flow) | ✅ PASSED — auth/scope/upstream BFF route verified |
| 14B chat (model response) | ✅ PASSED — HTTP 200, "Hello from 14b" |
| 32B completion (BFF flow) | ✅ PASSED — auth/scope/upstream BFF→Gateway route verified |
| 32B completion (model response) | ✅ PASSED — HTTP 200, "Hello from 32b." |
| 32B chat adapter (BFF flow) | ✅ PASSED — auth/scope/adapter→Gateway route verified |
| 32B chat adapter (model response) | ✅ PASSED — HTTP 200, "Hello from 32b adapter" |
| Rate limit (10 req/60s → 429) | ✅ PASSED — 10×200 + 5×429 confirmed |
| Token revoke | ✅ PASSED — HTTP 200 → revoked |
| Revoked token blocked | ✅ PASSED — HTTP 401 |
| No secrets committed | ✅ PASSED |
| Forbidden zones unchanged | ✅ PASSED |

### Evidence Inventory

| Evidence | Status |
|---|---|
| e2e-environment-inventory.txt | PASSED |
| e2e-portal-health.txt | PASSED |
| e2e-login-success.txt | PASSED |
| e2e-token-create-redacted.txt | PASSED |
| e2e-token-list-metadata-only.txt | PASSED |
| e2e-models-with-token.txt | PASSED |
| e2e-14b-chat-response.txt | PARTIAL / BFF FLOW PASSED |
| e2e-32b-completion-response.txt | PARTIAL / BFF FLOW PASSED |
| e2e-32b-chat-adapter-response.txt | PARTIAL / BFF FLOW PASSED |
| e2e-rate-limit-still-429.txt | PASSED |
| e2e-token-revoke-and-block.txt | PASSED |
| e2e-no-secret-leak-check.txt | PASSED |
| e2e-forbidden-scope-check.txt | PASSED |

### Corrective 1 — Evidence (New)

| Evidence | Status |
|---|---|
| e2e-upstream-auth-secret-inventory.txt | PASSED |
| e2e-bff-rollout-after-secret-update.txt | PASSED |
| e2e-14b-chat-response-retest.txt | PASSED |
| e2e-32b-completion-response-retest.txt | PASSED |
| e2e-32b-chat-adapter-response-retest.txt | PASSED |
| e2e-auth-upstream-valid-summary.txt | PASSED / AUTH-UPSTREAM-VALID-01 RESOLVED |
| e2e-no-secret-leak-check-corrective-1.txt | PASSED |
| e2e-forbidden-scope-check-corrective-1.txt | PASSED |

### Corrective 1 — Upstream Internal Auth Resolution

**Commit:** 6b284235a5816d90077683ec1504eb18e8265209

**Runtime operation:**
- Secret inventory checked.
- Secret `aither-bff-auth` updated: `BFF_14B_UPSTREAM_AUTH_TOKEN` and `BFF_32B_GATEWAY_AUTH_TOKEN` changed from test-only (length 23) to real VLLM_API_KEY (length 64).
- BFF rollout restarted: YES.

**Retest results:**
- 14B chat: **PASSED** — HTTP 200, "Hello from 14b"
- 32B completion: **PASSED** — HTTP 200, "Hello from 32b."
- 32B chat adapter: **PASSED** — HTTP 200, "Hello from 32b adapter"

**Decision before ChatGPT audit (superseded by external audit):**
```
Stage 08: COMPLETED BY HERMES / WAITING FOR CHATGPT AUDIT
```

### External ChatGPT Audit Decision

**Date:** 2026-07-20
**Commit audited:** 6b284235a5816d90077683ec1504eb18e8265209
**Method:** GitHub connector

**Decision:**
- Stage 08 Corrective 1: **PASSED / CONNECTOR VERIFIED**
- AUTH-UPSTREAM-VALID-01: **PASSED / CONNECTOR VERIFIED**
- BFF-TOKEN-01: **PASSED / CONNECTOR VERIFIED**
- Stage 08: **PASSED WITH FINDINGS / CONNECTOR VERIFIED**
- Stage 09: **NOT APPROVED**
- PROD-READY-01: **OPEN**

**Accepted evidence:**
1. Runtime Secret inventory checked.
2. aither-bff-auth exists.
3. BFF_14B_UPSTREAM_AUTH_TOKEN exists and was updated at runtime.
4. BFF_32B_GATEWAY_AUTH_TOKEN exists and was updated at runtime.
5. Runtime Secret patch was not committed.
6. BFF rollout restarted successfully.
7. BFF pod is 1/1 Running.
8. /health returns HTTP 200.
9. 14B chat through Portal/BFF returns HTTP 200 and non-empty real model response.
10. 32B completion through Portal/BFF/Gateway returns HTTP 200 and non-empty real model response.
11. 32B chat adapter through Portal/BFF/Gateway returns HTTP 200 and non-empty adapter response.
12. 32B chat is adapter over completion, not native 32B chat.
13. Raw API tokens and upstream tokens are redacted.
14. No secrets, kubeconfig or VPN configs committed.
15. BFF code was not changed.
16. Portal code was not changed.
17. GitHub manifests were not changed.
18. vLLM/GPU/TP/Gateway/Redis/OAuth/Monitoring were not modified.
19. Stage 09 was not started.

### Remaining Findings (not closed)

| Finding | Status |
|---|---|
| GW-32B-REPLICA-01 | PARTIAL (one nginx-gateway-32b replica CrashLoopBackOff) |
| GW-IMG-01 | RISK ACCEPTED / PARTIAL |
| GW-SC-01 | PARTIAL |
| AUTH-REDIS-FAIL-01 | PARTIAL |
| AUTH-TOKEN-PERSIST-01 | PARTIAL |
| BFF-RL-REDIS-FAIL-01 | PARTIAL |
| BFF-RL-RESET-TTL-01 | MINOR FINDING |
| PROD-READY-01 | OPEN |

### Gate

```
Stage 08: PASSED WITH FINDINGS / CONNECTOR VERIFIED
Stage 09: NOT APPROVED
PROD-READY-01: OPEN
```
