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
| 14B chat (model response) | ⚠️ PARTIAL — upstream 401 (AUTH-UPSTREAM-VALID-01) |
| 32B completion (BFF flow) | ✅ PASSED — auth/scope/upstream BFF→Gateway route verified |
| 32B completion (model response) | ⚠️ PARTIAL — upstream 401 (AUTH-UPSTREAM-VALID-01) |
| 32B chat adapter (BFF flow) | ✅ PASSED — auth/scope/adapter→Gateway route verified |
| 32B chat adapter (model response) | ⚠️ PARTIAL — upstream 401 (AUTH-UPSTREAM-VALID-01) |
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

### Key Findings

1. **BFF flow confirmed** — auth middleware, scope enforcement, upstream routing, and status code propagation work correctly for all endpoints.
2. **Upstream auth blocked** — test-only internal upstream tokens return 401. Real vLLM/Gateway auth tokens not deployed. Finding AUTH-UPSTREAM-VALID-01 remains PARTIAL.
3. **Rate limiting active** — confirmed 429 after 10 requests in 60s window.
4. **Full token lifecycle** — create (once) → list (metadata) → revoke → blocked — all PASSED.
5. **Portal/BFF-only architecture** — confirmed no direct vLLM/Gateway access.
6. **32B labeled as adapter** — no native 32B chat claimed.

### Gate

```
Stage 08: PARTIAL / WAITING FOR CHATGPT AUDIT
```
