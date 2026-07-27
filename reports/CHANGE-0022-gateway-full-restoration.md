# CHANGE-0022 — GATEWAY FULL RESTORATION REPORT (R7-R5-EMG-GW-R2)

## 1. Executive Summary

**Статус: IN PROGRESS** — Gateway задеплоен и работает как FastAPI/ASGI-приложение, но задание выполнено частично. BFF cutover не произведён, значительная часть функционала не подключена или не протестирована.

---

## 2. Repository & Baseline

| Параметр | Значение |
|---|---|
| Repository | `dedvmedved-dot/aither-project` |
| Branch | `aither-v2` |
| Working directory | `/root/aither-project-r7-canonical` |
| Baseline commit (checkpoint) | `e82f245` |
| Final local HEAD | `773fc1d` |
| Remote HEAD | `773fc1d` |
| Working tree | 1 untracked file (`ROADMAP-RECOVERY.md`) |

---

## 3. Commit Chain (append-only)

```
773fc1d feat(gateway): CHANGE-0022 — Gateway deployed and running
c1aed63 fix(gateway): lazy reaper DB pool, add /var/log/aither emptyDir
744cfa8 fix(gateway): Dockerfile remove deps.py, finalize app.py
db4693f fix(gateway): update catalog.py for new catalog.yaml format
374fa68 chore(gateway): remove conflicting subagent dependencies.py
9dae617 feat(gateway): FastAPI app + core modules
be9c4ee infra(gateway): K8s manifests, updated catalog, Dockerfile
e82f245 docs(audit): verify #5 Gateway — baseline (978 loc, NOT deployed)
```

**18 files changed, 1230 insertions, 279 deletions** относительно baseline.

---

## 4. Runtime Objects (Kubernetes)

| Объект | Состояние |
|---|---|
| **Deployment** `aither-gateway` | 2/2 Ready, N7 + N8 |
| **Service** `aither-gateway` | ClusterIP `10.103.10.83:8000` |
| **Image** | `10.129.13.78:5000/aither-gateway:change-0022-190545` |
| **Namespace** | `aither-inference` |
| **NetworkPolicy** | Создан (manifest) |
| **PDB** | Создан (manifest) |
| **HPA** | Manifest существует, НЕ применён |

---

## 5. Архитектура: Before vs After

```
BEFORE (baseline e82f245):
  Клиент → Portal → BFF → vllm-14b (прямой)
  Клиент → Portal → BFF → nginx-gateway-32b → vllm-32b
  gateway.py (978 loc) — код существует, НЕ в runtime

AFTER (HEAD 773fc1d):
  Gateway задеплоен и работает, НО BFF cutover НЕ выполнен:
  Клиент → Portal → BFF → vllm-14b (по-прежнему прямой)
  Клиент → Portal → BFF → nginx-gateway-32b → vllm-32b
  Gateway работает отдельно, готов к приёму трафика
```

---

## 6. Файлы Gateway: полный инвентарь

| Файл | LOC | Статус | Назначение |
|---|---|---|---|
| `app.py` | 188 | ✅ **Active** | FastAPI app: lifespan, middleware, endpoints |
| `config.py` | 152 | ✅ **Active** | 30+ env vars, Settings dataclass |
| `auth.py` | 78 | ✅ **Active** | JWT RS256 + API key (fail-closed) |
| `routing.py` | 46 | ✅ **Active** | Model routing via catalog |
| `rate_limit.py` | 34 | ✅ **Active** | Redis Lua RPM/TPM/daily |
| `billing.py` | 75 | ⚠️ **Partial** | reserve/settle/refund — graceful fail |
| `usage.py` | 216 | ✅ **Active** | Usage records collector |
| `catalog.py` | 97 | ✅ **Active** | Catalog loader, ModelEntry |
| `catalog.yaml` | — | ✅ **Active** | 2 модели: qwen-14b, qwen-32b-base |
| `security.py` | 114 | ❌ **Not called** | Prompt injection, DLP |
| `security_egress.py` | 398 | ❌ **Not called** | Egress filter + SIEM |
| `vault.py` | 259 | ❌ **Not called** | HashiCorp Vault integration |
| `admin.py` | 290 | ⚠️ **Stubs only** | Админ-эндпоинты в app.py — заглушки |
| `metrics.py` | 169 | ❌ **Not exposed** | `/metrics` → 404, не зарегистрирован |
| `hybrid_rag.py` | 157 | ❌ **Not connected** | Hybrid RAG engine |
| `wiki_graph.py` | 340 | ❌ **Not connected** | Wiki knowledge graph |
| `reaper.py` | 100 | ⚠️ **Partial** | Reservation reaper — lazy pool |
| `siem.py` | — | ❌ **MISSING** | Файл отсутствует |
| `gateway.py` | 978 | 📦 **Legacy** | Старый HTTPServer, не используется |

