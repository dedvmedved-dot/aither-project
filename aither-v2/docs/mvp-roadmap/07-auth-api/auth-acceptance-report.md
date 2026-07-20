# Aither MVP — Auth Acceptance Report

## Stage 07.1 — Auth / API Token / Agent Access Baseline

### Summary

| Area | Status |
|---|---|
| Central auth middleware | IMPLEMENTED (Corrective 1: scope enforcement added) |
| Admin login/logout | IMPLEMENTED (Corrective 1: login bug fixed) |
| API token creation | IMPLEMENTED |
| API token listing | IMPLEMENTED |
| API token revocation | IMPLEMENTED |
| Agent access with Bearer token | IMPLEMENTED (Corrective 1: scope enforcement added) |
| User token isolation (upstream) | IMPLEMENTED (PASSED code review) |
| 32B chat adapter | IMPLEMENTED (Corrective 1: scope enforcement added) |
| 32B chat adapter scope | model:32b:chat-adapter required |
| 14B chat scope | model:14b:chat required |
| 32B completion scope | model:32b:completion required |
| 14B completions | BLOCKED (422) — use /api/v1/chat instead |
| Rate limit integration | PRESERVED |
| Source/ConfigMap alignment | VERIFIED (both syntax OK, functional match) |
| Runtime acceptance | NOT COLLECTED (VPN unstable) |

### Endpoints Added

| Method | Path | Auth | Rate Limited | Description |
|---|---|---|---|---|
| POST | /api/v1/auth/login | No | No | Admin login |
| POST | /api/v1/auth/logout | No | No | Admin logout |
| GET | /api/v1/auth/me | Cookie | No | Current session info |
| POST | /api/v1/tokens | Admin | No | Create API token |
| GET | /api/v1/tokens | Admin | No | List API tokens |
| DELETE | /api/v1/tokens/{id} | Admin | No | Revoke API token |
| GET | /api/v1/models | Token/Admin | Yes | List models |
| POST | /api/v1/chat | Token/Admin | Yes | Chat (14B native, 32B adapter) |
| POST | /api/v1/completions | Token/Admin | Yes | Completions (14B/32B) |

### Endpoints Preserved (No Change)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /health | No | Health check (unchanged) |

### Evidence Inventory

| Evidence | Status | Notes |
|---|---|---|
| bff-auth-manifest-dry-run.txt | COLLECTED | Manifest valid |
| bff-auth-secret-redacted.txt | COLLECTED | Secret created, redacted |
| bff-rollout-after-auth.txt | NOT COLLECTED | VPN drop |
| bff-pods-after-auth.txt | NOT COLLECTED | VPN drop |
| auth-health-no-auth-200.txt | NOT COLLECTED | VPN drop |
| auth-models-no-token-401.txt | NOT COLLECTED | VPN drop |
| auth-login-success.txt | NOT COLLECTED | VPN drop |
| token-create-success-redacted.txt | NOT COLLECTED | VPN drop |
| token-list-no-raw-token.txt | NOT COLLECTED | VPN drop |
| token-hash-storage-check.txt | NOT COLLECTED | VPN drop |
| token-revoke-check.txt | NOT COLLECTED | VPN drop |
| agent-models-valid-token-200.txt | NOT COLLECTED | VPN drop |
| agent-14b-chat-valid-token.txt | NOT COLLECTED | VPN drop |
| agent-32b-completion-valid-token.txt | NOT COLLECTED | VPN drop |
| agent-32b-chat-adapter-valid-token.txt | NOT COLLECTED | VPN drop |
| agent-wrong-token-401.txt | NOT COLLECTED | VPN drop |
| rate-limit-still-works-429.txt | NOT COLLECTED | VPN drop |
| no-user-token-forwarding-check.txt | PASSED (code review) | Source verified |
| no-secret-leak-check.txt | PASSED (git grep) | No secrets committed |
| forbidden-scope-check.txt | PASSED (git diff) | Scope confirmed |

### Key Findings

1. **VPN instability** prevented runtime evidence collection. Evidence must be re-collected after VPN restore.
2. **Auth config** verified: 6 env vars from Secret `aither-bff-auth`.
3. **User token isolation** confirmed by source code review: `_upstream_headers()` uses `BFF_*_UPSTREAM_AUTH_TOKEN`, never user token.
4. **32B chat** is an adapter over completion, NOT native chat. Documented separately.
5. **BFF-AUTH-01** (old finding) is functionally addressed but NOT closed until ChatGPT audits.

### Gate

```
Stage 07.1: COMPLETED BY HERMES / WAITING FOR CHATGPT AUDIT
Stage 07.2 Portal: NOT APPROVED
Stage 08: NOT APPROVED
```
