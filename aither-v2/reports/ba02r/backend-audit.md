# Backend Audit — Portal Backend OpenAPI

**Stage:** BA-02R  
**Date:** 2026-07-23  
**Author:** Hermes + DeepSeek  

## Code Structure

- **File:** `services/portal-backend/app/main.py` (444 lines, single file)
- **Framework:** FastAPI 1.0.0
- **Router:** Direct `@app.get/post/delete` decorators (no `include_router`)
- **Total endpoints:** 20

## Complete Endpoint List

| # | Method | Path | Auth | Upstream | Status | Notes |
|---|--------|------|------|----------|--------|-------|
| 1 | GET | `/health` | No | Local | ✅ 200 | Service health |
| 2 | GET | `/ready` | No | Identity `/ready` | ✅ 200/503 | Dependency check |
| 3 | GET | `/version` | No | Local | ✅ 200 | Version info |
| 4 | GET | `/metrics` | No | Local (Prometheus) | ✅ 200 | Prometheus scrape |
| 5 | POST | `/api/v1/auth/login` | No | Identity `/v1/identity/auth` | ✅ 200 | Returns JWT |
| 6 | POST | `/api/v1/auth/logout` | Bearer | Identity `/v1/identity/logout` | ✅ 200 | |
| 7 | GET | `/api/v1/auth/me` | Bearer | Identity `/v1/identity/me` | ✅ 200 | User info |
| 8 | GET | `/api/v1/status` | No | Identity + AI Platform | ✅ 200 | Aggregated status |
| 9 | GET | `/api/v1/models` | Bearer | AI Platform `/api/v1/models` | ✅ 200 | List models |
| 10 | POST | `/api/v1/models` | Bearer | AI Platform `/api/v1/models` | ✅ 201 | Create model |
| 11 | GET | `/api/v1/api-keys` | Bearer | AI Platform `/api/v1/api-keys` | ✅ 200 | List API keys |
| 12 | POST | `/api/v1/api-keys` | Bearer | AI Platform `/api/v1/api-keys` | ✅ 201 | Create API key |
| 13 | DELETE | `/api/v1/api-keys/{id}` | Bearer | AI Platform `/api/v1/api-keys/{id}` | ✅ 200 | Revoke API key |
| 14 | GET | `/api/v1/assistants` | Bearer | AI Platform `/api/v1/assistants` | ✅ 200 | List assistants |
| 15 | POST | `/api/v1/assistants` | Bearer | AI Platform `/api/v1/assistants` | ✅ 201 | Create assistant |
| 16 | GET | `/api/v1/conversations` | Bearer | AI Platform `/api/v1/conversations` | ✅ 200/401 | List conversations |
| 17 | POST | `/api/v1/conversations` | Bearer | AI Platform `/api/v1/conversations` | ✅ 201/401 | Create conversation |
| 18 | GET | `/api/v1/conversations/{id}` | Bearer | AI Platform `/api/v1/conversations/{id}` | ✅ 200/401 | Get conversation |
| 19 | POST | `/api/v1/conversations/{id}/messages` | Bearer | AI Platform `/api/v1/conversations/{id}/messages` | ✅ 200/502 | Send message |
| 20 | DELETE | `/api/v1/conversations/{id}` | Bearer | AI Platform `/api/v1/conversations/{id}` | ✅ 200/401 | Delete conversation |

## Auth Middleware

```
Portal Backend ──► proxies Bearer token ──► AI Platform ──► validates via Identity
```

Portal Backend does NOT validate tokens itself — it passes them through to AI Platform which calls Identity `/v1/identity/me`.

## CORS Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN],  # default: http://localhost:3000
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Issue:** CORS origin defaults to `http://localhost:3000` instead of Portal Frontend URL. In production, it should be the actual Portal URL.

## Proxy Implementation

All proxy routes follow the same pattern:
```python
auth = request.headers.get("Authorization", "")
async with httpx.AsyncClient(base_url=AI_PLATFORM_URL, timeout=10.0) as ac:
    r = await ac.get("/api/v1/models", headers={"Authorization": auth})
    return Response(content=r.content, status_code=r.status_code, media_type="application/json")
```

**Issues:**
1. New `httpx.AsyncClient` created on every request (no connection pooling for proxy)
2. Timeout is hardcoded (10s for most, 60s for messages — adequate)
3. No retry logic for transient failures
4. Error handling returns generic 503 "AI Platform unreachable"

## OpenAPI Docs

- **docs_url:** `/api/v1/docs`
- **openapi_url:** `/api/v1/openapi.json`

Both are enabled (default FastAPI behavior, explicitly set).

## Missing Features

1. No WebSocket support (no streaming from Portal)
2. No rate limiting in Portal Backend (Redis is available separately)
3. No request/response validation (FastAPI pydantic models only used for login)
4. Proxy headers not forwarded (no X-Forwarded-For, X-Request-ID propagation)

## Recommendations

1. Add connection pool: reuse `httpx.AsyncClient` for AI Platform calls
2. Add retry with backoff for proxy requests
3. Make timeout configurable via environment variables
4. Propagate request IDs for debugging
5. Set CORS origin to Portal Frontend URL in production deployment
