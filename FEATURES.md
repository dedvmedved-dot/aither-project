# Функционал AI-платформы Aither

**Дата:** 08.07.2026
**Целевая архитектура:** Consumption Layer → Security Layer → Control Plane → Kubernetes Execution Plane

---

## 1. Consumption Layer (Northbound)

Единый вход для клиентов.

| Функция | Статус | Комментарий |
|---|---|---|
| Единый API (OpenAI-совместимый) | ✅ | `/v1/chat/completions` |
| Аутентификация (API-ключи) | ✅ | JWT, org_id |
| Квоты и тарифные классы | ✅ | Rate Limiter RPM/TPM |
| Service profile (приоритеты) | ❌ | Жёсткая привязка модель→провайдер |
| Мультиарендность (org_id) | ✅ | Изоляция по организациям |
| Баланс и биллинг | ✅ | reserve → settle → usage_records |
| Ключи доступа с правами | ⚠️ | Только root-ключи, без ролей |
| Текстовый чат | ✅ | SSE-стриминг |
| Vision (изображения) | ❌ | Модели загружены, API нет |
| Speech (голос) | ❌ | — |
| Embeddings | ❌ | Нет CPU inference pool |

---

## 2. AI Security Gateway

Контроль входа и выхода модели.

| Функция | Статус | Комментарий |
|---|---|---|
| Input filtering (DLP) | ❌ | Детекция чувствительных данных во входе |
| Prompt injection detection | ❌ | Защита от инъекций в промпт |
| Jailbreak detection | ❌ | Детекция попыток обхода ограничений |
| Классификация запроса | ❌ | Категоризация: код/документ/личное |
| Output moderation | ❌ | Фильтрация неприемлемого вывода |
| Output redaction | ❌ | Маскировка служебных данных в ответе |
| Аудит безопасности | ⚠️ | Логи есть, специализированного аудита нет |
| Data masking до модели | ❌ | — |

---

## 3. Control Plane

Выбор модели и маршрута исполнения.

| Функция | Статус | Комментарий |
|---|---|---|
| Каталог моделей | ❌ | Сейчас одна модель жёстко зашита |
| SLA-профили | ❌ | Premium / Basic / Async |
| Cost-aware routing | ❌ | Выбор CPU vs GPU по стоимости |
| Таблицы стоимости маршрутов | ❌ | — |
| Fallback (деградация) | ❌ | При недоступности GPU → CPU |
| Очереди запросов | ❌ | — |
| Маржинальная маршрутизация | ❌ | Max margin при соблюдении SLA |
| Policy flags (RAG/tools/vision) | ❌ | — |
| Reservation Reaper | ⚠️ | День 4, в плане |
| Rate Limiter | ✅ | Redis Lua, RPM/TPM |
| Usage Collector | ✅ | Точный подсчёт токенов |
| Приоритеты запросов | ❌ | — |

---

## 4. Execution Plane (Kubernetes)

| Pool | Функция | Статус | Комментарий |
|---|---|---|---|
| **GPU Inference** | vLLM serving | ✅ | 40.51: Qwen 14B/32B/Coder/Saiga |
| **GPU Inference** | Multimodal (vision/OCR) | ❌ | Модели есть, эндпоинтов нет |
| **GPU Inference** | Long-context serving | ⚠️ | 32K у текущих моделей |
| **GPU Inference** | Второй узел vLLM | ⚠️ | 40.50: ставится NVIDIA |
| **CPU Inference** | Embeddings | ❌ | Нет CPU pool |
| **CPU Inference** | Компактные модели | ❌ | — |
| **CPU Inference** | Batch-обработка | ❌ | — |
| **RAG Data** | Ingestion (парсинг) | ❌ | — |
| **RAG Data** | OCR | ❌ | — |
| **RAG Data** | Чанкинг | ❌ | — |
| **RAG Data** | Embeddings + векторная БД | ❌ | — |
| **RAG Data** | Retrieval с цитируемостью | ❌ | — |
| **MLOps** | Дообучение (fine-tuning) | ❌ | Этап 4 |
| **MLOps** | Model registry | ❌ | — |
| **MLOps** | Evaluation gates | ❌ | — |
| **MLOps** | Controlled rollout | ❌ | — |

**Планировщик:**

| Функция | Статус |
|---|---|
| Node affinity / taints | ❌ |
| Resource quotas | ❌ |
| Priority classes | ❌ |
| Autoscaling по очередям | ❌ |
| Network policies (изоляция) | ❌ |
| Отдельные namespace/SA | ⚠️ Частично |

---

## 5. Observability & Economics

| Функция | Статус | Комментарий |
|---|---|---|
| Latency (p50/p95/p99) | ❌ | Нет Grafana |
| Throughput (RPS) | ❌ | — |
| GPU utilization | ❌ | — |
| Cost per route | ❌ | — |
| Audit trail | ⚠️ | usage_records, нет UI |
| Статистика потребления | ⚠️ | `/v1/usage/stats` есть, дашборда нет |
| Quality metrics (retrieval) | ❌ | — |
| Security events log | ❌ | — |

---

## 6. Портал (ТР №2)

| Функция | Статус |
|---|---|
| Чат-интерфейс | ✅ |
| Выбор модели | ❌ |
| Баланс и история | ⚠️ API есть, UI нет |
| OAuth-вход | ❌ |
| Админ-панель | ❌ |
| Платёжный кабинет | ❌ |

---

## Сводка по этапам

| Этап | Готовность | Ключевые пробелы |
|---|---|---|
| **1. Inference** | 70% | Vision API, embeddings, OAuth, портал |
| **2. Cost-aware routing** | 15% | Control plane, каталог моделей, маршрутизация |
| **3. RAG** | 0% | Весь data plane |
| **4. Fine-tuning** | 0% | Весь MLOps |

---

## Приоритеты (ближайшие 2 недели)

1. 🔴 **AI Security Gateway** — DLP + prompt injection (критично для госкорпорации)
2. 🔴 **Второй vLLM-узел** (40.50) + каталог моделей
3. 🟡 **Control Plane** — cost-aware routing, fallback
4. 🟡 **Observability** — Grafana дашборд
5. 🟢 **OAuth + портал** — пользовательский вход
