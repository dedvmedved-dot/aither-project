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

**Commit:** (this commit)

**Runtime operation:**
- Secret inventory checked.
- Secret `aither-bff-auth` updated: `BFF_14B_UPSTREAM_AUTH_TOKEN` and `BFF_32B_GATEWAY_AUTH_TOKEN` changed from test-only (length 23) to real VLLM_API_KEY (length 64).
- BFF rollout restarted: YES.

**Retest results:**
- 14B chat: **PASSED** — HTTP 200, "Hello from 14b"
- 32B completion: **PASSED** — HTTP 200, "Hello from 32b."
- 32B chat adapter: **PASSED** — HTTP 200, "Hello from 32b adapter"

**Decision before ChatGPT audit:**
```
Stage 08: COMPLETED BY HERMES / WAITING FOR CHATGPT AUDIT
```

### Key Findings

1. **AUTH-UPSTREAM-VALID-01 RESOLVED** — Secret aither-bff-auth updated with real VLLM_API_KEY; all three upstream endpoints return HTTP 200 with real model responses.
2. **Full E2E flow confirmed** — Portal → BFF → vLLM/Gateway → model response works for all endpoints.
3. **Full token lifecycle** — create (once) → list (metadata) → revoke → blocked — all PASSED.
4. **Rate limiting active** — confirmed 429 after 10 requests in 60s window.
5. **Portal/BFF-only architecture** — confirmed no direct vLLM/Gateway access.
6. **32B labeled as adapter** — 32B chat is adapter over completion (text_completion object), not native 32B chat.

### Gate

```
Stage 08: COMPLETED BY HERMES / WAITING FOR CHATGPT AUDIT
Stage 09: NOT APPROVED
```
