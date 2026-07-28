# FRONTEND INTEGRATION — API CONTRACT

**Created:** 2026-07-28T09:58:00Z
**Based on:** FRONTEND-INTEGRATION-API-INVENTORY.md
**Commit:** ef41e0e

---

## 1. Auth Endpoints

### POST /api/v1/auth/login
```
Request:  { "username": "string", "password": "string" }
Response: { "token": "string (JWT)", "user": { "id": int, "username": "string", "role": "string" } }
Errors:   401 Invalid credentials, 403 Account disabled
```

### GET /api/v1/auth/me
```
Request:  Authorization: Bearer <jwt>
Response: { "id": int, "username": "string", "role": "string" }
Errors:   401 Invalid token
```

---

## 2. Chat Endpoint

### POST /api/v1/chat
```
Request:  {
    "model": "qwen-14b" | "qwen-32b-base",
    "messages": [{"role": "user"|"assistant"|"system", "content": "string"}],
    "max_tokens": int (default 512),
    "temperature": float (default 0.7)
  }
Response: {
    "id": "string",
    "object": "chat.completion",
    "model": "string",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "string"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}
  }
Errors:   401 Invalid token, 402 Insufficient balance, 429 Rate limit, 503 AI Platform unreachable
Rate limit: per-user, Redis sliding window
Audit:     usage_records + billing_ledger
```

---

## 3. Admin Gateway Endpoints (via Portal Backend facade)

All require: `role=admin`, Portal Backend mints delegation JWT with X-Admin-Key.

### GET /api/v1/admin/gateway/queues
```
Response: { "queues": [], "status": "ok" }
```

### GET /api/v1/admin/gateway/models
```
Response: { "models": [{"model": "string", "requests": int, "tokens": int}] }
```

### POST /api/v1/admin/gateway/models/{model}/drain
```
Response: { "status": "ok", "model": "string", "drained": true }
```

### POST /api/v1/admin/gateway/models/{model}/undrain
```
Response: { "status": "ok", "model": "string", "drained": false }
```

### GET /api/v1/admin/gateway/health
```
Response: { "status": "ok", "orgs": int, "transactions_24h": int }
```

### GET /api/v1/admin/gateway/reaper
```
Response: { "status": "ok", "message": "Reaper is running in background thread" }
```

---

## 4. Billing/Usage Endpoints (TO BE IMPLEMENTED)

### GET /v1/billing/me
```
Auth:     Bearer JWT → org_id from token
Response: { "org_id": "string", "tier": "string", "balance": int, "reserved": int, "available": int, "updated_at": "ISO8601" }
```

### GET /v1/billing/me/ledger
```
Response: { "org_id": "string", "ledger": [{"amount": int, "operation": "reserve"|"settle"|"refund", "reference": "string", "balance_after": int, "created_at": "ISO8601"}] }
```

### GET /v1/usage/me
```
Response: { "org_id": "string", "total_tokens": int, "total_requests": int, "requests_today": int }
```

### GET /v1/usage/me/daily
```
Response: { "org_id": "string", "daily": [{"date": "string", "requests": int, "tokens": int}] }
```

---

## 5. RAG Endpoints (via Portal Backend facade)

### GET /api/v1/rag/status
```
Auth:     Bearer JWT
Response: { "status": "ok", "wiki_pages": int, "chroma_ok": bool, "last_ingest": "ISO8601" }
```

### POST /api/v1/rag/query
```
Auth:     Bearer JWT, scope: rag:query
Request:  { "query": "string", "top_k": int (default 5) }
Response: { "results": [{"title": "string", "snippet": "string", "score": float, "source": "string"}] }
```

### POST /api/v1/rag/hybrid-query
```
Auth:     Bearer JWT, scope: rag:query
Request:  { "query": "string", "top_k": int, "wiki_radius": int (default 1) }
Response: { "results": [...] }
```

### POST /api/v1/rag/ingest
```
Auth:     Bearer JWT, scope: rag:ingest
Request:  multipart/form-data: file
Response: { "status": "ok", "chunks": int }
```

---

## 6. Monitoring Endpoints (TO BE IMPLEMENTED)

All require: `role=admin` or `role=operator`.

### GET /api/v1/monitoring/summary
```
Response: {
    "requests_total": int, "requests_rate": float,
    "success_rate": float, "error_rate": float,
    "ttft_p50": float, "ttft_p95": float, "ttft_p99": float,
    "latency_p50": float, "latency_p95": float,
    "active_requests": int
  }
```

### GET /api/v1/monitoring/models
```
Response: { "models": [{"model": "string", "requests": int, "tokens": int, "ttft_p50": float}] }
```

### GET /api/v1/monitoring/security
```
Response: { "auth_denials": int, "rate_limit_denials": int, "ingress_blocks": int, "egress_blocks": int }
```

### GET /api/v1/monitoring/dependencies
```
Response: { "redis": "ok"|"error", "postgresql": "ok"|"error", "vault": "ok"|"error"|"disabled", "siem": "ok"|"error", "14b": "ok"|"error", "32b": "ok"|"error" }
```

---

## 7. Delegation JWT Contract

Portal Backend → Gateway: RS256 JWT
```json
{
  "iss": "aither-portal-backend",
  "aud": "aither-gateway",
  "sub": "<username>",
  "user_id": "<uuid>",
  "org_id": "<uuid>",
  "role": "admin"|"user"|"operator",
  "tier": "free"|"pro"|"enterprise",
  "scopes": ["model:14b:chat", "rag:query"],
  "jti": "<uuid>",
  "iat": "<unix>",
  "nbf": "<unix>",
  "exp": "<unix, iat+60>"
}
```
