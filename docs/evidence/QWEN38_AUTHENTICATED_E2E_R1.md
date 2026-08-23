# Qwen3.8 Authenticated E2E — R1 (Execution Evidence)

## Task / Result
- task_id: `AITHER-QWEN38-AUTHENTICATED-E2E-R1`
- executor: `hermes`
- mode: `NARROW_AUTHENTICATED_EXTERNAL_API_E2E`
- branch: `aither-v2`
- baseline_sha: `3c58659027af3ec62918f0e11f14ec976c2e4533`
- HEAD: `fb227cbcfbed959dfb7feb7529e40aceb0b4bcf1`
- baseline is parent of HEAD: **YES** (`3c58659…` → `fb227cb…`, diff baseline..HEAD = только `.agent/CURRENT_TASK.json` + `.agent/CURRENT_TASK.md`)
- result: **OWNER_REQUIRED** — отсутствует безопасная уже существующая Test Zone credential/session для штатного создания временного API key

## Timestamps (UTC)
- evidence start (runner): `2026-08-23T09:2x:xxZ`
- evidence collected: `2026-08-23T09:20Z` – `2026-08-23T09:31Z`

## Preflight runtime state (зафиксировано без изменений)

| Объект | Состояние |
|--------|-----------|
| `vllm-qwen38-27b-fp8` (n7) | Deployment 1/1; pod `…-5b4c7bdf57-qwdcq` Running, restarts=0, node n7; `/health` → 200 |
| `vllm-qwen3-32b-awq` (n8) | Deployment 1/1; pod `…-86cb6c9845-n2xpg` Running, restarts=0, node n8; `/health` → 200 |
| `vllm-32b-instruct-awq` (Qwen2.5) | Deployment **0/0** (replicas=0) — как требуется |
| `vllm-14b-instruct`, `vllm-32b-gptq` | 0/0 (pre-existing legacy, вне scope) |
| временные `compat` workloads | **отсутствуют** |
| Portal Backend | Deployment 1/1; `/health` 200, `/ready` 200, `/version` 200 |
| Identity | `/health` 200, `/ready` 200 |

## Test Zone (http://10.129.13.78:30080) — no-auth reachability

| Request | Status | Примечание |
|---------|--------|-----------|
| GET `/` | 200 | SPA |
| GET `/health` | 200 | — |
| GET `/ready` | 200 | — |
| GET `/api/v1/models` | 401 | authentication required |
| GET `/api/v1/chat/completions` | 405 | POST-only route (не 404) |
| POST `/v1/identity/auth` (probe, invalid creds) | 401 | Identity API route доступна через Test Zone |
| GET `/v1/identity/api-keys` | 401 | authentication required |
| POST `/v1/identity/api-keys` | 401 | authentication required |

## Определение безопасной тестовой авторизации (без чтения значений)

Проверены имена/ключи Secret, окружение executor и документация репозитория на предмет уже существующей credential/session, явно предназначенной для автоматизированного Test Zone/E2E:

- `aither-identity-secret` содержит только `IDENTITY_ADMIN_USER`/`IDENTITY_ADMIN_PASS` (bootstrap admin, это Owner production-аккаунт — **запрещён** п.7), `IDENTITY_INTERNAL_API_SECRET`, `IDENTITY_SECRET_KEY` (служебные).
- `aither-bff-auth` содержит `ADMIN_USERNAME=owner-r5` (Owner production), `BETA_USERS` (beta01/beta02 — только SHA-256 хэши, без plaintext; ранее скомпрометированы и ротированы в R5).
- Окружение executor: `AITHER_32B_API_KEY` = внутренний upstream-токен vLLM (Secret `vllm-api-key`/`VLLM_API_KEY`), а не user credential/session внешнего API.
- Отдельного plaintext пароля, bearer/session token'а, K8s Secret value или документа с безопасной Test Zone credential **не существует**.

Вывод: единственный блокер — отсутствие безопасной уже существующей Test Zone authentication/session. Согласно п.7 и разделу OWNER_REQUIRED — создание ничего не выполнялось, обход Identity не предпринимался.

## Authenticated E2E — таблица результатов (A–G)

Все authenticated проверки **NOT EXECUTED** (нет допустимой авторизации).

