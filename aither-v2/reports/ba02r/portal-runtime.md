# Portal Runtime Architecture

**Stage:** BA-02R  
**Date:** 2026-07-23  
**Author:** Hermes + DeepSeek  

## Request Flow

```
Browser (User)
    │
    ▼
┌─────────────────────────────┐
│ Portal Frontend (SPA)       │  nginx:stable-alpine
│ Pod: aither-portal-frontend │  IP: 10.244.1.23
│ Service: aither-portal      │  ClusterIP: 10.100.145.83:80
└──────────┬──────────────────┘
           │ /api/*  (via nginx location /api/)
           ▼
┌───────────────────────────────┐
│ Portal Backend (BFF)          │  FastAPI / uvicorn
│ Pod: aither-portal-backend    │  IP: 10.244.0.5 (n8)
│ Service: aither-portal-backend│  ClusterIP: 10.100.101.65:8000
│ Image: stage18a-82fe433       │
└──┬────────────┬───────────┬───┘
   │            │           │
   ▼            ▼           ▼
┌────────┐ ┌─────────┐ ┌──────────────┐
│ /auth/*│ │ /api/v1/│ │ /health      │
│ Proxy  │ │/* Proxy │ │ /ready       │
│ Identity│ │ AI Plat.│ │ /version     │
└───┬────┘ └───┬─────┘ └──────────────┘
    │          │
    ▼          ▼
┌─────────────────────┐
│ AI Platform          │  FastAPI / uvicorn
│ Pod: aither-ai-plat.│  IP: 10.244.0.4 (n8)
│ Service: aither-ai. │  ClusterIP: 10.107.239.156:8000
│ Image: ba01r-fix    │
├─────────────────────┤
│ Routes:             │
│ /api/v1/models      │
│ /api/v1/api-keys    │
│ /api/v1/assistants  │
│ /api/v1/conversations│
│ /v1/chat/completions│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Gateway (nginx)      │  nginx:alpine
│ nginx-gateway-32b    │  ClusterIP: 10.106.31.143:8000
├─────────────────────┤
│ /v1/completions ────│──► vLLM 32B (10.99.3.103:8000)
│ /health ───────────│──► vLLM 32B
│ /v1/models ────────│──► vLLM 32B
│ /chat/completions ─│──► 422 (model does not support chat)
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│ vLLM 32B             │  qwen-32b-base
│ Service: vllm-32b.  │  ClusterIP: 10.99.3.103:8000
│ Completion-only     │  Requires VLLM_API_KEY
└─────────────────────┘
```

## Alternative (Unused) Path — vLLM 14B

```
AI Platform ──► vLLM-14B-instruct
                 Service: vllm-14b-instruct
                 ClusterIP: 10.108.67.57:8000
                 Chat model (qwen-14b-instruct)
                 NOT connected to Gateway
                 Requires VLLM_API_KEY (separate from 32B)
```

## Endpoint Table

| Component | URL | Port | Auth | Notes |
|-----------|-----|------|------|-------|
| Portal Frontend (nginx) | `aither-portal-frontend:80` | 80 | — | Serves SPA, proxies /api/ |
| Portal Backend | `aither-portal-backend:8000` | 8000 | JWT Bearer | BFF, proxies to services |
| AI Platform | `aither-ai-platform:8000` | 8000 | JWT or API Key | Core business logic |
| Identity | `aither-identity:8000` | 8000 | — | User management, JWT |
| Gateway 32B | `nginx-gateway-32b:8000` | 8000 | VLLM_API_KEY | Routes to vLLM 32B |
| vLLM 32B | `vllm-32b-gptq:8000` | 8000 | VLLM_API_KEY | qwen-32b-base (completion) |
| vLLM 14B | `vllm-14b-instruct:8000` | 8000 | VLLM_API_KEY | qwen-14b-instruct (chat) |

## Auth Flow

```
User → Portal Backend Login → Identity JWT → Portal Backend stores Bearer token
User → API call → Portal Backend proxies Bearer token → AI Platform validates JWT via Identity
User → OpenAI API → API Key (ai ther_*) → AI Platform validates locally
```

## Auth Methods

1. **JWT Bearer token** — obtained from `/api/v1/auth/login` via Portal Backend
2. **API Key** — `ai ther_*` format, validated locally by AI Platform DB (SHA256 hash)
3. **Gateway API Key** — internal `VLLM_API_KEY`, injected by AI Platform when calling Gateway

## AI Platform → Gateway auth flow

1. AI Platform reads `AI_PLATFORM_GATEWAY_API_KEY` from env (from K8s Secret `vllm-api-key`)
2. Sends `Authorization: Bearer <key>` to Gateway
3. Gateway proxies header to vLLM
4. vLLM validates the key internally

## Known Limitations

1. **Gateway supports one model only** — qwen-32b-base (completion-only). Chat format breaks.
2. **14B model not accessible** through Gateway — no Gateway route exists for it.
3. **k8s API intermittency** — affects kubectl and port-forward from build host.
4. **Portal Frontend → Portal Backend path** works via nginx proxy `/api/`.
