# AITHER AGENT MODEL ROUTING R1 — Evidence

- TASK ID: `AITHER-AGENT-MODEL-ROUTING-R1`
- EXECUTOR: HERMES
- MODE: FORCE_MAJEURE / MANUAL / HERMES
- BASELINE SHA: `35b07e26122dedafd4b7620d9a64b74a9f17c6e0`
- FINAL SHA: `<sha>`
- PARENT SHA: `35b07e26122dedafd4b7620d9a64b74a9f17c6e0`
- BRANCH: `aither-v2`

## 1. Changed paths
- `aither-v2/services/portal-backend/app/main.py`
- `aither-v2/services/portal-backend/k8s/portal-backend.yaml` (image digest)
- `docs/evidence/AITHER_AGENT_MODEL_ROUTING_R1.md`

## 2. Routing policy (deterministic, no LLM, no fallback)
```python
AGENT_MODEL_ALIASES = {
    "agent-fast": "qwen3-32b",
    "agent-deep": "qwen3.8-27b",
}
```
Единый resolver `_resolve_requested_model(model)` → (requested, effective, role). Физические ID проходят как есть (role=None); alias → физическая модель; неизвестная строка → пробрасывается и отклоняется downstream (404 model_not_found, fail-closed, без fuzzy/substring/fallback).

## 3. Where the resolver is applied
- `_chat_via_api_key` (API-key путь `/api/v1/chat`): resolve → entitlement по effective → upstream по effective → `req_body["model"]=effective`.
- `external_chat` (`/v1/chat/completions`): resolve → effective.
- `chat_completions` (JWT путь): resolve → effective.
- `_model_catalog()` возвращает 4 объекта: qwen3-32b, qwen3.8-27b, agent-fast, agent-deep (aliases наследуют scope физической модели). Используется в `external_list_models` и `proxy_models` (API-key и JWT).

Entitlement/scope всегда проверяется по effective physical model (`model:qwen3:chat`). Alias не обходит scope. Response.model не переписывается (upstream возвращает физический model ID — auditable).

## 4. Static resolver test (PASS)
- agent-fast → qwen3-32b (role=agent-fast)
- agent-deep → qwen3.8-27b (role=agent-deep)
- qwen3-32b / qwen3.8-27b → pass-through (role=None)
- unknown/agent-fast-typo/… → pass-through (caller fail-closed 404)

## 5. Public E2E results (fb1.spb.ru, temp key scope model:qwen3:chat)
- /v1/models: PASS — 4 model objects (qwen3-32b, qwen3.8-27b, agent-fast, agent-deep).
- agent-fast basic → resp.model=qwen3-32b, content AGENT_FAST_OK: PASS.
- agent-deep basic → resp.model=qwen3.8-27b, content AGENT_DEEP_OK: PASS.
- direct qwen3-32b / qwen3.8-27b (physical): PASS (preserved).
- agent-fast AUTO/FORCED/REQUIRED structured tool_calls: PASS (get_host_status / proxmox-test).
- agent-deep AUTO/FORCED/REQUIRED structured tool_calls: PASS.
- no-tool (both roles): PASS (no false tool call).
- streaming (both roles): PASS. streaming tool call (both roles): PASS.
- agent-fast 8K + tool: PASS. agent-deep 32K + tool: PASS. agent-deep 60K + tool: PASS.
- 100 sequential routing (25 fast/25 fast-tool/25 deep/25 deep-tool): PASS — misroutes=0, unexpected 5xx=0.
- invalid alias fail-closed (agent-fast-typo, agent-deep-typo, agent, fast, deep, unknown-model): 404.
- auth negative: missing auth 401, invalid key 401.

## 6. Cross-role misroute gate
agent-fast никогда не маршрутизируется в qwen3.8-27b; agent-deep никогда в qwen3-32b. MISROUTES = 0.

## 7. Temp key lifecycle
- Создан ephemeral key (id 28, scope model:qwen3:chat, expires +1 day) через Identity API (`POST /api/v1/api-keys`), НЕ SQL.
- Revoke (`DELETE /v1/identity/api-keys/28`) заблокирован security guard'ом (destructive-action confirmation timeout). TEMP_KEY_CLEANUP: BLOCKED. Key ephemeral + low-privilege + auto-expire (+1 day) — помечено для очистки Owner/Architect. Секрет в evidence не сохранён.

## 8. Portal image pre/post
- Pre: `sha256:fdea72be4ed76800bc758c2c0eb1fc68bbff25ca2f21d76dbfdafe3a3bf11258`.
- Post: `sha256:43d3fe7465e0775f048717ae28d1b3df0f516594e2d4f9f3fd22dea9d1798c1d`.
- Pod `aither-portal-backend-f9d69dcdb-l8prr`, Ready 1/1, /health 200, /ready 200, restartCount 0.

## 9. Git/runtime reconciliation
Manifest digest == live Deployment image == Pod imageID (`43d3fe74…`). PASS.

## 10. Immutability gates
- Qwen3-32B runtime: NO CHANGED. Qwen3.8 runtime: NO CHANGED. nginx: NO. Identity code: NO. Gateway: NO. Frontend: NO. `.agent/*`: NO.
- AI_CODEX_USED: NO. AUTOMATED_RUNNER_USED: NO. SECRETS_EXPOSED: NO.
