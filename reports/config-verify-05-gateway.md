# Отчёт: Gateway (FastAPI + Redis RL) — верификация задачи #5 ROADMAP

**Задача:** #5 — Gateway (FastAPI + Redis RL)
**Дата проверки:** 27.07.2026 18:00 МСК
**Метод:** kubectl, git, анализ кода, live-проверки
**Результат:** ⚠️ ЧАСТИЧНО — Python Gateway не задеплоен, функциональность распределена

---

## 1. Что заявлено в ROADMAP

```
Gateway (FastAPI + Redis RL):
  - FastAPI-шлюз с rate limiting через Redis
  - Проксирует запросы к vLLM
  - Коммит: 5185dc0
```

## 2. Что есть в коде (репозиторий)

### `gateway/gateway.py` — 978 строк ✅

| Модуль | Функция |
|---|---|
| JWT RS256 | Верификация delegation-токенов |
| Rate Limiter | RPM + TPM через Redis sliding window |
| Billing | `reserve → settle → refund` (double-entry) |
| Usage Collector | Точный учёт токенов, `usage_records` |
| Catalog | `catalog.yaml` → динамический роутинг моделей |
| AI Security Gateway | Prompt injection + DLP (29 паттернов) |
| Security Egress | ДСП-фильтр на выходе |
| SIEM | Syslog CEF-форматтер |
| Vault | Внешняя генерация API-ключей |
| Admin API | Очереди, модели, drain |
| TTFT Metrics | Prometheus-метрики |
| Wiki-Graph RAG | Гибридный поиск по графу |
| Reservation Reaper | Фоновый возврат просроченных резервов |

**Код написан. В репозитории. НЕ ЗАДЕПЛОЕН.**

---

## 3. Что реально запущено

### 3.1 nginx-gateway-32b (2 реплики)

| Параметр | Значение |
|---|---|
| Тип | nginx:alpine (reverse proxy) |
| Порт | 8000 (ClusterIP), 30901 (NodePort) |
| Реплики | 2 (N7 + N8) |
| Rate limiting | `limit_req_zone` 300 req/min (nginx-level) |

**Маршруты:**

| Путь | Действие |
|---|---|
| `/healthz` | 200 OK |
| `/ready` | Прокси → vLLM-32b `/health` |
| `/v1/completions` | Прокси → vLLM-32b (rate limited 300 r/m) |
| `/v1/chat/completions` | 422 "does not support chat" |
| `/v1/models` | Прокси → vLLM-32b |
| `/` | 404 |

**НЕТ:** catalog, RAG, security, billing, admin, metrics — только reverse proxy.

### 3.2 aither-bff (2 реплики)

| Параметр | Значение |
|---|---|
| Тип | FastAPI (python:3.11-slim) |
| Rate limiting | ✅ `RATE_LIMIT_ENABLED: true` |
| Redis | ✅ `aither-redis-rate-limit:6379` |
| Chat routing | 14B → прямой vLLM, 32B → nginx-gateway → completions |

### 3.3 aither-redis-rate-limit (1 реплика)

| Параметр | Значение |
|---|---|
| Тип | Redis 7 (Alpine) |
| Используется | BFF для rate limiting, invite codes |

---

## 4. Матрица функций Gateway

| Функция | Код в репо | Задеплоено | Где |
|---|---|---|---|
| **Reverse proxy к vLLM** | ✅ `gateway.py` | ✅ | `nginx-gateway-32b` (только 32B) |
| **Rate Limiting (Redis)** | ✅ `gateway.py` | ✅ | `aither-bff` (RATE_LIMIT_ENABLED) |
| JWT RS256 delegation | ✅ | ❌ | — |
| Billing (reserve→settle) | ✅ | ❌ | — |
| Usage Collector | ✅ | ❌ | — |
| Model Catalog (YAML) | ✅ `catalog.yaml` | ❌ | — |
| AI Security Gateway | ✅ `security.py` | ❌ | — |
| Security Egress (ДСП) | ✅ `security_egress.py` | ❌ | — |
| SIEM (syslog CEF) | ✅ | ❌ | — |
| Vault PKI | ✅ `vault.py` | ❌ | — |
| Admin API | ✅ `admin.py` | ❌ | — |
| TTFT Metrics | ✅ `metrics.py` | ❌ | — |
| Wiki-Graph RAG | ✅ `wiki_graph.py` | ❌ | — |
| Reservation Reaper | ✅ | ❌ | — |

**Задеплоено: 2/14 функций (14%)**

---

## 5. Архитектура (фактическая)

```
Клиент → Portal (nginx) → BFF (FastAPI) ──14B──→ vllm-14b-instruct:8000
                              │
                              ├──32B──→ nginx-gateway-32b:8000 → vllm-32b-gptq:8000
                              │
                              └─Redis─→ aither-redis-rate-limit:6379 (rate limit)
```

Python Gateway (978 строк) с 12 дополнительными модулями **не участвует** в цепочке запросов.

---

## 6. Вывод

| Критерий | Статус |
|---|---|
| FastAPI Gateway в коде | ✅ `gateway.py` 978 строк |
| Gateway задеплоен как под | ❌ Отсутствует |
| Reverse proxy к vLLM | ✅ nginx-gateway-32b (только 32B) |
| Rate limiting через Redis | ✅ BFF использует Redis |
| Catalog (YAML → Gateway) | ❌ Не задеплоен |
| Security Gateway | ❌ Не задеплоен |
| Billing | ❌ Не задеплоен |
| RAG | ❌ Не задеплоен |
| Admin API | ❌ Не задеплоен |
| Metrics | ❌ Не задеплоен |

**Задача #5 ROADMAP («Gateway FastAPI + Redis RL»): код написан (978 строк + 12 модулей), но НЕ ЗАДЕПЛОЕН. Базовая функциональность (прокси + rate limit) работает через BFF + nginx.**
