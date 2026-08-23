# AITHER-QWEN38-AUTHENTICATED-E2E-R1

## Цель
Независимо подтвердить authenticated end-to-end работу внешнего OpenAI-compatible API Test Zone после permanent cutover для обеих активных моделей:

- `qwen3-32b` → n8;
- `qwen3.8-27b` → n7.

Это тест, а не этап разработки. Не менять source, deployments, routing, catalog, Identity schema или модельные manifests.

## Критические требования к поведению Hermes

1. GitHub — Source of Truth. Работать только с baseline и `allowed_paths` из `CURRENT_TASK.json`.
2. Запрещены прямые SQL/SQLite операции, чтение/изменение Identity DB, подделка JWT, ручная вставка API key в БД и обход штатной Identity API.
3. Для E2E разрешён только штатный API lifecycle: authenticated user/session → `POST /v1/identity/api-keys` → тесты → `DELETE /v1/identity/api-keys/{key_id}`.
4. Создать ровно один временный API key со scope **только** `model:qwen3:chat`, коротким сроком жизни и очевидным тестовым именем `aither-qwen38-e2e-r1`.
5. Raw API key, bearer/session token, пароль, K8s Secret value, prefix ключа и любые credential-фрагменты запрещено печатать, коммитить, логировать или включать в evidence. Отключить shell tracing; не использовать `curl -v` и не сохранять Authorization headers.
6. Секретный материал допускается только в памяти процесса для выполнения теста. Не писать его во временные файлы, history, environment dumps, evidence или Git.
7. Не использовать личные/production credentials Owner. Допустима только уже существующая credential/session, явно предназначенная для автоматизированного Test Zone/E2E. Сначала определить её наличие без чтения значения. Если безопасной тестовой авторизации нет — завершить `OWNER_REQUIRED`, не обходить ограничение.
8. Если временный ключ был создан, его отзыв/удаление обязателен в `finally` независимо от PASS/FAIL. После удаления подтвердить, что этот же ключ больше не проходит auth.
9. Не менять n7/n8 model deployments. При любом сбое теста runtime оставить как есть.
10. Не создавать дополнительных пользователей, организаций, scopes, permanent keys или credentials.
11. Evidence должен содержать только статусы, модели, HTTP codes, безопасные метаданные и выводы. `SECRETS_EXPOSED: NO|YES` обязателен.

## Предварительные проверки

Зафиксировать без изменений:

- `vllm-qwen38-27b-fp8` на n7: desired/ready/available, pod, restarts, `/health`;
- `vllm-qwen3-32b-awq` на n8: desired/ready/available, pod, restarts, `/health`;
- `vllm-32b-instruct-awq` (Qwen2.5): `replicas=0`;
- Portal Backend: `1/1`, `/health=200`, `/ready=200`;
- отсутствие временных `compat` workloads.

Если любой из двух активных model backends не healthy — `BLOCKED`, authenticated E2E не продолжать.

## Авторизация и временный ключ

Использовать только штатную Identity API. API semantics уже подтверждены source:

- `POST /v1/identity/api-keys` — создать API key;
- `DELETE /v1/identity/api-keys/{key_id}` — revoke/delete owner key.

Параметры временного key:

- name: `aither-qwen38-e2e-r1`;
- purpose: `agent` или `test` согласно валидному API contract;
- scopes: ровно `["model:qwen3:chat"]`;
- минимально доступный expiry (не более 1 дня, если API допускает 1 день).

Не фиксировать key id, prefix или raw key в evidence, если это не требуется для доказательства; достаточно `EPHEMERAL_KEY_CREATED: YES` и `EPHEMERAL_KEY_REVOKED: YES`.

Если безопасная тестовая authenticated session/credential отсутствует, завершить:

`RESULT: OWNER_REQUIRED`

с указанием только причины уровня `safe Test Zone credential/session unavailable`; ничего не создавать и не менять.

## Authenticated E2E — обязательные проверки

Base Test Zone: `http://10.129.13.78:30080`

### A. Model list

Authenticated `GET /api/v1/models`:

PASS если:

