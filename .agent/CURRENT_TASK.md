# AITHER-PORTAL-USER-PATH-HOTFIX-R1

## Authority

Executor: **Hermes only**. OpenAI Codex is not authorized for Aither.

Baseline: `0c4f59efd528a5ada9ac495baf61a393d4eecb64`
Branch: `aither-v2`

## User-reported production defects

1. In the authenticated Portal chat the user sees: `Каталог моделей недоступен — отправка отключена`.
2. The Portal documentation card `Работа с моделями` still shows the old runtime article headed `РАБОТА С МОДЕЛЯМИ AITHER — Qwen2.5-32B и Qwen3-32B`, version CB-WEBUI-02 / 07 August 2026, instead of the canonical current article.

These user-visible observations override the previous runtime acceptance. Do not claim the Portal is accepted until the browser-facing path is corrected and independently verified.

## Architect diagnosis to verify, then fix

### A. Web-session model catalog wiring defect

Current frontend login stores the Web session identifier/token in `authToken` and `api('/models')` sends it as `Authorization: Bearer <session-id/token>` to `/api/v1/models`.

Current nginx has an exact `/api/v1/models` route to `aither-portal-backend`.

Current `portal-backend/app/main.py::proxy_models()` distinguishes only external API keys starting with `aither_`; every other bearer is proxied to `AI_PLATFORM_URL` as if it were a JWT. A normal Portal session therefore can be misclassified and produce 401/403/503 or an unusable response, leaving the frontend catalog empty.

Required correction:

- Preserve external OpenAI-compatible API-key behavior for `Bearer aither_...`.
- For a normal authenticated Portal session, validate the bearer/session through Identity using the same accepted identity contract used by `/api/v1/auth/me`.
- Return the exact active catalog from the authoritative current model map: `qwen3-32b`, `qwen3.8-27b`, filtered by the user's effective `model:qwen3:chat` entitlement.
- Do not proxy a Portal session identifier to `AI_PLATFORM_URL` merely because it is not an API key.
- Missing/invalid session must fail closed with 401; missing entitlement with 403.
- No substring model routing and no fallback to a retired model.
- Do not change vLLM deployments, model routing, Identity DB, API-key format, or scopes.

If the live runtime service wiring differs from the repository assumption, prove the actual chain first and implement the equivalent fix in the canonical source path; do not guess.

### B. Stale `17_MODEL_USAGE_GUIDE` in browser

Canonical source is `docs/user-package/17_MODEL_USAGE_GUIDE.md` and must describe only `qwen3-32b` and `qwen3.8-27b`.

Required correction:

- Verify the live `/docs/17_MODEL_USAGE_GUIDE.md` bytes, the mounted file inside the active Portal pod, the `aither-portal-docs` ConfigMap key, and the GitHub file.
- Re-sync the ConfigMap from canonical GitHub source if any mismatch exists.
- Make documentation browser-safe against stale cache: `location /docs/` must return explicit `Cache-Control: no-store, no-cache, must-revalidate, max-age=0` (or stricter equivalent), plus suitable legacy no-cache header if needed.
- Locate the frontend `showDoc`/documentation fetch and make it request fresh content (`cache: 'no-store'` and/or a deterministic build revision query). Do not rely only on a user hard refresh.
- Bump the `app.js` cache-busting revision in `index.html` so existing browsers receive the fixed JS.
- Because nginx configuration is loaded at process start, perform a controlled restart/rollout of the Portal after ConfigMap/config synchronization and wait for Ready.

## Runtime deployment rules

- Determine which Deployment/Service currently serves `aither-portal-backend` and which serves the frontend before mutation.
- If `portal-backend/app/main.py` requires a new runtime image, build from the canonical Dockerfile using an immutable task-specific tag/digest, update only the matching Portal Backend deployment image and its source manifest, wait for Ready, and record old/new image identifiers.
- Preserve all existing Secret refs and env settings. **Do not read, print, export, or record Secret values.**
- For frontend/docs, update only `aither-portal-config` and `aither-portal-docs` as required, then perform a controlled rollout of the actual frontend Portal deployment so nginx reloads the new config.
- No changes to Gateway routing/catalog, vLLM deployments, Identity DB, billing DB, reverse-proxy external routing, or unrelated services.

## Required validation

### Source

- `python3 -m py_compile aither-v2/services/portal-backend/app/main.py`
- `node --check aither-v2/services/portal-frontend/app.js`
- `git diff --check`
- `qwen2.5-32b-instruct`, `qwen-14b`, `qwen-32b-base` must not reappear in the active frontend user path.
- Canonical doc 17 must contain both current models and must not present Qwen2.5 as active.

### Browser-facing docs

After rollout, verify both Internet and internal Portal endpoints where available:

- `/docs/17_MODEL_USAGE_GUIDE.md` HTTP 200.
- Response headers explicitly disable stale caching.
- Body contains `qwen3-32b` and `qwen3.8-27b`.
- Body does not contain the obsolete heading `Qwen2.5-32B и Qwen3-32B`.
- Plain URL and a cache-busted URL return the same current canonical content.
- SHA-256: GitHub source == ConfigMap key == mounted pod file == live HTTP body.

### Model catalog path

- Prove the fixed runtime routing chain for `/api/v1/models`.
- Invalid/nonexistent Portal bearer must return controlled 401, not be proxied as a fake AI Platform JWT.
- If a safe existing authenticated test session is available without reading Secret values, verify the browser-equivalent request returns exactly `qwen3-32b` and `qwen3.8-27b` and the selector becomes enabled.
- If no safe authenticated session is available, add a local/in-container integration test using dependency monkeypatch/test client to prove the session branch validates Identity and returns exactly the active pair for `model:qwen3:chat`; clearly mark live authenticated verification as pending final E2E. Do not invent credentials.
- External API-key `/api/v1/models` behavior must remain intact.

## Evidence

Create exactly:

`docs/evidence/AITHER_PORTAL_USER_PATH_HOTFIX_R1.md`

It must include:

- reproduced/diagnosed cause of both user-visible defects;
- exact source changes;
- actual runtime service/deployment chain;
- old/new backend image if rebuilt;
- ConfigMap and rollout details;
- model catalog validation results;
- doc response headers, content checks and SHA-256 chain;
- Portal/backend Ready states and restart counts;
- `BACKEND_MODEL_DEPLOYMENTS_CHANGED: NO`;
- `GATEWAY_ROUTING_CHANGED: NO`;
- `IDENTITY_DB_CHANGED: NO`;
- `SECRETS_EXPOSED: NO`;
- exact `RUNTIME_MUTATIONS`;
- `RESULT: PASS` only if all non-authenticated requirements pass and the session model branch is demonstrably fixed.

STOP after evidence. Do not run the full final authenticated E2E in this task.
