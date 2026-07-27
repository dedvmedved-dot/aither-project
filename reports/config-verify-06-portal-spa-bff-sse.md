# Configuration Verification Report — Task #6: Portal (SPA + BFF + SSE)

**Date:** 2026-07-27
**HEAD:** d174d3e
**Validator:** Hermes / DeepSeek
**Method:** read-only runtime verification (kubectl, curl, configmap inspection)

---

## 1. Portal SPA (Single Page Application)

| Check | Result | Evidence |
|---|---|---|
| Service | `aither-portal` NodePort 30080 | HTTP 200 at `/` |
| Container | nginx:stable-alpine, 1 replica (N7) | Running |
| index.html | ✅ PRESENT, served at `/` | Full SPA: Login, Register, Dashboard, Chat, API Keys, Agent, Docs, Feedback, Status, Profile |
| app.js | ✅ PRESENT, inline in index.html | Auth (session cookie), chat (non-streaming POST), API key CRUD, invite registration |
| styles.css | ✅ PRESENT | Dark theme, responsive, CB-WEBUI-01 |
| version badge | `Версия 2.0 — CB-WEBUI-01` | Footer text |

**SPA configuration:** `aither-portal-config` ConfigMap (4 files):
- `nginx.conf` — reverse proxy:
  - `/api/*` → `http://aither-bff:8000/api/`
  - `/docs/*` → `http://aither-portal-frontend/docs/`
  - `/health` → `http://aither-bff:8000/health`
  - `/ready` → `http://aither-bff:8000/health`
  - Root `/` → `/usr/share/nginx/html/index.html`
- `index.html` — SPA with inline CSS + JS
- `app.js` — placeholder
- `styles.css` — placeholder (real styles inlined in HTML)

---

## 2. BFF (Backend for Frontend)

| Check | Result | Evidence |
|---|---|---|
| Deployment | 2 replicas (N7 + N8) | Running, READY 1/1 |
| Image | python:3.11-slim | FastAPI via uvicorn |
| ConfigMap | `aither-bff-config` → `/app/app.py` | v0.6.0-r7r7-c2-d18 |
| Health | ✅ HTTP 200 | `{"status":"ok","version":"0.6.0-r7r7-c2-d18","rate_limit":"enabled","redis":"connected","auth":"configured"}` |
| Redis | ✅ connected | `redis://aither-redis-rate-limit.aither-inference.svc:6379/0` |
| Rate limit | ✅ enabled | 60s window, 10 req max |

**BFF endpoints:**
- `/health` — health check
- `/api/v1/auth/login` — admin (K8s Secret) + registered users (Argon2id)
- `/api/v1/auth/logout` — session invalidation
- `/api/v1/auth/me` — session check (D18: recheck user status)
- `/api/v1/auth/register` — invite-based registration (D18: Lua expires_at, fail-closed)
- `/api/v1/tokens` (GET/POST/DELETE) — API key management (athr_* format, ownership tracking)
- `/api/v1/chat` — 14B chat (direct → vLLM), 32B chat-adapter (via nginx-gateway-32b)
- `/api/v1/completions` — 32B completion
- `/api/v1/models` — model list

**BFF secrets:** `aither-bff-auth` (ADMIN_USERNAME, ADMIN_PASSWORD_HASH, SESSION_SECRET, AUTH_TOKEN_HASH_SECRET, BFF_14B_UPSTREAM_AUTH_TOKEN, BFF_32B_GATEWAY_AUTH_TOKEN)

**D18 corrections verified:**
- ✅ Lua expires_at_epoch read from invite data (not ARGV)
- ✅ Session recheck: user record status verified on every auth
- ✅ Session invalidation: `_invalidate_user_sessions()` scan
- ✅ list_tokens ownership filter: non-admin sees only own tokens via `_token_user_set_key`
- ✅ revoke fail-closed: empty owner_id or foreign token → 403
- ✅ Scope restriction: create_token rejects forbidden scopes with 403

---

## 3. SSL / SSE

| Check | Result | Evidence |
|---|---|---|
| BFF chat streaming | ❌ NOT ACTIVE | `stream: false` in chat payload |
| Gateway SSE | ✅ IMPLEMENTED (not in path) | Gateway has real SSE streaming with security egress chunk check |
| SPA SSE handling | ❌ NOT IMPLEMENTED | JS uses single POST response, no EventSource or streaming |
| HTTPS (Internet Zone) | ✅ via NodePort ingress | fb1.spb.ru:443 |

