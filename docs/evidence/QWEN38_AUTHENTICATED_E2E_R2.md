# Qwen3 Authenticated E2E — R2 (Execution Evidence)

## Task / Result
- task_id: `AITHER-QWEN38-AUTHENTICATED-E2E-R2`
- executor: `hermes`
- mode: `NARROW_AUTHENTICATED_EXTERNAL_API_E2E_WITH_EPHEMERAL_SECRET`
- branch: `aither-v2`
- baseline_sha: `8fc9894bdd7843dfbf5aeee2326a4bbfd3f69189`
- HEAD: `e90f672c0b7b44969be34668b04ab6b18d40a283`
- baseline is parent/ancestor of HEAD: **YES** (`git merge-base --is-ancestor` → OK)
- result: **PASS**

## Timestamps (UTC)
- evidence collected: `2026-08-23T10:25Z` – `2026-08-23T10:31Z`
- report finalized: `2026-08-23T10:31:25Z`

## Preflight runtime state (зафиксировано без изменений)

| Объект | Состояние |
|--------|-----------|
| Secret `aither-e2e-user-r1` | существует; keys ровно `username`,`password` (значения не читались/не выводились) |
| `vllm-qwen38-27b-fp8` (n7) | Deployment 1/1; pod `…-5b4c7bdf57-qwdcq` Running, restarts=0, node n7; `/health` → 200 |
| `vllm-qwen3-32b-awq` (n8) | Deployment 1/1; pod `…-86cb6c9845-n2xpg` Running, restarts=0, node n8; `/health` → 200 |
| `vllm-32b-instruct-awq` (Qwen2.5) | Deployment **0/0** (replicas=0) — как требуется |
| Portal Backend | Deployment 1/1; `/health` 200, `/ready` 200, `/version` 200 |
| Identity | Deployment 1/1 |
| Test Zone no-auth reachability | `/` 200, `/health` 200, `/ready` 200, `GET /api/v1/models` 401, `POST /api/v1/chat/completions` 401, `GET /v1/identity/auth` 405 (POST-only) |

## Authenticated flow (credential из Secret — только в памяти процесса, значения не выводились)

### 1. Login
- `LOGIN_HTTP`: 200
- `USERNAME_MATCH`: yes (`e2e-qwen-test`)
- `ROLE`: user
- `ORG_STATUS`: active
- `TIER_PRESENT`: yes
- `QWEN3_SCOPE_PRESENT`: yes (`model:qwen3:chat`)

### 2. Temporary API key
- `EPHEMERAL_KEY_CREATED`: yes (HTTP 201)
- name `aither-qwen38-e2e-r2`, purpose `agent`, scopes `["model:qwen3:chat"]`, expiry 1 day.
- key id / raw key — только в памяти для DELETE; в evidence не фиксировались.

### 3. Authenticated model list
- `GET /api/v1/models` → HTTP 200
- IDs ровно: `qwen3-32b`, `qwen3.8-27b`
- `QWEN25_ABSENT`: yes (qwen2.5 отсутствует)

### 4–5. Chat (non-streaming + streaming), обе модели

| Модель | non-stream HTTP | non-stream content | non-stream model match | stream HTTP | stream SSE | deltas | delta content | [DONE] | Verdict |
|--------|-----------------|--------------------|------------------------|-------------|------------|--------|---------------|--------|---------|
| `qwen3-32b` | 200 | non-empty | yes | 200 | yes | 4 | yes | yes | PASS |
| `qwen3.8-27b` | 200 | non-empty | yes | 200 | yes | 4 | yes | yes | PASS |

Отсутствуют 5xx/fallback; generated text в evidence не сохранялся (только статусы/counts).

### 6. Invalid model (fail-closed)
- model `aither-invalid-model-e2e` → HTTP 404, `detail: model_not_found: 'aither-invalid-model-e2e'`
- без 5xx и fallback → PASS.

### 7. Revoke + proof
- `EPHEMERAL_KEY_REVOKED`: yes (DELETE → HTTP 200)
- `REVOKED_KEY_REJECTED`: yes (повторный запрос revoked key → HTTP 401)
- raw key variable очищена.

### 8. Logout и Secret cleanup
- `LOGOUT_DONE`: yes (`POST /v1/identity/logout` → HTTP 200)
- session/password variables очищены.
- `K8S_E2E_SECRET_DELETED`: yes (Secret `aither-e2e-user-r1` удалён)
- `SECRET_PRESENT_AFTER_CLEANUP`: no (`kubectl get secret` → NotFound)

## Post-check runtime state

| Объект | Состояние |
|--------|-----------|
| `vllm-qwen38-27b-fp8` (n7) | 1/1, restarts=0, `/health` 200 |
| `vllm-qwen3-32b-awq` (n8) | 1/1, restarts=0, `/health` 200 |
| `vllm-32b-instruct-awq` (Qwen2.5) | replicas=0 |
| Portal Backend | 1/1, `/health` 200, `/ready` 200 |
| Secret `aither-e2e-user-r1` | удалён (NotFound) |
| runtime mutation | только ephemeral API key/session lifecycle + удаление Owner-created Secret |

## Repository evidence

Изменён ровно один путь (только allowed_path из CURRENT_TASK.json):

```
docs/evidence/QWEN38_AUTHENTICATED_E2E_R2.md
```

`.agent/*` не изменялся. Git metadata write не выполнялся (executor не пишет Git; finalization — за host supervisor).

## Concluding fields

- `TASK_ID`: `AITHER-QWEN38-AUTHENTICATED-E2E-R2`
- `LOGIN_HTTP`: 200
- `USERNAME_MATCH`: yes
- `ORG_ACTIVE`: yes
- `TIER_PRESENT`: yes
- `QWEN3_SCOPE_PRESENT`: yes
- `EPHEMERAL_KEY_CREATED`: yes
- `MODEL_LIST_IDS`: `qwen3-32b`, `qwen3.8-27b`
- `CHAT_NONSTREAMING`: PASS (обе модели)
- `CHAT_STREAMING`: PASS (обе модели)
- `INVALID_MODEL`: PASS (404 model_not_found, fail-closed)
- `EPHEMERAL_KEY_REVOKED`: yes
- `REVOKED_KEY_REJECTED`: yes
- `LOGOUT_DONE`: yes
- `K8S_E2E_SECRET_DELETED`: yes
- `RESULT`: PASS

SECRETS_EXPOSED: NO
