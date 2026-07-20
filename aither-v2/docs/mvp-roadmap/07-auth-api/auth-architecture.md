# Aither MVP — Auth Architecture

## Overview

BFF v0.4.0 introduces a central auth layer that protects model inference endpoints and enables API token management for AI agents.

```
User / Portal / AI Agent
        |
        v
  BFF Auth Middleware
        |
        +-- Cookie-based admin session (login/logout)
        +-- Bearer API token verification (athr_xxx)
        +-- Redis-backed token metadata
        +-- Redis-backed rate limiting (Stage 06)
        |
        v
  BFF Route Handler
        |
        +-- Upstream call with BFF_*_UPSTREAM_AUTH_TOKEN (NOT user token)
```

## Auth Flow

### 1. Admin Login
```
POST /api/v1/auth/login
  Body: { "username": "admin", "password": "xxx" }
  Response: Set-Cookie: session_id=xxx (httponly)

GET /api/v1/auth/me
  Cookie: session_id=xxx
  Response: { "username": "admin", "created_at": "..." }

POST /api/v1/auth/logout
  Response: deleted cookie
```

### 2. API Token Management (admin only)
```
POST /api/v1/tokens     -> Create token (returns raw token ONCE)
GET  /api/v1/tokens     -> List tokens (metadata only, no raw token)
DELETE /api/v1/tokens/X -> Revoke token
```

### 3. AI Agent Access
```
GET  /api/v1/models        -> Auth required + rate limited
POST /api/v1/chat          -> Auth required + rate limited
POST /api/v1/completions   -> Auth required + rate limited
```

### 4. Public Endpoints
```
GET /health                -> No auth (shows status)
POST /api/v1/auth/login    -> No auth (handles login itself)
```

## Token Security

| Property | Implementation |
|---|---|
| Token format | `athr_<32 bytes random (urlsafe)>` |
| Storage | HMAC-SHA256 hash in Redis only |
| Raw token | Shown ONCE at creation, never stored |
| Revocation | Supported (sets revoked=true in Redis metadata) |
| Token verification | Fast HMAC-SHA256 comparison |

## Upstream Credential Isolation

User tokens (`Authorization: Bearer athr_xxx`) are:
- Verified locally in BFF
- NOT forwarded to upstream vLLM/gateway
- Replaced with internal `BFF_14B_UPSTREAM_AUTH_TOKEN` or `BFF_32B_GATEWAY_AUTH_TOKEN`

This ensures:
- Users cannot access upstream directly with their token
- Upstream credential rotation doesn't affect user tokens
- No user token leakage to model providers

## Session Management

- Admin session: Redis-backed, 24h TTL
- Session identifier: UUID4 hex
- Cookie: httponly, samesite=strict
- Session data: username, created_at, IP

## 32B Chat Adapter

Since the 32B model is a base/completion model:
- `POST /api/v1/chat model=32b` converts messages to completion prompt format
- Uses `<|role|>\ncontent` template
- Routes through `nginx-gateway-32b` for policy enforcement
- This is NOT native chat — documented as adapter

## Limitations (Stage 07.1)

- No OAuth (future stage)
- No Portal UI (Stage 07.2)
- No token expiration enforcement (MVP scope)
- Redis-only token storage (no persistence beyond Redis)
- Admin password stored as SHA-256 hash in Kubernetes Secret
