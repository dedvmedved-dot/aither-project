# Identity & Authentication — Stage 15

## User Model

Users are stored in an SQLite database (`identity.db`) with the following schema:

| Field | Type | Description |
|---|---|---|
| `id` | INTEGER (PK, AUTO) | Unique user ID |
| `username` | TEXT (UNIQUE, NOT NULL) | Login name |
| `password` | TEXT (NOT NULL) | bcrypt hash |
| `role` | TEXT (NOT NULL) | `administrator` or `user` |
| `created_at` | TEXT | ISO timestamp |
| `disabled` | INTEGER | `0` = active, `1` = disabled |

## Roles

| Role | Privileges |
|---|---|
| **Administrator** | Full access — create/manage users, view all, bootstrap |
| **User** | Limited access — login, view own profile, system status |

## Password Storage

- **Algorithm:** bcrypt
- **Rounds:** 12 (configurable in code via `bcrypt.gensalt(rounds=12)`)
- **Storage:** Only the bcrypt hash is stored in the database
- **Verification:** `bcrypt.checkpw(plaintext, stored_hash)`

Salting is built into bcrypt — each password gets a unique salt.

## Authentication Process

```
1. User submits username + password
2. Identity Service looks up user by username
3. If user not found → 401 "Invalid credentials"
4. If user disabled → 403 "Account disabled"
5. bcrypt.checkpw(password, stored_hash)
6. If mismatch → 401 "Invalid credentials"
7. If match → generate HMAC-signed token → 200
```

## Token Format

Identity Service uses a stateless HMAC-signed token with this payload:

```json
{
  "uid": 1,
  "sub": "admin",
  "role": "administrator",
  "iat": 1700000000,
  "exp": 1700086400,
  "jti": "random-token-id"
}
```

The payload is HMAC-SHA256 signed with `IDENTITY_SECRET_KEY`.

### Session Management

Sessions are tracked in a `sessions` table:

| Field | Type | Description |
|---|---|---|
| `id` | INTEGER (PK) | Session ID |
| `user_id` | INTEGER (FK) | References users.id |
| `token_hash` | TEXT (UNIQUE) | SHA256 of token JTI |
| `created_at` | TEXT | Session creation time |
| `expires_at` | TEXT | Expiration time |
| `revoked` | INTEGER | `0` = active, `1` = revoked |

### Token Lifecycle

- **Creation:** On successful login
- **Validation:** On each authenticated request (stateless HMAC check)
- **Expiration:** After `IDENTITY_TOKEN_TTL` seconds (default: 86400 = 24h)
- **Revocation:** On logout (token JTI marked as revoked in sessions table)

## Bootstrap

The first administrator is created via the `/v1/identity/bootstrap` endpoint.

**Procedure:**
1. Set `IDENTITY_ADMIN_USER` and `IDENTITY_ADMIN_PASS` (bcrypt hash) env vars
2. Start the Identity Service
3. Call `POST /v1/identity/bootstrap`
4. Endpoint checks that no admin exists → creates one
5. Returns 201 on success, 400 if admin already exists

**CLI tool:** `scripts/bootstrap-admin.sh` automates this with password prompt,
bcrypt hashing, and API call.

**Security notes:**
- Bootstrap is one-shot — only works before any admin is created
- To reset: delete `identity.db` and restart the service
- Default credentials must be changed after first login (future Stage 16 feature)
