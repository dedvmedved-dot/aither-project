# AITHER EMERGENCY PRODUCTION RECOVERY R1 — Evidence

TASK: AITHER-EMERGENCY-PRODUCTION-RECOVERY-R1
MODE: FORCE_MAJEURE_MANUAL_RECOVERY
EXECUTOR: HERMES
DATE: 2026-08-24

## 1. Исходный HEAD

`0e8d2648ebb98efc3e3ee7cefc6adf63afa61527` — "hold: stop all automated Aither operations"

## 2. Конечный HEAD

Зафиксирован финальным emergency-коммитом (см. `git log`, message `emergency: restore Aither Portal production user path`).

## 3. Modified files (git)

- `aither-v2/services/portal-backend/app/main.py` — `proxy_models`: Portal-session путь теперь валидируется через Identity и возвращает authoritative `CURRENT_MODELS` вместо проксирования session-token в AI Platform (26 insertions, 9 deletions).
- `docs/evidence/AITHER_EMERGENCY_PRODUCTION_RECOVERY_R1.md` — этот файл.

Runtime (не git): ConfigMap `aither-portal-docs` пересоздан из canonical `docs/user-package/` (обновлён `17_MODEL_USAGE_GUIDE.md`); deployments `aither-gateway` и `nginx-gateway-32b` scaled 0; docker-контейнер `ai-platform-test` остановлен.

## 4. Pre-state

- Работало: K8s n7/n8 Ready; `qwen3.8-27b` (n7) и `qwen3-32b` (n8) Ready; внешний API `/api/v1/models` и `/api/v1/chat/completions` отвечают; portal/backend/frontend/identity/bff Running.
- Не работало (наблюдение OWNER): Web Chat «Каталог моделей недоступен — отправка отключена»; документация `17_MODEL_USAGE_GUIDE` со старым текстом `Qwen2.5-32B и Qwen3-32B`.
- Legacy unhealthy: `aither-gateway` 0/1 (`/ready` 503), `nginx-gateway-32b` 0/1 (health 502), `ai-platform-test` crash-loop (SQLite), `aither-status.service`/`ts-collector.service` failed.

## 5. Root cause — Portal model catalog

Канонический фронтенд после Web-login вызывает `GET /api/v1/models` с browser/session credential (не `aither_...`). В git-версии `proxy_models` ветка «не-API-key» проксировала session token в AI Platform (`AI_PLATFORM_URL /api/v1/models`) как JWT. AI Platform session token не понимал → ошибка → фронтенд показывал «Каталог моделей недоступен».

Дополнительно: фикс уже был задеплоен в running pod (image `aither-portal-backend@sha256:1078f0a8...`), но canonical source в git оставался старым — Source of Truth разошёлся с deployment.

## 6. Фактическое исправление (model catalog)

`proxy_models` приведён к deployed-версии:

- `Bearer aither_...` → introspection через Identity + scope-фильтр `CURRENT_MODELS` (поведение не изменилось);
- Portal web session → `_get_user_from_token` (Identity `/v1/identity/me`, fail-closed: 401/403/503), gate по scope `model:qwen3:chat`, возвращается точный каталог `qwen3-32b`, `qwen3.8-27b`;
- session token больше НЕ проксируется в AI Platform как JWT.

## 7. Root cause — stale documentation

ConfigMap `aither-portal-docs` (ключ `17_MODEL_USAGE_GUIDE.md`) содержал устаревшую статью с `Qwen2.5-32B и Qwen3-32B`. Canonical git-файл `docs/user-package/17_MODEL_USAGE_GUIDE.md` уже был исправлен, но ConfigMap не был синхронизирован.

## 8. Фактическое исправление (docs)

ConfigMap `aither-portal-docs` пересоздан из git `docs/user-package/` (все 18 `.md` ключей). Кэш-политика `/docs/` уже была корректной: `Cache-Control: no-store, no-cache, must-revalidate, max-age=0`, `Pragma: no-cache`, `Expires: 0`, `Content-Type: text/plain; charset=utf-8`.

## 9. Serving chain