| # | Проверка | Ожидание | Факт | Verdict |
|---|----------|----------|------|---------|
| A | Authenticated `GET /api/v1/models` | 200, `qwen3-32b` + `qwen3.8-27b`, без `qwen2.5-32b-instruct` | 401 (no auth) | NOT EXECUTED |
| B | `POST /api/v1/chat/completions` `qwen3-32b` `stream=false` | 200, OpenAI JSON, content non-empty | — | NOT EXECUTED |
| C | `POST /api/v1/chat/completions` `qwen3.8-27b` `stream=false` | 200, n7/Qwen3.8 routing | — | NOT EXECUTED |
| D | Streaming `stream=true` (обе модели) | 200, valid SSE, >=1 delta, no cross-routing | — | NOT EXECUTED |
| E | Invalid model `aither-invalid-model-e2e` | 4xx `model_not_found`, no fallback/5xx | — | NOT EXECUTED |
| F | Scope semantics: только `model:qwen3:chat` для обеих моделей | обе доступны | — | NOT EXECUTED |
| G | Revoke proof + повторный запрос с revoked key | 401/403, key отсутствует в списке | — | NOT EXECUTED |

## Model routing conclusions (source-level, read-only)

Проверка source `aither-v2/services/portal-backend/app/main.py` (результат предшествующего permanent cutover, изменений не вносил):

- `CURRENT_MODELS = {"qwen3-32b": {"scope": "model:qwen3:chat"}, "qwen3.8-27b": {"scope": "model:qwen3:chat"}}`.
- `ALLOWED_MODELS = {"qwen3-32b", "qwen3.8-27b"}`; `qwen2.5-32b-instruct` отсутствует в каталоге.
- Обе активные модели требуют единственный scope `model:qwen3:chat` (соответствует GOVERNANCE Scope Contract и п.6 задачи).
- Invalid model → `400 model_not_found` (fail-closed, без fallback).

Runtime подтверждение маршрутизации (n7/Qwen3.8, n8/Qwen3-32B) достигнуто на уровне pod/node placement; authenticated запросы не выполнялись (OWNER_REQUIRED).

## Post-check runtime state

| Объект | Состояние |
|--------|-----------|
| `vllm-qwen38-27b-fp8` (n7) | 1/1, restarts=0, `/health` 200 |
| `vllm-qwen3-32b-awq` (n8) | 1/1, restarts=0, `/health` 200 |
| `vllm-32b-instruct-awq` (Qwen2.5) | replicas=0 |
| Portal Backend | 1/1, `/health` 200, `/ready` 200 |
| source worktree | чист, кроме нового evidence (до host finalization) |
| model/runtime/config mutation | **не выполнялась** |

## Cleanup proof

- `EPHEMERAL_KEY_CREATED: NO`
- `EPHEMERAL_KEY_REVOKED: N/A`
- Временный API key не создавался; пользователи/организации/scopes/permanent keys не создавались; runtime не менялся. Очистка не требуется.

## Repository evidence

Изменён ровно один путь (только allowed_path из CURRENT_TASK.json):

```
docs/evidence/QWEN38_AUTHENTICATED_E2E_R1.md
```

`.agent/*` не изменялся. Git metadata write не выполнялся (executor не пишет Git; finalization — за host supervisor).

## Concluding fields

- `TASK_ID: AITHER-QWEN38-AUTHENTICATED-E2E-R1`
- `EPHEMERAL_KEY_CREATED: NO`
- `EPHEMERAL_KEY_REVOKED: N/A`
- `AUTHENTICATED_TESTS_A_G: NOT EXECUTED`
- `MODEL_LIST_AUTHENTICATED: NOT EXECUTED`
- `CHAT_NONSTREAMING: NOT EXECUTED`
- `CHAT_STREAMING: NOT EXECUTED`
- `INVALID_MODEL: NOT EXECUTED`
- `SCOPE_SEMANTICS: NOT EXECUTED`
- `REVOKE_PROOF: NOT EXECUTED`
- `RUNTIME_MUTATION: NONE`
- `RESULT: OWNER_REQUIRED`
- `OWNER_REQUIRED_REASON: safe Test Zone credential/session unavailable`

SECRETS_EXPOSED: NO
