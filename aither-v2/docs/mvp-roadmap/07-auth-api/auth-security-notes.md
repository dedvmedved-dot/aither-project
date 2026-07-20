# Aither MVP — Auth Security Notes

## Security Model

### Authentication
- Admin: password-based login with SHA-256 hash comparison
- Agent: Bearer token (`athr_xxx`) verified via HMAC-SHA256

### Token Storage
- Raw tokens: NEVER stored (shown once at creation)
- Stored: HMAC-SHA256 hash only
- Hash secret: from Kubernetes Secret `AUTH_TOKEN_HASH_SECRET`
- Redis keys: no raw tokens, no reversible data

### Credential Isolation
- User/admin tokens: used only for BFF authentication
- Upstream credentials: `BFF_14B_UPSTREAM_AUTH_TOKEN` and `BFF_32B_GATEWAY_AUTH_TOKEN`
- User token NEVER forwarded to vLLM or nginx-gateway

### Session Security
- Cookie: httponly, samesite=strict
- Session TTL: 24 hours (Redis-backed)
- Session ID: UUID4 (128 bits random)

### Logging
- Raw passwords: NOT logged
- Raw API tokens: NOT logged
- Session IDs: partially logged (first 12 chars)
- Token creation events: logged (without raw token)

## Known Limitations (MVP)

### 1. SHA-256 for Password Hash
Status: ACCEPTED FOR MVP
Details: Admin password hash uses single SHA-256, not bcrypt/argon2. This is acceptable for MVP because:
- Hash stored in Kubernetes Secret (not in git)
- Access to Secret requires cluster-level permissions
- Password can be rotated easily

### 2. No OAuth
Status: OUT OF SCOPE
Details: OAuth integration is planned as a separate stage after Portal UI.

### 3. Redis-only Token Storage
Status: PARTIAL
Details: Tokens exist only in Redis. If Redis is lost, all tokens must be re-created.
Finding: AUTH-TOKEN-PERSIST-01 — PARTIAL

### 4. No TLS/HTTPS
Status: ACCEPTED FOR MVP
Details: All traffic is within Kubernetes cluster network (ClusterIP). TLS will be added in a hardening stage.

### 5. No Rate Limiting on Auth Endpoints
Status: ACCEPTED FOR MVP
Details: Auth login endpoint is not rate-limited. Acceptable for internal MVP.

## Secrets Management

| Secret | Where | Committed? |
|---|---|---|
| ADMIN_USERNAME | `aither-bff-auth` K8s Secret | ❌ No (example has REPLACE_ME) |
| ADMIN_PASSWORD_HASH | `aither-bff-auth` K8s Secret | ❌ No (example has REPLACE_ME) |
| SESSION_SECRET | `aither-bff-auth` K8s Secret | ❌ No (example has REPLACE_ME) |
| AUTH_TOKEN_HASH_SECRET | `aither-bff-auth` K8s Secret | ❌ No (example has REPLACE_ME) |
| BFF_14B_UPSTREAM_AUTH_TOKEN | `aither-bff-auth` K8s Secret | ❌ No (example has REPLACE_ME) |
| BFF_32B_GATEWAY_AUTH_TOKEN | `aither-bff-auth` K8s Secret | ❌ No (example has REPLACE_ME) |

## Threat Model (MVP Scope)

| Threat | Mitigation |
|---|---|
| Token theft from Redis | Only HMAC hashes stored; raw token not recoverable |
| Token reuse after revoke | `revoked` flag checked on every request |
| Direct upstream access | User tokens not valid for upstream; upstream uses separate credentials |
| Secret leak via git | Example file uses REPLACE_ME; real secret created via kubectl |
| Brute force login | Constant-time comparison (hmac.compare_digest) |
| Session hijacking | httponly cookie, random session ID |