**Total: 2,713 LOC Python в 16 файлах + catalog.yaml**

---

## 7. Функциональная матрица

### 7.1 Reverse Proxy / Model Routing

| Endpoint | Статус | Детали |
|---|---|---|
| `GET /health` | ✅ 200 | `{"status":"ok","service":"aither-gateway"}` |
| `GET /ready` | ✅ 200 | `{"status":"degraded"}` — Redis ✅, PG ❌ |
| `GET /v1/models` | ✅ 200 | 2 модели: qwen-14b, qwen-32b-base |
| `POST /v1/chat/completions` | ✅ Реализован | Pipeline: auth→RL→billing→upstream |
| `POST /v1/completions` | ✅ Реализован | Аналогично chat |

### 7.2 Authentication

| Проверка | Статус |
|---|---|
| Fail-closed (неизвестный token → 401) | ✅ |
| JWT RS256 validation | ✅ |
| API key (ak-*) validation | ✅ |
| Admin key из Secret | ✅ (403 без ключа) |
| Legacy key fallback удалён | ✅ |

### 7.3 Rate Limiting

| Проверка | Статус |
|---|---|
| Redis подключён | ✅ |
| RPM/TPM/daily Lua скрипты | ✅ Реализованы |
| Атомарность (Lua INCR + EXPIRE) | ✅ |
| Тестирование между репликами | ❌ Не тестировалось |
| Fail-closed при недоступности Redis | ❌ Не тестировалось |

### 7.4 Billing

| Функция | Статус |
|---|---|
| Код `reserve/settle/refund` | ✅ Написан |
| Вызов в пайплайне | ⚠️ `if True: # billing always attempted, fails gracefully` |
| PostgreSQL pool | ❌ Не настроен (`PG_HOST=aither-postgres` — хост не резолвится) |
| Фактическое списание | ❌ Не работает |
| Idempotency | ❌ Не реализована |

### 7.5 Security (Ingress + Egress)

| Модуль | Статус |
|---|---|
| `security.py` (114 loc) | ❌ Не вызывается в пайплайне |
| `security_egress.py` (398 loc) | ❌ Не вызывается в пайплайне |
| SIEM | ❌ `siem.py` отсутствует |
| Prompt injection detection | ❌ Не тестировалось |

### 7.6 Vault

| Функция | Статус |
|---|---|
| `vault.py` (259 loc) | ❌ Не импортируется и не вызывается |
| Режимы VAULT_REQUIRED | ❌ Не реализованы |

### 7.7 Admin API

| Endpoint | Статус |
|---|---|
| `GET /admin/queues` | ⚠️ Stub: `{"queues":[]}` |
| `GET /admin/models` | ⚠️ Stub: список из каталога |
| `POST /admin/models/{mid}/drain` | ⚠️ Stub: `{"drained": mid}` |
| `GET /admin/health` | ⚠️ Stub: `{"status":"ok"}` |
| `GET /admin/metrics` | ❌ Не реализован |
| `GET /admin/reaper` | ❌ Не реализован |
| `GET /admin/orgs/{org_id}` | ❌ Не реализован |
| Защита (user → 403, admin → разрешён) | ✅ |

### 7.8 RAG

