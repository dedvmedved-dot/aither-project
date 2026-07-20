# Aither Portal — Architecture

## Overview

Stage 07.2 introduces a lightweight web portal as a separate deployment:
`aither-portal` (nginx:alpine) deployed in namespace `aither-inference`.

## Architecture Diagram

```
                          ┌───────────────┐
                          │   Browser     │
                          └───────┬───────┘
                                  │
                          ┌───────▼───────┐
                          │ aither-portal │
                          │  nginx:alpine │ ← same-origin proxy
                          │  :80          │
                          └───────┬───────┘
                                  │ proxy_pass
                          ┌───────▼───────┐
                          │  aither-bff   │
                          │  FastAPI      │ ← auth, tokens, chat, models
                          │  :8000        │
                          └───────┬───────┘
                                  │
                  ┌───────────────┼───────────────┐
                  │               │               │
          ┌───────▼───────┐ ┌────▼────┐ ┌────────▼────────┐
          │  vLLM 14B     │ │n-gateway│ │ aither-redis     │
          │  (native)     │ │ 32B     │ │ rate-limit +     │
          │               │ │         │ │ token metadata   │
          └───────────────┘ └─────────┘ └─────────────────┘
```

## Routes

| Browser URL | nginx proxy_pass | Description |
|---|---|---|
| `/` | static | Portal SPA |
| `/api/v1/*` | → `http://aither-bff:8000/api/v1/*` | Auth, tokens, chat, models |
| `/health` | → `http://aither-bff:8000/health` | System health |

## Data Flow

1. **Login**: Browser → Portal → POST `/api/v1/auth/login` → BFF validates → returns session cookie
2. **Token Management**: Browser → Portal → POST/GET/DELETE `/api/v1/tokens` → BFF → Redis
3. **Chat**: Browser → Portal → POST `/api/v1/chat` → BFF → vLLM 14B or nginx-gateway 32B
4. **Status**: Browser → Portal → GET `/health` → BFF returns health info

## Security Boundaries

- Portal NEVER accesses vLLM/Gateway/Redis directly
- Portal NEVER stores raw tokens in browser storage
- Session cookies use Same-Origin policy (no CORS needed)
- BFF validates all auth/scope requirements before upstream calls

## Deployment

- **Deployment**: `aither-portal` — nginx:alpine, ConfigMap-mounted static files
- **Service**: `aither-portal:80` — ClusterIP
- **ConfigMap**: `aither-portal-config` — index.html, styles.css, app.js, nginx.conf
