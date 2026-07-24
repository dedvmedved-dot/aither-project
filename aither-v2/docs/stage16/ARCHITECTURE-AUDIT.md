# Aither / AI Hermes MVP
# Stage 16 — Architecture Audit

## Repository State

| Field | Value |
|---|---|
| Repository | `dedvmedved-dot/aither-project` |
| Branch | `aither-v2` |
| Parent commit | `5fea3c76145e781a9f8477f16eeae8650fa6b242` |
| Status | Clean — no uncommitted changes |

## Existing Components

### 1. Identity Service (`services/identity/`)
- **Technology:** Python FastAPI + SQLite
- **Auth tokens:** HMAC-signed with `IDENTITY_SECRET_KEY` (custom format — payload + HMAC hex)
- **Token format:** `{"uid": N, "sub": "username", "role": "str", "iat": int, "exp": int, "jti": "token"}`
- **Token validation:** Stateless HMAC verify via `verify_jwt()`
- **Password storage:** bcrypt (12 rounds)
- **Database:** SQLite at `/data/identity.db` (currently **emptyDir** — data lost on pod restart)
- **API prefix:** `/v1/identity/` (auth, me, users, bootstrap)
- **K8s:** Port 8000, Service name `aither-identity`
- **Health endpoints:** `/health`, `/ready`, `/version`

### 2. Portal Backend (BFF) (`services/portal-backend/`)
- **Technology:** Python FastAPI + httpx
- **Role:** Proxying layer — forwards `/api/v1/auth/*` to Identity
- **Identity URL:** `http://aither-identity:8000` (env `PORTAL_IDENTITY_URL`)
- **Health endpoints:** `/health`, `/ready`, `/version`
- **CORS:** Open (`*`) via env `PORTAL_CORS_ORIGIN`
- **K8s:** Port 8000, Service name `aither-portal-backend`

### 3. Portal Frontend (`services/portal-frontend/`)
- **Runtime:** Nginx static SPA
- **API proxy:** `/api/` → `http://aither-portal-backend:8000`
- **Health proxy:** `/health`, `/ready`, `/version` → Portal Backend
- **K8s:** Port 80, Service name `aither-portal-frontend`, ConfigMap-based deployment

### 4. Gateway (`manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml`)
- **Technology:** Nginx ConfigMap
- **Port:** 8000
- **Service name:** `nginx-gateway-32b.aither-inference.svc`
- **Endpoint:** `/v1/completions` → `http://10.99.3.103:8000` (qwen-32b-base)
- **Chat completions:** `/v1/chat/completions` returns `422` (qwen-32b-base doesn't support chat)
- **Auth:** Proxies `Authorization` header upstream
- **DNS:** `ClusterFirst` (fixed in Stage 11)
- **CoreDNS:** `10.96.0.10`
- **Health:** `/healthz` (nginx only), `/health` (upstream)

### 5. vLLM Inference (`03-vllm-14b-deploy/manifests/`)
- **Model:** `qwen-14b-instruct` (chat-capable)
- **Service:** `vllm-14b-instruct.aither-inference.svc:8000`
- **Deployment:** `vllm-14b-instruct` in namespace `aither-inference`
- **Gateway references:** The hardened nginx-gateway-32b proxies to `10.99.3.103:8000` directly (IP-based, not service DNS)

### 6. Stage 14 Deployment (`deploy/`)
- **Namespace:** `aither-inference`
- **Structure:** `10-precheck.sh`, `20-infrastructure.sh`, `30-services.sh`, `40-validation.sh`
- **Currently deploys:** Gateway, vLLM, Redis, BFF, Portal

## Key Findings

### Identity Persistence Issue
- Identity Service uses `emptyDir` for `/data/` — **all users, sessions lost on pod restart**
- Stage 16 **must** fix: add PVC for identity data

### Gateway Architecture
- Gateway is at `nginx-gateway-32b.aither-inference.svc:8000`
- `/v1/chat/completions` returns `422` — this is for qwen-32b-base only
- The 14b model (instruct/chat) is at `vllm-14b-instruct.aither-inference.svc:8000`
- Gateway proxies to upstream via hardcoded IP `10.99.3.103:8000`

### Token Verification
- Portal Backend proxies `Authorization: Bearer <token>` to Identity
- Token is HMAC-signed — no JWT library, custom implementation
- `verify_jwt()` exists in Identity Service
- Portal Backend does NOT have its own token validation

### CORS Configuration
- Currently `*` — acceptable for Beta, should be restricted for production

## Decisions for Stage 16

### Architecture: New AI Platform Service
**Decision:** Create a dedicated `services/ai-platform/` service rather than extending Portal Backend.

**Rationale:**
1. Clear separation of concerns — identity/auth stays in Portal Backend, AI business logic in AI Platform
2. Independent scaling — AI Platform may need different resources
3. Independent security context — API Key validation is separate from session auth
4. Clean API surface — `/v1/chat/completions` endpoint is OpenAI-compatible

### Gateway Integration
- AI Platform will call Gateway at `http://nginx-gateway-32b.aither-inference.svc:8000`
- For chat models (14b), the call goes to Gateway's `/v1/completions` or directly to vLLM service
- Decision: go through Gateway to respect existing architecture

### Persistence
- Add PVC for Identity Service (`aither-identity-data`)
- Add PVC for AI Platform (`aither-ai-platform-data`)
- Keep SQLite for Beta — document that migration to PostgreSQL is a Stage 18 concern