| Endpoint | Статус |
|---|---|
| `GET /v1/rag/status` | ✅ `{"ready": false}` — не настроен |
| `POST /v1/rag/ingest` | ❌ Не реализован |
| `POST /v1/rag/query` | ❌ Не реализован |
| `POST /v1/rag/hybrid-query` | ❌ Не реализован |
| `POST /v1/rag/wiki-ingest` | ❌ Не реализован |

### 7.9 Metrics / Prometheus

| Функция | Статус |
|---|---|
| `prometheus-client` в requirements.txt | ✅ |
| `metrics.py` (169 loc) | ✅ Написан |
| `/metrics` endpoint в app.py | ❌ **Не зарегистрирован → 404** |

### 7.10 Прочее

| Функция | Статус |
|---|---|
| Streaming (SSE) | ✅ Реализован |
| Upstream timeout → 504 | ✅ Реализован |
| Cost-aware routing | ❌ Не реализован |
| Model ACL / Tier access | ❌ Не реализован |
| Wiki Graph | ❌ Не подключён |
| Reservation Reaper | ⚠️ Код есть, не тестировался |
| PostgreSQL миграции | ❌ Не созданы |

---

## 8. BFF Integration

**Статус: НЕ ВЫПОЛНЕН**

- BFF по-прежнему направляет 14B напрямую в vLLM
- BFF по-прежнему направляет 32B через nginx-gateway-32b
- Gateway не участвует в рабочем тракте
- `nginx-gateway-32b` не классифицирован как rollback component

---

## 9. Тестирование

**Статус: НЕ ВЫПОЛНЕН**

| Категория | Статус |
|---|---|
| Static tests (ruff/mypy) | ❌ |
| Unit tests | ❌ |
| Integration tests (GW-001…GW-010) | ❌ |
| Auth tests (AUTH-001…AUTH-008) | ❌ |
| Rate limit tests (RL-001…RL-007) | ❌ |
| Billing tests (BILL-001…BILL-008) | ❌ |
| Security tests (SEC-001…SEC-008) | ❌ |
| RAG tests (RAG-001…RAG-008) | ❌ |
| Vault tests (VAULT-001…VAULT-006) | ❌ |
| Admin tests (ADM-001…ADM-008) | ❌ |
| Metrics/SIEM tests (MET-001…MET-005, SIEM-001…SIEM-004) | ❌ |
| E2E Portal tests | ❌ |
| Load tests | ❌ |
| Failover tests | ❌ |
| Cutover evidence | ❌ |
| Rollback evidence | ❌ |
| Secret scan | ❌ |

---

## 10. Evidence

**Статус: НЕ СОЗДАН**

Каталог `reports/evidence/CHANGE-0022/` и его подкаталоги (`00-baseline/` … `17-secret-scan/`) отсутствуют.

Итоговый отчёт `reports/CHANGE-0022-gateway-full-restoration.md` отсутствует.

Дельта `reports/CHANGE-0022-runtime-git-delta.md` отсутствует.

---

## 11. Ключевые дефекты и блокеры

| ID | Дефект | Severity | Статус |
|---|---|---|---|
| GW-DEF-001 | `/metrics` endpoint не зарегистрирован → 404 | High | Open |
| GW-DEF-002 | `siem.py` отсутствует | High | Open |
| GW-DEF-003 | Billing: PostgreSQL не подключён, reserve/settle/refund не работают | High | Open |
| GW-DEF-004 | Security ingress/egress не вызываются в пайплайне | Critical | Open |
| GW-DEF-005 | Vault не подключён | High | Open |
| GW-DEF-006 | RAG endpoints (ingest/query/hybrid-query/wiki-ingest) не реализованы | Medium | Open |
| GW-DEF-007 | Admin endpoints возвращают заглушки | Medium | Open |
| GW-DEF-008 | Cost-aware routing / Model ACL не реализованы | Medium | Open |
| GW-DEF-009 | BFF cutover не выполнен — Gateway не в рабочем тракте | Critical | Open |
| GW-DEF-010 | 0 тестов выполнено | Critical | Open |
| GW-DEF-011 | 0 evidence артефактов создано | High | Open |
| GW-DEF-012 | PostgreSQL миграции не созданы | Medium | Open |
| GW-DEF-013 | HPA не применён | Low | Open |
| GW-DEF-014 | ServiceMonitor не создан | Low | Open |

