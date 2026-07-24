# Stage 16 — Security Notes

## Threat Model (Beta v0.9)

| Threat | Mitigation | Status |
|---|---|---|
| API Key theft | SHA-256 hashed storage, full key never stored | ✅ |
| Horizontal access | Ownership check on every assistant/conversation/key | ✅ |
| Privilege escalation | Role enforcement (admin role required for model management) | ✅ |
| SQL injection | Parameterized queries (SQLite parameter substitution) | ✅ |
| Token forgery | HMAC-SHA256 signed tokens, constant-time comparison | ✅ |
| Password cracking | bcrypt (12 rounds) | ✅ |
| XSS | Content-Type: application/json on API responses | ✅ |
|| CORS abuse | Configurable origins (default: `http://localhost:3000`, restrict in production) | ✅ |

## API Key Protection

1. Full key shown **only once** at creation
2. SHA-256 hash stored — not reversible
3. Prefix-only in list responses
4. `last_used_at` tracked
5. Revoked keys rejected immediately
6. Full key never appears in logs (no logging of `Authorization` header)

## Object Ownership

Every assistant, conversation, and API Key has an `owner_user_id`.
All operations verify that the authenticated user matches the owner.
Admin can view metadata but not full secrets.

## Role Enforcement

| Operation | Required Role |
|---|---|
| Create/update/delete models | Administrator |
| List models | Any authenticated user |
| Create/revoke API Keys | Any authenticated user (own keys only) |
| Create/edit assistants | Any authenticated user (own assistants only) |
| Create/view chats | Any authenticated user (own chats only) |
| Admin: view all users | Administrator |

## CORS Configuration

All services support configurable CORS via environment variables:

| Service | Variable | Default | Production |
|---|---|---|---|
| Portal Backend | `PORTAL_CORS_ORIGIN` | `http://localhost:3000` | Set to Portal Frontend URL |
| AI Platform | `AI_PLATFORM_CORS_ORIGIN` | `http://localhost:3000` | Set to Portal Frontend URL |

**Important:** The default is `http://localhost:3000` (NOT `*`). In production, set to the
exact Portal Frontend origin. Multiple origins require a reverse proxy configuration.

## Known Limitations (Beta v0.9)

1. **CORS:** Restricted to `http://localhost:3000` by default. Configure via environment variables for production.
2. **Transport security:** No HTTPS by default. Add Ingress with TLS for production.
3. **Rate limiting:** API Key usage not rate-limited (future: integrate with existing Redis rate limiter)
4. **Audit logging:** Basic logging only. No audit trail for admin actions.
5. **Secrets rotation:** No automated secret rotation (Stage 18 concern)
6. **SQLite:** Single-file database. Not suitable for HA. Plan PostgreSQL migration (Stage 18).

## What is deferred to Stage 18

- PostgreSQL migration
- Full audit logging
- Secrets rotation
- KMS integration for API Key encryption
- mTLS between services
- OAuth/OIDC integration
