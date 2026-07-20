# E2E Architecture

## Full Path

```
User Browser / Agent
  │
  ▼
aither-portal (nginx:alpine, same-origin reverse proxy)
  │
  ├── /health → aither-bff:8000/health
  ├── /api/v1/* → aither-bff:8000/api/v1/*
  └── /* → static files (index.html, app.js, styles.css)
  │
  ▼
aither-bff (FastAPI v0.4.0)
  │
  ├── Auth middleware (session + Bearer token)
  │   ├── POST /api/v1/auth/login
  │   ├── POST /api/v1/auth/logout
  │   ├── GET  /api/v1/auth/me
  ├── Token management
  │   ├── POST /api/v1/tokens (create, raw token once)
  │   ├── GET  /api/v1/tokens (list, metadata only)
  │   └── DELETE /api/v1/tokens/{id} (revoke)
  ├── Model endpoints
  │   ├── GET  /api/v1/models (list models)
  │   ├── POST /api/v1/chat (14B chat + 32B adapter)
  │   └── POST /api/v1/completions (32B only)
  ├── Redis rate limiting (10 req/60s window)
  │
  ├── 14B path → vllm-14b-instruct:8000 (internal token)
  └── 32B path → nginx-gateway-32b:8000 → vllm-32b-gptq:8000 (internal token)
```

## Key Design Decisions

1. Portal → BFF only: no direct Portal access to vLLM, Gateway, or Redis.
2. User API tokens are Bearer auth for BFF, NEVER forwarded to upstream.
3. Upstream calls use separate internal tokens (BFF_14B_UPSTREAM_AUTH_TOKEN, BFF_32B_GATEWAY_AUTH_TOKEN).
4. Rate limiting is per token hash or client IP before upstream call.
5. Session auth (admin) vs Bearer auth (API token) both supported.
6. 32B chat is adapter over completion — never native chat.
