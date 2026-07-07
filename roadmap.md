# Дорожная карта Aither — 08.07.2026

> Согласована с целевой архитектурой AI-платформы: Consumption → Security → Control Plane → Execution Plane

---

## Этап 1: Inference (08.07 – 19.07)

**Цель:** стабильный inference-контур, биллинг, 2 узла vLLM, безопасность входа.

### Неделя 1 (08.07 – 12.07) — сквозной сценарий

| День | Задача | Статус |
|---|---|---|
| 1 | `org_id` в делегировании (BFF → Gateway) | ✅ |
| 2 | Rate Limiter (Redis Lua: RPM/TPM) | ✅ |
| 3 | Usage Collector (точный подсчёт токенов) | ✅ |
| 4 | Reservation Reaper (закрытие зависших резервов) | ⬜ |
| 5 | Интеграционный тест: reserve → inference → settle | ⬜ |

### Неделя 2 (15.07 – 19.07) — пилотный показ

| День | Задача |
|---|---|
| 6 | **AI Security Gateway:** prompt injection + DLP (входной фильтр) |
| 7 | OAuth-вход (GitHub) в портал |
| 8 | **Каталог моделей:** выбор модели в чате → маршрутизация |
| 9 | **Второй vLLM-узел** (40.50): загрузка моделей, балансировка |
| 10 | Observability: Grafana (GPU, RPS, балансы) |

**DoD этапа 1:** 2 узла vLLM работают, модель выбирается из каталога, биллинг корректен, Security Gateway фильтрует промпты.

---

## Этап 2: Cost-aware Routing (22.07 – 02.08)

| Задача |
|---|
| Control Plane: SLA-профили (premium/basic/async) |
| Cost-aware routing: выбор CPU vs GPU по стоимости и загрузке |
| Fallback: GPU → CPU при недоступности |
| Таблицы стоимости маршрутов |
| Маржинальная маршрутизация |
| CPU Inference Pool: embeddings, компактные модели |
| Приоритеты запросов и очереди |
| Статистика потребления в портале |
| Платёжный кабинет (ручной topup) |

---

## Этап 3: RAG (05.08 – 23.08)

| Задача |
|---|
| Ingestion pipeline: парсинг документов (PDF, DOCX, HTML) |
| OCR (распознавание сканов) |
| Чанкинг и embeddings |
| Векторная БД (Qdrant/Milvus) |
| Retrieval с цитируемостью источников |
| Access-aware retrieval (ACL на документы) |
| RAG API в едином контракте |
| Security: защита от poisoning, аудит retrieval |

---

## Этап 4: Fine-tuning / MLOps (26.08 – ...)

| Задача |
|---|
| Dataset registry |
| Training jobs (LoRA/QLoRA) |
| Model registry + evaluation gates |
| Controlled rollout (canary → production) |
| Изолированный MLOps-контур |

---

## Параллельные треки (в течение всех этапов)

| Трек | Описание |
|---|---|
| **Безопасность** | Output moderation, redaction, аудит безопасности, key rotation |
| **Observability** | Дашборды, алерты, cost per route |
| **Портал** | Чат, админ-панель, финансы, статистика |
| **Инфраструктура** | 40.50 в кластер, NFS, автомасштабирование |

---

## Что HE делаем

| Задача | Причина |
|---|---|
| mTLS BFF ↔ Core | Не влияет на демо |
| Partial settle | Редкий кейс |
| Webhook / email | Не для MVP |
| CI/CD / Terraform | Внутренняя инженерия |
| Cloud PoC (Yandex Cloud) | Отдельный трек |

---

> Создано: 08.07.2026 · Обновлено: 08.07.2026 (синхронизация с целевой архитектурой)
