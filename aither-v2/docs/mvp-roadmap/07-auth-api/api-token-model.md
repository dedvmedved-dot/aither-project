# Aither MVP — API Token Model

## Token Format

```
athr_<base64url random 32 bytes>
```

Example: `athr_5xK3pQ2mN8vR9wL4jH6fA1cD7gB0sE3yT5uW2iX8oZ9nM0vC1b`

## Generation

```python
import secrets
TP = "athr_"
raw_token = TP + secrets.token_urlsafe(32)
```

## Storage

- Raw token: NEVER stored
- Storage: `HMAC-SHA256(raw_token, AUTH_TOKEN_HASH_SECRET)` → stored in Redis
- Redis key: `aither-auth:token:<hex_hash>`
- Redis value: JSON metadata (no raw token, no hash that could be reversed)

## Metadata Fields

| Field | Type | Description |
|---|---|---|
| token_id | string | UUID4 hex (first 12 chars) — used for revocation |
| token_hash | string | HMAC-SHA256 of raw token (internal, not exposed) |
| name | string | Human-readable label |
| scopes | list[string] | Permissions (see below) |
| created_at | ISO datetime | Creation timestamp |
| last_used_at | ISO datetime | Updated on each successful auth |
| revoked | boolean | True if revoked |
| revoked_at | ISO datetime | Revocation timestamp |

## Scopes (MVP)

| Scope | Permission |
|---|---|
| `model:14b:chat` | Chat with 14B model |
| `model:32b:completion` | Completions with 32B model |
| `model:32b:chat-adapter` | Chat adapter for 32B (converts to completion) |
| `tokens:read` | List API tokens |
| `tokens:create` | Create new API tokens |
| `tokens:revoke` | Revoke API tokens |

## Admin Scope

Admin session (from login) gets `admin` scope which bypasses all scope checks.

## Token Lifecycle

```
Create -> Active -> Revoke -> Dead
              |
              +-> (optional) Expires
```

## Redis Schema

```
aither-auth:token:<hash>          -> JSON metadata
aither-auth:token:all             -> Set of all token hashes (for listing)
aither-auth:session:<session_id>  -> Admin session data (24h TTL)
```

## Security Notes

- Raw token entropy: 32 bytes = 256 bits (secrets.token_urlsafe)
- HMAC-SHA256 prevents raw token recovery from database compromise
- Scope enforcement done on every request
- Token list endpoint NEVER exposes `token_hash` or raw token