---

## 12. Финальная функциональная матрица (40 пунктов задания)

| № | Функция | Code | Deploy | FuncTest | SecTest | Status |
|---|---|---|---|---|---|---|
| 1 | Reverse proxy/routing | ✅ | ✅ | ❌ | ❌ | PARTIAL |
| 2 | Redis RPM/TPM/quota | ✅ | ✅ | ❌ | ❌ | PARTIAL |
| 3 | JWT delegation | ✅ | ✅ | ❌ | — | PARTIAL |
| 4 | API keys/Vault | ✅/❌ | ❌ | ❌ | ❌ | FAIL |
| 5 | Billing | ⚠️ | ❌ | ❌ | ❌ | FAIL |
| 6 | Usage Collector | ✅ | ✅ | ❌ | — | PARTIAL |
| 7 | Model Catalog | ✅ | ✅ | ❌ | — | PARTIAL |
| 8 | AI Security ingress | ✅ | ❌ | ❌ | ❌ | FAIL |
| 9 | Security Egress | ✅ | ❌ | ❌ | ❌ | FAIL |
| 10 | SIEM | ❌ | ❌ | ❌ | ❌ | FAIL |
| 11 | Admin API | ⚠️ | ⚠️ | ❌ | ✅ | PARTIAL |
| 12 | TTFT/Metrics | ✅ | ❌ | ❌ | — | FAIL |
| 13 | RAG | ❌ | ❌ | ❌ | ❌ | FAIL |
| 14 | Wiki Graph/Hybrid RAG | ✅ | ❌ | ❌ | — | NOT TESTED |
| 15 | Reservation Reaper | ✅ | ❌ | ❌ | — | NOT TESTED |
| 16 | Cost-aware routing | ❌ | ❌ | ❌ | — | NOT TESTED |
| 17 | Model ACL/Tiers | ❌ | ❌ | ❌ | — | NOT TESTED |
| 18 | 14B end-to-end | ❌ | ❌ | ❌ | — | NOT TESTED |
| 19 | 32B end-to-end | ❌ | ❌ | ❌ | — | NOT TESTED |
| 20 | Portal end-to-end | ❌ | ❌ | ❌ | — | NOT TESTED |

**Итого: 0/20 PASS, 7/20 FAIL, 5/20 PARTIAL, 8/20 NOT TESTED**

---

## 13. Hermes Status

```
CHANGE-0022: IN PROGRESS
Emergency mode: ACTIVE
BFF cutover: NOT PERFORMED
Full Gateway deployment: PARTIAL
Production acceptance: NOT GRANTED
Security scanning: NOT PERFORMED
Tests executed: 0
Evidence created: 0

Hermes: STOPPED — awaiting next directive
```

---

## 14. Что сделано vs что осталось

**Сделано:**
1. ✅ FastAPI Gateway app (app.py + 7 core modules)
2. ✅ K8s manifests (Deployment, Service, ConfigMap, NetworkPolicy, PDB)
3. ✅ Docker image build + push
4. ✅ Deploy (2/2 replicas Running, N7 + N8)
5. ✅ Health/Ready/Models endpoints working
6. ✅ Git: 8 append-only commits, pushed to origin/aither-v2

**Не сделано (основные блоки):**
1. ❌ BFF cutover to Gateway
2. ❌ Security ingress/egress integration + testing
3. ❌ SIEM module creation
4. ❌ Vault integration
5. ❌ PostgreSQL + Billing activation
6. ❌ RAG endpoints
7. ❌ /metrics endpoint registration
8. ❌ All testing (0 tests run)
9. ❌ All evidence (0 artifacts)
10. ❌ Load/failover/rollback testing