- HTTP 200;
- присутствует `qwen3-32b`;
- присутствует `qwen3.8-27b`;
- `qwen2.5-32b-instruct` отсутствует;
- нет лишней активной inference model из старого каталога.

### B. Non-streaming chat — qwen3-32b

`POST /api/v1/chat/completions`, model=`qwen3-32b`, `stream=false`, нейтральный детерминированный тестовый prompt, небольшой `max_tokens`.

PASS если:

- HTTP 200;
- OpenAI-compatible JSON;
- response `model` соответствует `qwen3-32b` либо безопасно подтверждён upstream routing;
- assistant content непустой;
- нет 404/5xx/routing fallback.

### C. Non-streaming chat — qwen3.8-27b

То же для model=`qwen3.8-27b`.

PASS criteria идентичны; отдельно подтвердить, что запрос обслужен n7/Qwen3.8, а не n8/Qwen3-32B.

### D. Streaming

Для каждой активной модели выполнить короткий `stream=true` запрос.

PASS если:

- HTTP 200;
- получен валидный SSE/OpenAI-compatible stream;
- есть минимум один content/reasoning delta и корректное завершение потока;
- нет cross-routing между моделями.

Не сохранять полный generated text; достаточно безопасного структурного факта `STREAM_VALID: YES`.

### E. Invalid model с валидным key

Отправить authenticated request с моделью `aither-invalid-model-e2e`.

PASS если:

- controlled 4xx (`404 model_not_found` ожидаемо для external route);
- запрос не попал ни на n7, ни на n8;
- нет fallback и нет 5xx.

### F. Scope/catalog semantics

Временный key имеет только `model:qwen3:chat`; обе активные модели должны быть доступны с этим scope. Не добавлять `model:32b:chat`, `model:qwen2.5:chat` или другие scopes.

### G. Revoke proof

После всех тестов немедленно удалить временный key через штатный Identity DELETE endpoint.

Затем повторить один безопасный запрос с тем же raw key, всё ещё находящимся только в памяти процесса.

PASS если:

- ключ после revoke получает 401/403 invalid/revoked key;
- `EPHEMERAL_KEY_REVOKED: YES`;
- не осталось тестового key `aither-qwen38-e2e-r1` в owner key list (проверить через API без raw key material).

## Post-check

После E2E снова подтвердить:

- n7 Qwen3.8 `1/1`, `/health=200`, restarts без неожиданного роста;
- n8 Qwen3-32B `1/1`, `/health=200`;
- Qwen2.5 `replicas=0`;
- Portal Backend `1/1`, health/ready 200;
- source worktree чист, кроме evidence до host finalization;
- никакой model/runtime/config mutation не выполнено.

## PASS / BLOCKED / OWNER_REQUIRED

### PASS
Только если одновременно:

1. authenticated model list корректен;
2. non-streaming chat 200 для обеих моделей;
3. streaming корректен для обеих моделей;
4. invalid model fail-closed без fallback;
5. обе модели работают через единственный scope `model:qwen3:chat`;
6. temporary API key создан штатным API и гарантированно revoked/deleted;
7. post-revoke auth check отрицательный;
8. n7/n8/Portal остаются healthy;
9. secrets не попали в evidence/log/Git.

### OWNER_REQUIRED
Если единственный блокер — отсутствие безопасной уже существующей Test Zone authentication/session для штатного создания временного key. Не использовать production/Owner password и не обходить Identity.

### BLOCKED
Любая техническая ошибка runtime/API/routing/auth cleanup, невозможность гарантировать revoke, изменение runtime вне scope или секретная утечка.

## Evidence

Создать только:

`docs/evidence/QWEN38_AUTHENTICATED_E2E_R1.md`

Включить:

- task/baseline/HEAD/timestamps;
- preflight runtime state;
- `EPHEMERAL_KEY_CREATED: YES|NO`;
- `EPHEMERAL_KEY_REVOKED: YES|NO|N/A`;
- таблицу HTTP/results A–G;
- model routing conclusions;
- post-check runtime state;
- cleanup proof;
- итог `PASS|BLOCKED|OWNER_REQUIRED`;
- `SECRETS_EXPOSED: NO|YES`.

Никогда не включать raw key, key prefix, bearer/session token, password, secret value или Authorization header.
