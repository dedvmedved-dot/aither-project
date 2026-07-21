# Stage 15 REST API Documentation

## Identity Service

Base URL: `http://aither-identity:8000`

### Health

```
GET /health
```

**Response 200:**
```json
{"status": "ok", "service": "identity"}
```

---

### Readiness

```
GET /ready
```

**Response 200:**
```json
{"status": "ok", "database": "connected"}
```

**Response 503:** Database unavailable

---

### Version

```
GET /version
```

**Response 200:**
```json
{"service": "aither-identity", "version": "1.0.0", "build": "stage15"}
```

---

### Bootstrap Administrator

```
POST /v1/identity/bootstrap
Content-Type: application/json

{
  "username": "admin",
  "password_hash": "$2b$12$..."
}
```

**Response 201:**
```json
{"message": "Administrator 'admin' created successfully"}
```

**Response 400:** Bootstrap already completed or env not set
**Response 409:** User already exists

---

### Login

```
POST /v1/identity/auth
Content-Type: application/json

{
  "username": "admin",
  "password": "plaintext_password"
}
```

**Response 200:**
```json
{
  "token": "<hmac_signed_token>",
  "user": {"id": 1, "username": "admin", "role": "administrator"}
}
```

**Response 401:** Invalid credentials
**Response 403:** Account disabled

---

### Logout

```
POST /v1/identity/logout
Authorization: Bearer <token>
```

**Response 200:**
```json
{"message": "Logged out"}
```

**Response 401:** Not authenticated

---

### Current User

```
GET /v1/identity/me
Authorization: Bearer <token>
```

**Response 200:**
```json
{"id": 1, "username": "admin", "role": "administrator"}
```

**Response 401:** Invalid or expired token

---

### List Users (Admin Only)

```
GET /v1/identity/users
Authorization: Bearer <admin_token>
```

**Response 200:**
```json
[
  {"id": 1, "username": "admin", "role": "administrator", "created_at": "2026-07-21", "disabled": false}
]
```

**Response 403:** Not an administrator

---

### Create User (Admin Only)

```
POST /v1/identity/users
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "username": "newuser",
  "password": "min8chars",
  "role": "user"
}
```

**Response 201:**
```json
{"message": "User 'newuser' created with role 'user'"}
```

**Response 400:** Invalid role or short password
**Response 409:** Username already exists

---

### Service Status

```
GET /v1/identity/status
```

**Response 200:**
```json
{"service": "aither-identity", "version": "1.0.0", "status": "operational — 2 users (1 administrators)"}
```

---

## Portal Backend (BFF)

Base URL: `http://aither-portal-backend:8000`

### Health

```
GET /health
```

**Response 200:**
```json
{"status": "ok", "service": "portal-backend"}
```

---

### Readiness

```
GET /ready
```

**Response 200:**
```json
{"status": "ok", "identity": "connected"}
```

**Response 503:** Identity service unreachable

---

### Version

```
GET /version
```

**Response 200:**
```json
{"service": "aither-portal-backend", "version": "1.0.0", "build": "stage15"}
```

---

### Login (Proxy)

```
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "plaintext_password"
}
```

**Response 200:**
```json
{
  "token": "<hmac_signed_token>",
  "user": {"id": 1, "username": "admin", "role": "administrator"}
}
```

**Response 401:** Invalid credentials
**Response 503:** Identity service unavailable

---

### Logout (Proxy)

```
POST /api/v1/auth/logout
Authorization: Bearer <token>
```

**Response 200:**
```json
{"message": "Logged out"}
```

---

### Current User (Proxy)

```
GET /api/v1/auth/me
Authorization: Bearer <token>
```

**Response 200:**
```json
{"id": 1, "username": "admin", "role": "administrator"}
```

---

### Aggregated Status

```
GET /api/v1/status
```

**Response 200:**
```json
{
  "status": "operational",
  "services": {
    "portal-backend": "healthy",
    "identity": {"service": "aither-identity", "version": "1.0.0", "status": "operational — 2 users (1 administrators)"}
  }
}
```

---

## Error Responses

All errors follow this format:

```json
{"detail": "Human-readable error message"}
```

HTTP status codes used:
| Code | Meaning |
|---|---|
| 200 | Success |
| 201 | Created |
| 400 | Bad request |
| 401 | Not authenticated |
| 403 | Forbidden (insufficient role) |
| 404 | Not found |
| 409 | Conflict (duplicate) |
| 503 | Service unavailable |
