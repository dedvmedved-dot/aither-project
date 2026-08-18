# EXT API Chat Recovery R2 — Execution Evidence

- Task: `AITHER-MVP-EXT-API-CHAT-RECOVERY-R2`
- Mode: `RUNTIME_DIAGNOSIS_AND_MINIMAL_RECOVERY`
- Executor: `hermes`
- Branch: `aither-v2`
- Baseline SHA: `f8557f930393138cf6a9fa6e6be1ab2383890529`
- HEAD (task-control): `55e393782952bc7b18fcc033fea44e4ad92ba3bb`
- HEAD parent: `f8557f930393138cf6a9fa6e6be1ab2383890529`
- Result: **PASS** (recovery verified complete; no source/runtime correction required — the external API is already functional at runtime)

---

## 1. Preflight

| Item | Value |
|------|-------|
| hostname | `330133.fornex.cloud` |
| executor uid/gid | `0`/`0` (root Hermes; repo owned by `codex` uid 1000) |
| workdir | `/home/codex/aither-project` |
| `git rev-parse HEAD` | `55e393782952bc7b18fcc033fea44e4ad92ba3bb` |
| branch | `aither-v2` |
| `git status --short` | clean (empty) |
| baseline ancestor of HEAD | YES |

Git was invoked exclusively via `runuser -u codex -- git ...` (no `safe.directory`). No git write was performed.

## 2. NodePort 30080 topology (proven)

```
NodePort 10.129.13.78:30080
  └─ Service aither-portal (ns aither-inference, port 80→targetPort 80, selector app=aither-portal)
       └─ Pod aither-portal-6c9dd7bcb9-9fzfd (container: nginx:stable-alpine, node n7-gpu)
            ├─ ConfigMap aither-portal-config (key nginx.conf mounted at /etc/nginx/conf.d)
            ├─ ConfigMap aither-portal-config (keys index.html/app.js/styles.css at /usr/share/nginx/html)
            ├─ ConfigMap aither-portal-docs (docs)
            └─ upstreams:
                 ├─ location = /api/v1/models          → http://aither-portal-backend:8000        (full URI → backend /api/v1/models)
                 ├─ location = /api/v1/chat/completions → http://aither-portal-backend:8000/v1/chat/completions
                 ├─ location /api/                     → http://aither-bff:8000/api/
                 ├─ location /v1/identity/, /auth/     → http://aither-identity.aither-inference.svc:8000
                 └─ location /health, /ready           → http://aither-bff:8000/health
```

Backend service `aither-portal-backend`:
- Deployment `aither-portal-backend`, image `10.129.13.78:5000/aither-portal-backend:q25-d0-adf54f0`
- FastAPI app (`/app/app/main.py`), port 8000
- External OpenAI-compatible routes (API key `aither_*` auth):
  - `GET  /v1/models` → `external_list_models`
  - `POST /v1/chat/completions` → `external_chat`
- Internal portal routes (JWT / `aither_*` auth):
  - `GET /api/v1/models` → `proxy_models`

Model upstreams (Secret `aither-portal-upstream`, values verified, tokens not printed):
- `UPSTREAM_32B_URL` = `http://vllm-32b-instruct-awq.aither-inference.svc:8000` (qwen2.5-32b-instruct)
- `UPSTREAM_14B_URL` = `http://vllm-qwen3-32b-awq.aither-inference.svc:8000` (qwen3-32b; stale `14B` variable name only — see GOVERNANCE Scope Contract)

vLLM pods: `vllm-32b-instruct-awq` 1/1 Running, `vllm-qwen3-32b-awq` 1/1 Running.

## 3. Route matrix (observed)

| Request | Status | Body (truncated) |
|---------|--------|------------------|
| GET `/` | 200 | `<!DOCTYPE html>…` (SPA) |
| GET `/health` | 200 | `{"status":"ok","version":"0.6.0-r7r7-c2-d18"}` |
| GET `/api/v1/health` | 404 | `{"detail":"Not Found"}` |
| GET `/api/v1/models` (no auth) | 401 | `{"detail":"Authentication required"}` |
| POST `/api/v1/chat/completions` (no auth) | 401 | `{"detail":"invalid_api_key: Bearer token required"}` |

Health: supported path is `/health` (200) and backend `/ready` (200); `/api/v1/health` is not a backend route (404, recorded as-is).

## 4. Root cause of the original 404

The external OpenAI-compatible API is served by `aither-portal-backend` at `/v1/models` and `/v1/chat/completions`. The nginx ConfigMap must map the public prefix `/api/v1` onto those `/v1/*` backend routes:

- `/api/v1/chat/completions` → `aither-portal-backend:8000/v1/chat/completions` — **correctly mapped** in the current ConfigMap.
- `/api/v1/models` → `aither-portal-backend:8000` (full URI, i.e. backend `/api/v1/models` = the internal `proxy_models` route) — **not the external `/v1/models` route**.

The original `POST /api/v1/chat/completions → 404 {"detail":"Not Found"}` was the FastAPI/Starlette 404 of the backend (the request reached a route that did not exist). In the current deployed ConfigMap the chat route is already rewritten to the external `/v1/chat/completions` endpoint, which returns 401 without a key and 200 with a valid `aither_*` key. The 404 is therefore no longer reproducible.

## 5. Source/runtime drift audit