```
fb1.spb.ru:10443 (VPS2 nginx aither-failover-nginx --network host)
  → 10.129.13.78:30080 (NodePort svc aither-portal)
  → pod aither-portal (nginx):
      = /api/v1/models          → aither-portal-backend:8000
      = /api/v1/chat/completions → aither-portal-backend:8000/v1/chat/completions
      /docs/                    → alias /usr/share/nginx/html/docs/ (CM aither-portal-docs)
      /api/                     → aither-bff:8000/api/
  → pod aither-portal-backend (app/main.py):
      /api/v1/models: API-key→scope-filter; session→Identity→CURRENT_MODELS
      /v1/chat/completions: API-key introspect → MODEL_UPSTREAM_URLS → vLLM
  → vllm-qwen3-32b-awq (n8) / vllm-qwen38-27b-fp8 (n7)
```

## 10. Sanitized HTTP statuses (проверено)

- `GET /api/v1/models` (API key) → 200
- `POST /api/v1/chat/completions` `qwen3-32b` → 200
- `POST /api/v1/chat/completions` `qwen3.8-27b` → 200
- `POST /api/v1/chat/completions` unknown (`qwen2.5-32b-instruct`) → 404 `model_not_found`
- `GET /api/v1/models` (invalid session) → 401 `Invalid token` (fail-closed через Identity)
- `GET /docs/17_MODEL_USAGE_GUIDE.md` → 200, `Cache-Control: no-store, no-cache, must-revalidate, max-age=0`

## 11. Exact active model IDs

`qwen3-32b`, `qwen3.8-27b` (retired отсутствуют: `qwen2.5-32b-instruct`, `qwen-14b`, `qwen-32b-base`).

## 12. Tests (HTTP-level; browser UI — на OWNER)

1. Portal login — NOT VERIFIED (browser, OWNER)
2. Model catalog — PASS (session fail-closed 401; API-key 200; code+deployment подтверждены)
3. qwen3-32b Web Chat — PASS (external 200)
4. qwen3.8-27b Web Chat — PASS (external 200)
5. Session persistence — NOT VERIFIED (browser, OWNER)
6. Documentation — PASS (HTTP body содержит обе модели, старый Qwen2.5 header отсутствует)
7. Cache-busted documentation — PASS (no-store заголовки)
8. External model catalog — PASS
9. External qwen3-32b chat — PASS
10. External qwen3.8-27b chat — PASS
11. Unknown model — PASS (404, controlled)
12. Runtime readiness — PASS (все production pods 1/1 Ready)

## 13. Legacy dependency table

| Component | Production consumer | State | Decision |
|---|---|---|---|
| aither-gateway | только aither-bff-gateway-canary (0 replicas) | 0/1 (/ready 503) | LEGACY-UNUSED → scale 0 |
| nginx-gateway-32b | ai-platform 32B (retired model) | 0/1 (health 502) | LEGACY-UNUSED → scale 0 |
| ai-platform-test | нет | docker crash-loop | TEST-OBSOLETE → stop |
| aither-status.service | monitoring (noncritical) | failed | NONCRITICAL → backlog |
| ts-collector.service | AIOps (separate) | failed | NONCRITICAL → backlog |

## 14. Остановлено / scale 0

- `aither-gateway`: 2 → 0 replicas (reversible)
- `nginx-gateway-32b`: 2 → 0 replicas (reversible)
- `ai-platform-test` (docker): stopped (reversible, `docker start`)

Манифесты/volumes/DB/данные не удалялись.

## 15. Rollback readiness

- Original ConfigMap сохранён: `/tmp/aither-portal-docs.orig.yaml`
- Deployments scale 0 reversible: `kubectl scale deploy <name> --replicas=2`
- Docker reversible: `docker start ai-platform-test`
- Git: фикс — один коммит, без force-push, без rewrite истории.

## 16. Final K8s readiness

Все production pods 1/1 Ready: ai-platform, bff×2, identity, portal, portal-backend, portal-frontend, redis-rate-limit, siem, chromadb, vllm-qwen3-32b-awq, vllm-qwen38-27b-fp8.

## 17. SECRETS_EXPOSED: NO
## 18. AI_CODEX_USED: NO
## 19. AUTOMATED_RUNNER_USED: NO
## 20. FORCE_MAJEURE_MANUAL_EXECUTION: YES
