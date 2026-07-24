# API Keys — Stage 16

## Format

```
aither_<8-char hex prefix>_<64-char URL-safe base64 secret>
```

Example: `aither_a1b2c3d4_z0x9y8w7v6u5t4s3r2q1p0o9i8u7y6t5r4e3w2q1`

## Creation

1. User calls `POST /api/v1/api-keys` with a name
2. Server generates: prefix (`aither_<random 4 bytes hex>`) + secret (`token_urlsafe(48)`)
3. Full key returned **only once** in response
4. Server stores: SHA-256 hash of full key + prefix (for lookup)
5. Original secret NEVER stored

## Storage

| Field | Content |
|---|---|
| `key_prefix` | `aither_a1b2c3d4` — public identifier |
| `key_hash` | `SHA-256(full_key)` — never reversible |
| Full key | **NOT stored** — only in create response |

## Authentication

API Key can be sent as:
```http
Authorization: Bearer aither_<prefix>_<secret>
```
or:
```http
X-API-Key: aither_<prefix>_<secret>
```

## Lifecycle

1. **Create** → full key shown once
2. **List** → prefix and metadata only
3. **Use** → update `last_used_at`
4. **Revoke** → sets `revoked_at`, key immediately invalidated
5. **Expire** → optional `expires_at` date

## Security

- SHA-256 hashing (not reversible)
- Constant-time comparison via `hashlib.sha256`
- `last_used_at` tracked per request
- Full key not logged anywhere
- Revoked keys checked on every request