- Repo `portal/` (Fastify monolith: `server.ts`, `api-gateway.ts`, `nginx.conf`, `Dockerfile` with `node dist/server.js`) is **stale legacy** relative to the deployed runtime.
- Deployed runtime is the microservices architecture: `aither-portal` (nginx-only) + `aither-portal-backend` (FastAPI) + `aither-bff` (FastAPI) + `aither-identity` (FastAPI) + `aither-ai-platform`.
- The live nginx config lives in ConfigMap `aither-portal-config` (created 2026-08-07), which is ahead of every nginx source in the repo (`portal/nginx.conf`, `portal/nginx/default.conf`, `aither-v2/deploy/portal/nginx.conf`, `aither-v2/tools/portal/nginx.conf` — none contain the `/api/v1/models` + `/api/v1/chat/completions` external routes).

### Model ID mapping (legacy source vs live)

| Source | Model IDs |
|--------|-----------|
| `portal/api-gateway.ts` MODEL_MAP (legacy) | `qwen2.5-14b` → `/models/Qwen2.5-14B-Instruct`, `qwen2.5-32b` → `/models/Qwen2.5-32B-Instruct-GPTQ` |
| `portal/server.ts` MODEL_MAP (legacy) | same legacy map |
| Live backend `CURRENT_MODELS` | `qwen2.5-32b-instruct` (scope `model:qwen2.5:chat`, legacy `model:32b:chat`), `qwen3-32b` (scope `model:qwen3:chat`) |
| GOVERNANCE scope contract | `qwen2.5-32b-instruct` → `model:qwen2.5:chat`; `qwen3-32b` → `model:qwen3:chat` |

Live model IDs are the new canonical IDs; legacy map was not reintroduced.

## 6. E2E tests (all through `http://10.129.13.78:30080`)

A temporary test API key was created via the identity API (admin login) to exercise the authenticated path. Key id `21`, prefix `aither_9LfU_uvnIrtyI`, scopes `model:qwen2.5:chat,model:qwen3:chat`, expires in 30 days (Owner may revoke). Full key is not recorded anywhere in this document.

| # | Test | Expected | Actual | Verdict |
|---|------|----------|--------|---------|
| 1 | GET `/api/v1/models` (valid key) | 200, both canonical IDs | 200, `["qwen2.5-32b-instruct","qwen3-32b"]` | PASS |
| 2 | POST chat `qwen2.5-32b-instruct` `stream:false` prompt "Reply exactly: AITHER_OK" | 200, non-empty content | 200, `choices[0].message.content == "AITHER_OK"` | PASS |
| 3 | POST chat `qwen3-32b` | 200, non-empty content | 200, `choices[0].message.content == "AITHER_OK"` | PASS |
| 4 | Invalid model | 4xx (not 500) | 404 `{"detail":"model_not_found: 'nonexistent'"}` | PASS |
| 5 | No auth | 401/403 | 401 `{"detail":"invalid_api_key: Bearer token required"}` | PASS |
| 6 | Wrong auth | 401/403 | 401 `{"detail":"Invalid API key"}` | PASS |

POST accepts `model`, `messages`, `max_tokens`, `temperature`, `stream`; `stream:false` returns OpenAI-compatible JSON with non-empty `choices[0].message.content`.

## 7. Security logging

- Backend source (`/app/app/main.py`) does not log `Authorization`/API key/token/secret/password values (grep-verified).
- After E2E, all running pod logs were scanned for the test key prefix, long `Bearer` tokens, and password/key patterns: **no secret lines found**.
- Pre-existing committed secrets (legacy-format keys in `aither-v2/reports/beta/api-keys.md`, `aither-v2/docs/stage16/API-KEYS.md`, gitleaks logs) predate this task and were not touched.
- Compromised key rotation: **OWNER REQUIRED** (no key was rotated/deleted by this task; no secret value is printed or committed here).

## 8. K8s health

API-path pods all `1/1 Running`: `aither-portal`, `aither-portal-backend`, `aither-bff` (×2), `aither-identity`, `aither-ai-platform`, `vllm-32b-instruct-awq`, `vllm-qwen3-32b-awq`, `aither-portal-frontend`, `aither-redis-rate-limit`.

Backend probes: `/health` 200, `/ready` 200 (`identity: connected`), `/version` 200 (`0.6.0-r7r7-c2-d18`).

Pre-existing out-of-scope conditions (not modified): `aither-gateway` (0/1, readiness 503) and `nginx-gateway-32b` (0/1, readiness 502) — legacy components outside the external API path.

## 9. Ownership gate

Changed repository paths (read-only `git status`): the single new file `docs/evidence/EXT_API_CHAT_RECOVERY_R2.md`.

```
uid 1000 gid 1000 mode 644 docs/evidence/EXT_API_CHAT_RECOVERY_R2.md
```

(ownership set on this exact path only; no recursive chown; repository root ownership unchanged.)

## 10. Conclusion

The Test Zone external API is **already recovered and verified working**:

- `/api/v1/models` → 200 with both canonical model IDs (`qwen2.5-32b-instruct`, `qwen3-32b`).
- `/api/v1/chat/completions` → 200 for both models, OpenAI-compatible, `stream:false` returns non-empty content.
- Invalid model → 404; no auth → 401; wrong auth → 401.

Root cause of the historical 404 is proven (external `/v1/*` route mapping). The deployed ConfigMap already carries the correct chat-completions rewrite; no further runtime correction was required and none was applied (avoiding scope expansion). Only the evidence file was added to the repository.

SECRETS_EXPOSED: NO
