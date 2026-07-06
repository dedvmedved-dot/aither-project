# Статус реализации ТР — 07.07.2026

## ТР№1 — Ядро Aither (Token-as-a-Service)

### Реализовано

| # | Компонент | Статус | Проверка |
|---|---|---|---|
| 1 | K8s single-node + GPU Operator | ✅ | 18 подов Running |
| 2 | vLLM Qwen2.5-14B (TP=2) | ✅ | `/v1/models` → модель загружена |
| 3 | PostgreSQL 16 (Billing DB) | ✅ | `billing_accounts` (6 орг), `billing_ledger` |
| 4 | Redis 7 | ✅ | Running |
| 5 | API Gateway (Python) | ✅ | `/health`, `/v1/chat/completions`, `/v1/models` на :30900 |

### Не реализовано

| # | Компонент | Эпик | Описание |
|---|---|---|---|
| 1 | HMAC API-ключи | GW-01 | Формат `aither-<prefix>-<secret>`, constant-time compare |
| 2 | BillingGuard | GW-03 | Reserve ДО инференса, 402 при отказе |
| 3 | SSEProxy | GW-04 | Прокси SSE без буферизации, cancellation |
| 4 | TraceContext | GW-05 | W3C traceparent, сквозной request_id |
| 5 | Partial Settle | BILL-04 | Частичное списание при обрыве SSE |
| 6 | Reservation Reaper | BILL-05 | Автозакрытие зависших резервов |
| 7 | Reconciliation | BILL-06 | Сверка ledger vs account vs usage |
| 8 | Admin API (topup) | Admin | Пополнение баланса организации |
| 9 | Usage Collector | EPIC-03 | Подсчёт токенов, finalization |
| 10 | Rate Limiter | RL-01/02 | RPM/TPM/concurrency через Redis Lua |
| 11 | Admission Controller | ADM-01/02 | Очередь GPU, приоритеты тарифов |
| 12 | Model Registry | EPIC-00 | Управление версиями моделей |
| 13 | Security (RBAC/MFA/audit) | EPIC-07 | Роли, аудит, ротация ключей |
| 14 | Observability | EPIC-08 | Grafana, алерты, Jaeger, SLO |
| 15 | CI/CD + IaC | EPIC-09 | Terraform, Helm, GitLab CI |

### Gates

| Gate | Содержание | Статус |
|---|---|---|
| 0 | Совместимость стека | ⚠️ Пройден на Astra 1.8, не на RedOS |
| 1 | Model Fit | ⚠️ Qwen2.5-14B вместо целевой Qwen3-14B |
| 2 | Performance Benchmark | ❌ |
| 3 | Billing Integrity | ❌ |
| 4 | Security Sign-Off | ❌ |
| 5 | Pilot Readiness | ❌ |

---

## ТР№2 — Портал пользователя Aither

### Реализовано

| # | Компонент | Статус | Детали |
|---|---|---|---|
| 1 | nginx (SPA) | ✅ | VPS2:80, HTTP 200 |
| 2 | Portal BFF (Fastify) | ✅ | VPS2:3000, v0.5.0 |
| 3 | Portal DB (PostgreSQL) | ✅ | 6 таблиц, 7 орг, 10 польз., 18 ключей |
| 4 | Dev-аутентификация | ✅ | Вход по имени |
| 5 | CRUD организаций | ✅ | Создание, члены, роли (owner/billing_admin/developer/viewer) |
| 6 | CRUD API-ключей | ✅ | Создание, отзыв (нет ротации и блокировки) |
| 7 | Дашборд | ✅ | Баланс, usage, статус ядра |
| 8 | Чат (SSE streaming) | ✅ | История, share, выбор модели (бонус — не в ТР) |
| 9 | Делегирование BFF → Gateway | ⚠️ | JWT создаётся, но org_id не передаётся фронтендом |

### Не реализовано

| # | Компонент | Endpoint'ы / Таблицы | Описание |
|---|---|---|---|
| 1 | OAuth/OIDC | `/auth/*`, `/auth/refresh`, `/auth/logout` | GitHub/Google/ALD Pro, refresh-токены |
| 2 | Платежи | `POST /payments`, `GET /payments/{id}` | Пополнение через платёжный шлюз |
| 3 | Статистика | `GET /stats`, `GET /stats/export` | Графики по дням, экспорт CSV |
| 4 | Уведомления | `GET/PUT /settings/notifications` | Email/webhook при низком балансе |
| 5 | Webhook | `GET/POST/DELETE /settings/webhooks` | Подписка на события |
| 6 | Ротация ключей | `POST /keys/{id}/rotate` | Перевыпуск API-ключа |
| 7 | Блокировка ключей | `POST /keys/{id}/block` | Временная заморозка |
| 8 | Сессии (DB) | `sessions` | Refresh-токены, IP, user-agent |
| 9 | OAuth-линки (DB) | `oauth_links` | Привязка внешних аккаунтов |
| 10 | Уведомления (DB) | `notification_settings` | Порог баланса, email |
| 11 | Webhook (DB) | `webhook_endpoints`, `webhook_deliveries` | URL + лог доставок |
| 12 | Профиль (DB) | `user_preferences` | Язык, тема, часовой пояс |
| 13 | Приглашения (DB) | `invitations` | Инвайты в организацию |
| 14 | Аудит (DB) | `audit_events` | Лог действий пользователей |
| 15 | Кэш статистики (DB) | `cached_stats` | Агрегированные метрики |
| 16 | Observability | Grafana, логи, трейсинг | Эксплуатационная готовность |
| 17 | mTLS | BFF ↔ Core | Взаимный TLS |
| 18 | Rate Limiter (BFF) | На уровне BFF | Защита от перегрузки |
| 19 | Email (SMTP) | Отправка уведомлений | Нотификации |
| 20 | Runbooks | Инструкции дежурному | Эксплуатация |

---

## Сводная таблица

| Категория | ТР№1 | ТР№2 |
|---|---|---|
| **Реализовано** | 5 | 9 |
| **Не реализовано** | 15 | 20 |
| **Готовность к Production** | ~25% | ~30% |

### Приоритеты (ближайшие)

| Приоритет | Задача | ТР |
|---|---|---|
| 🔴 P0 | Починить org_id в делегировании (фронтенд) | ТР№2 |
| 🔴 P0 | Rate Limiter (Redis Lua) | ТР№1 |
| 🔴 P0 | Reservation Reaper | ТР№1 |
| 🟡 P1 | OAuth/OIDC | ТР№2 |
| 🟡 P1 | Платёжный кабинет | ТР№2 |
| 🟡 P1 | Usage Collector | ТР№1 |
| 🟢 P2 | Observability (Grafana, алерты) | ТР№1 |
| 🟢 P2 | Статистика + экспорт CSV | ТР№2 |
| 🟢 P2 | CI/CD + IaC | ТР№1 |