**SSE status:** The Gateway implements real SSE streaming (yield chunks, egress security filter per chunk) but the Gateway is NOT in the active request path (BFF cutover was rolled back). The BFF chat endpoint uses `stream: false` and returns a single response. The SPA has no SSE/EventSource handling — it displays the full response after it arrives.

---

## 4. Gateway (CHANGE-0022-C2) — standby

| Check | Result | Evidence |
|---|---|---|
| Deployment | 2 replicas (N7 + N8) | Running |
| Health | ✅ | `{"status":"ok","service":"aither-gateway","change":"CHANGE-0022-C2"}` |
| Readiness | ✅ ALL GREEN | `{"status":"ok","dependencies":{"redis":"ok","postgres":"ok","catalog":"2 models","model_14b":"ok","model_32b":"ok"}}` |
| Models | ✅ 2 active | qwen-14b (Qwen 2.5 14B Instruct, max 4096), qwen-32b-base (Qwen 2.5 32B GPTQ, max 4096) |
| Metrics | ✅ Prometheus | 9 metric types: requests_total, tokens_total, billing_total, auth_denied_total, rate_limit_denied_total, security_denied_total, upstream_errors_total, siem_delivery_failures_total, active_requests |
| PostgreSQL | ✅ connected | DB `aither`, 12 tables |
| Rate limiting | ✅ PG-backed tiers | Redis Lua atomic counters |
| Billing | ✅ idempotent | reserve→settle→refund, `billing_idempotency` table |
| Auth | ✅ ak-* + athr_* | SHA-256 hash storage |
| Admin drain | ✅ PG-backed | Cross-replica `drain_state` table |
| Active in path | ❌ NOT IN PATH | BFF cutover rolled back, Gateway on standby |

---

## 5. Architecture Summary

```
Internet → fb1.spb.ru:443 (HTTPS)
  → NodePort 30080 → aither-portal (nginx:80)
    ├── /          → index.html (SPA)
    ├── /api/*     → aither-bff:8000/api/*    [ACTIVE PATH]
    ├── /docs/*    → aither-portal-frontend/docs/
    └── /health    → aither-bff:8000/health

aither-bff (FastAPI, 2 replicas):
  ├── /api/v1/chat (14B)     → vllm-14b-instruct:8000/v1/chat/completions      [DIRECT]
  ├── /api/v1/chat (32B)     → nginx-gateway-32b:8000/v1/completions          [DIRECT]
  ├── /api/v1/completions    → nginx-gateway-32b:8000/v1/completions          [DIRECT]
  ├── /api/v1/auth/*         → Redis (session/token storage)
  └── /api/v1/tokens/*       → Redis (token CRUD)

aither-gateway (FastAPI, 2 replicas): [STANDBY — not in active path]
  ├── /v1/chat/completions   → vllm-14b-instruct:8000 (with security pipeline)
  ├── /v1/completions        → vllm-32b-gptq:8000 (with security pipeline)
  ├── /health, /ready, /metrics, /v1/models
  └── PG-backed: billing, rate limiting, admin drain, metrics
```

---

## 6. Assessment

| Criterion | Status | Note |
|---|---|---|
| Portal SPA (index.html) | ✅ PRESENT | Full SPA with auth, chat, API keys, agent, docs, feedback, status, profile |
| BFF (app.py) | ✅ PRESENT | v0.6.0-r7r7-c2-d18, 2/2 Running, all endpoints functional |
| SSE (streaming) | ⚠️ IMPLEMENTED BUT NOT ACTIVE | Gateway has SSE, BFF+SPA use non-streaming |
| Gateway (standby) | ✅ READY | All checks green, models live, PG/Redis OK |
| BFF cutover | ❌ ROLLED BACK | Gateway not in active request path |
| Overall Portal | ✅ OPERATIONAL | HTTP 200, /health: ok, all SPA pages render, auth works |

**Conclusion:** Task #6 (Portal: SPA + BFF + SSE) is **partially complete**:
- SPA ✅ — full interactive web UI with all pages
- BFF ✅ — auth, tokens, chat routing operational
- SSE ⚠️ — implemented in Gateway but not in active path; BFF/SPA use non-streaming
- Gateway ✅ — ready for production cutover (pending authorization)
