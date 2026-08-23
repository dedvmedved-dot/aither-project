# AITHER-QWEN38-AUTHENTICATED-E2E-R2

## Цель
Завершить authenticated end-to-end проверку внешнего OpenAI-compatible API Test Zone для `qwen3-32b` и `qwen3.8-27b`, используя созданный Owner Kubernetes Secret `aither-e2e-user-r1`.

## Безопасность и ограничения

1. Secret `aither-e2e-user-r1` использовать только как источник username/password для входа пользователя `e2e-qwen-test`; значения держать только в памяти процесса.
2. Никогда не печатать, не логировать, не коммитить и не сохранять username/password raw, bearer/session token, raw API key, key prefix, Authorization header или содержимое Secret.
3. Shell tracing (`set -x`) запрещён. `curl -v`, `env`, `printenv`, `kubectl get secret -o yaml/json/jsonpath`, base64 decode Secret запрещены.
4. Разрешено получить Secret программно внутри root Hermes в переменные процесса только для выполнения auth. Любой вывод значений запрещён.
5. Запрещены прямые SQL/SQLite операции, изменение Identity DB, создание/изменение users/org/scopes, подделка JWT и обход Identity API.
6. Использовать штатный lifecycle: login `e2e-qwen-test` → создать ровно один temporary API key через Identity API → выполнить тесты → revoke/delete key → logout → удалить `aither-e2e-user-r1`.
7. Kubernetes Secret `aither-e2e-user-r1` должен быть удалён в обязательном cleanup/finally при любом исходе после успешного чтения credential. Если Secret отсутствует до начала — `OWNER_REQUIRED` без обхода.
8. Model deployments, Portal source/runtime, Identity source/runtime и routing не менять.
9. Evidence: только безопасные статусы/HTTP-коды/model IDs/counts; generated content не сохранять полностью.
10. `SECRETS_EXPOSED: NO|YES` обязателен. При любой утечке — `BLOCKED`.

## Preflight

Подтвердить:
- Secret `aither-e2e-user-r1` существует и содержит keys `username`,`password` по metadata/key names, без вывода values.
- n7 `vllm-qwen38-27b-fp8` 1/1, health 200, restarts stable.
- n8 `vllm-qwen3-32b-awq` 1/1, health 200.
- Qwen2.5 replicas=0.
- Portal Backend 1/1, health/ready 200.

## Authenticated flow

### 1. Login
Используя credential из Secret только в памяти, выполнить штатный `POST /v1/identity/auth`.

PASS если HTTP 200 и authenticated user = `e2e-qwen-test`.
Безопасно зафиксировать только:
- LOGIN_HTTP
- USERNAME_MATCH=yes/no
- role
- org_status
- tier_present yes/no
- scope `model:qwen3:chat` present yes/no
Не фиксировать token.

Если пользователь не имеет активной org/tier/`model:qwen3:chat`, `BLOCKED` с безопасной причиной; не менять entitlement.

### 2. Temporary API key
Создать через `POST /v1/identity/api-keys` ровно один key:
- name `aither-qwen38-e2e-r2`
- purpose `test` если API принимает, иначе `agent`
- scopes только `["model:qwen3:chat"]`
- expiry минимальный доступный, <=1 day.

Raw key держать только в памяти. Key id допускается держать только в памяти для DELETE; в evidence не нужен.

### 3. Authenticated model list
GET `/api/v1/models` с temporary key.
PASS: HTTP 200, IDs ровно `qwen3-32b` и `qwen3.8-27b`; qwen2.5 отсутствует.

### 4. Non-streaming
Для каждой модели POST `/api/v1/chat/completions`, `stream=false`, короткий нейтральный prompt, `max_tokens` небольшой.
PASS: HTTP 200, OpenAI-compatible JSON, assistant content non-empty, returned model/routing соответствует запрошенной модели, нет 5xx/fallback.

### 5. Streaming
Для каждой модели короткий `stream=true`.
PASS: HTTP 200, валидный SSE, >=1 delta, корректное завершение. Полный generated text не писать в evidence.

### 6. Invalid model
С валидным temporary key запрос model=`aither-invalid-model-e2e`.
PASS: controlled 4xx (`404 model_not_found` для external API ожидаемо), без 5xx и fallback.

### 7. Revoke
В обязательном cleanup удалить temporary key штатным `DELETE /v1/identity/api-keys/{id}`.
Затем, пока raw key ещё только в памяти, выполнить один запрос и подтвердить 401/403 revoked/invalid.
После этого очистить raw key variable.

### 8. Logout и Secret cleanup
- logout user session штатным `/v1/identity/logout` если endpoint доступен;
- очистить session/password variables;
- удалить Kubernetes Secret `aither-e2e-user-r1`;
- подтвердить только `SECRET_PRESENT_AFTER_CLEANUP: NO` без чтения values.

## Post-check

Повторно проверить n7/n8/Qwen2.5/Portal состояния. Никакой runtime mutation кроме ephemeral API key/session lifecycle и удаления Owner-created Secret не допускается.

## Evidence
Создать только `docs/evidence/QWEN38_AUTHENTICATED_E2E_R2.md`.

Обязательные поля:
- task_id/baseline/HEAD/timestamps;
- preflight statuses;
- LOGIN_HTTP, USERNAME_MATCH, ORG_ACTIVE, TIER_PRESENT, QWEN3_SCOPE_PRESENT;
- EPHEMERAL_KEY_CREATED yes/no;
- model list IDs (только IDs);
- таблица non-stream/stream status по двум моделям;
- invalid model status;
- EPHEMERAL_KEY_REVOKED yes/no;
- REVOKED_KEY_REJECTED yes/no;
- LOGOUT_DONE yes/no;
- K8S_E2E_SECRET_DELETED yes/no;
- post-check;
- RESULT PASS|BLOCKED|OWNER_REQUIRED;
- SECRETS_EXPOSED NO|YES.

## PASS
Только если login, temporary key, authenticated model list, non-streaming обеих моделей, streaming обеих моделей, invalid-model fail-closed, revoke proof, Secret cleanup и post-health — все PASS.

## BLOCKED
Любая техническая ошибка auth/API/model/routing/stream/revoke/cleanup или entitlement mismatch. Не исправлять систему внутри этой задачи.

## OWNER_REQUIRED
Только если `aither-e2e-user-r1` отсутствует до начала или credential из него не соответствует Owner-created user и безопасное продолжение невозможно. Не обходить.
