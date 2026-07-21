# Aither / AI Hermes MVP
# Stage 16 — Architecture

## Components

```
Browser
  │
  ▼
Portal Frontend (Nginx SPA)
  ├── /api/* → Portal Backend
  ├── /v1/chat/completions → AI Platform
  ├── /health → Portal Backend
  └── /version → Portal Backend
         │
 Portal Backend (FastAPI, BFF proxying layer)
  ├── /api/v1/auth/* → Identity Service
  └── /api/v1/status → aggregates Identity + AI Platform
         │
 Identity Service (FastAPI + SQLite + PVC)
  ├── Users, roles, sessions
  ├── bcrypt password hashing
  └── HMAC-signed tokens
         │
 AI Platform Service (FastAPI + SQLite + PVC)
  ├── Model Registry
  ├── API Key Store (SHA-256 hashed)
  ├── Assistant Store
  ├── Conversation Store
  └── Chat → Gateway → vLLM
         │
 Gateway (nginx-gateway-32b, existing, UNCHANGED)
  └── /v1/completions → vLLM inference
```

## Data Flow

### Authentication (user session)
1. User logs in via Portal → Portal Backend → Identity Service
2. Identity returns HMAC-signed bearer token
3. Token stored in localStorage, sent as `Authorization: Bearer`

### AI Platform (Portal)
1. User accesses Models/Assistants/Chats via browser
2. Portal Frontend calls `/api/v1/*` → Portal Backend proxies to AI Platform
3. AI Platform validates bearer token via Identity Service
4. Returns/processes data from SQLite

### AI Completion (API Key)
1. External client calls `/v1/chat/completions` with `Authorization: Bearer aither_xxx`
2. Portal Frontend Nginx proxies to AI Platform
3. AI Platform validates API Key (SHA-256 hash comparison)
4. AI Platform looks up model, builds messages
5. Calls Gateway `/v1/chat/completions` or `/v1/completions`
6. Gateway proxies to vLLM inference runtime
7. Response returned to client

## Persistence

- **Identity Service:** SQLite on PVC (`aither-identity-data`, 1Gi)
- **AI Platform:** SQLite on PVC (`aither-ai-platform-data`, 1Gi)
- **Backup:** Documented in DEPLOYMENT.md (manual sqlite backup)

## Trust Boundaries

| Boundary | Authentication | Notes |
|---|---|---|
| Browser → Frontend | None (public) | HTTPS recommended |
| Frontend → Portal Backend | Bearer token | Proxied, validated against Identity |
| Frontend → AI Platform | Bearer token or API Key | API Key for external `/v1/chat/completions` |
| Portal Backend → Identity | Bearer token | Forwarded from user |
| AI Platform → Identity | Bearer token | Forwarded from user |
| AI Platform → Gateway | None (internal) | Cluster-internal only |
