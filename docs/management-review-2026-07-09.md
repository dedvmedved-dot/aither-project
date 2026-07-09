# Ответы на вопросы руководства — Aither Platform

**Дата:** 09.07.2026
**Версия платформы:** 0.5.0 (23/36 задач = 64%)

---

## 1. LDAP-аутентификация

**Текущее состояние:** OAuth (GitHub/Google/Яндекс) + email/password. OAuth реализован через Fastify-коллбэки в BFF, email/password — через bcrypt в PostgreSQL портала.

**Что нужно добавить:**

```
Пользователь → BFF /auth/ldap → FreeIPA/LDAP → группа/роль → JWT
```

**План реализации (3-4 дня):**
- Добавить провайдер LDAP в `portal/server.ts` (рядом с GitHub/Google/Яндекс)
- Конфигурация: `LDAP_URL`, `LDAP_BASE_DN`, `LDAP_BIND_DN`, `LDAP_BIND_PASSWORD` в `.env`
- Маппинг LDAP-групп → роли Aither (admin/user/viewer)
- Авто-создание portal_user при первом входе (как сейчас OAuth)
- Сохранение в `oauth_provider='ldap'`, `oauth_id=<DN>`

**Безопасность:** LDAP-трафик через LDAPS (порт 636) или StartTLS.

---

## 2. Чат — опциональный функционал

**Текущее состояние:** чат — один из центральных компонентов портала. Занимает 60% UI (sidebar, chat area, message list, SSE-стриминг).

**План (1 день):**
- Флажок `chat_enabled` в конфигурации (`config.yaml` → env `CHAT_ENABLED=true/false`)
- Если `false` — BFF скрывает `/chat`-роуты, UI не показывает вкладку чата
- SSE-стриминг и Chat-API отключаются полностью, освобождая ресурсы
- Чат остаётся в коде, но не инициализируется — можно включить в любой момент

---

## 3. Security Gateway — архитектура

### Текущее состояние

Security Gateway реализован только **на входе** (ingress). Проверяет входящие сообщения:
- Prompt injection (EN/RU паттерны: «игнорируй», «забудь», «ignore previous instructions»)
- Jailbreak-паттерны
- DLP: номера карт, СНИЛС, ИНН, паспорта

### Требования руководства: Security Gateway на входе + на выходе

```
                    ┌──────────────┐
Клиент ────────────▶│SECURITY GATE │ ─────▶ vLLM
                    │   INGRESS    │
                    └──────┬───────┘
                           │ audit log
                           ▼
                    ┌──────────────┐
                    │ SECURITY LOG │
                    │   STORAGE    │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │    SIEM      │
                    │ (syslog/CEF) │
                    └──────────────┘

vLLM ответ ────────▶│SECURITY GATE │ ─────▶ Клиент
                    │   EGRESS     │
                    └──────────────┘
```

### Security Gateway Egress (выходной контроль)

Проверяет ответ модели **перед отправкой пользователю** на:
- **ДСП-маркеры:** «Для служебного пользования», «ДСП», «Секретно», «Конфиденциально», грифы секретности
- **Персональные данные:** ФИО + паспорт, адреса, телефоны — даже если модель их «придумала»
- **Утечка системной информации:** internal IP, hostname, пути файловой системы, токены
- **Токсичность/нежелательный контент**

**Поведение при срабатывании:**
1. Сообщение пользователю: «Ответ содержит информацию ограниченного распространения и был отфильтрован»
2. Блокировка передачи
3. Запись в security-лог с полным контекстом (запрос + ответ + сработавшее правило)
4. Инкремент счётчика инцидентов для SIEM

### Хранилище security-логов

**Архитектура:**

```
Gateway Security Module
    │
    ├── PostgreSQL (structured) — таблица security_events:
    │   - id, timestamp, org_id, user_id, direction (ingress/egress)
    │   - rule_triggered, severity (low/medium/high/critical)
    │   - request_hash, response_hash, full_payload (JSONB)
    │   - action (block/pass/warn)
    │
    ├── Файловый лог (JSON Lines) — /var/log/aither/security.log
    │   - Ротация: logrotate, 30 дней хранения
    │   - Формат: одна строка JSON на событие
    │
    └── SIEM-коннектор (syslog/CEF) — RFC 5424 syslog
        - Приоритет: LOCAL0
        - Формат: CEF (Common Event Format)
        - Отправка: UDP/TCP на SIEM-коллектор
```

**Оценка объёма:** при 10K запросов/день, ~100MB логов/месяц. PostgreSQL — основное хранилище, JSON-файлы — резервное + для SIEM-агентов.

---

## 4. API-ключи через внешний Vault

### Текущее состояние

API-ключи генерируются в BFF: `crypto.randomBytes(24).toString('hex')` → SHA256-хеш → хранение в PostgreSQL (`portal_api_keys`). Префикс `ak-...` для идентификации.

### Требование: внешний корпоративный Vault

**Архитектура:**

```
BFF (create key)
    │
    ├── POST /api/v1/orgs/:orgId/api-keys
    │
    ▼
HashiCorp Vault (корпоративный)
    │
    ├── PKI secrets engine — выпуск ключа
    │   - TTL: 90 дней (ротация)
    │   - Политика: max_ttl=365d, require_cn=org_id
    │
    ├── Политики ИБ (транслируются):
    │   - Ключ привязан к организации
    │   - Max RPM/TPM согласно тарифу
    │   - Срок действия / авто-отзыв
    │   - Аудит использования
    │
    └── Возвращает: { api_key, fingerprint, expires_at }
```

**Как политики ИБ транслируются в платформу:**

| Политика ИБ (Vault) | Реализация в Gateway |
|---|---|
| `max_rpm=60` | Rate Limiter: sliding window 60 req/min |
| `max_tpm=100000` | Rate Limiter: sliding window 100K tokens/min |
| `expires_at=2026-10-07` | Gateway проверяет `expires_at` при каждом запросе |
| `models=['qwen2.5-14b']` | Каталог моделей: блокировка остальных |
| `ip_whitelist=['10.0.0.0/8']` | Gateway: проверка source IP |

**Поток при запросе:**
1. Клиент → BFF с `Authorization: Bearer ak-...`
2. BFF → Vault: `POST /v1/aither/validate { api_key }`
3. Vault возвращает: `{ org_id, policies: {...}, valid: true/false }`
4. BFF кэширует результат в Redis (TTL=60s) для производительности
5. При отзыве ключа в Vault → BFF инвалидирует кэш

---

## 5. RAG + LLM-Wiki (гибридная реализация)

### Текущее состояние

RAG реализован через ChromaDB + nomic-embed-text. LLM-Wiki — отдельно (`llm-wiki` навык).

### Требование: гибридная система

**Архитектура гибридного поиска:**

```
Запрос пользователя
        │
        ▼
┌───────────────────────────┐
│     ROUTER (классификатор)│
│   ┌─────┐  ┌───────────┐  │
│   │ RAG │  │ LLM-Wiki  │  │
│   └──┬──┘  └─────┬─────┘  │
│      │           │        │
│  embedding    keyword     │
│  similarity   search      │
│      │           │        │
│      └─────┬─────┘        │
│            ▼              │
│     FUSION (RRF/score)    │
│            │              │
└────────────┼──────────────┘
             ▼
     Контекст → LLM
```

**Где что используется:**

| Источник | Технология | Применение |
|---|---|---|
| **ChromaDB** (RAG) | Embedding similarity (nomic-embed-text) | Поиск по смыслу: документация, регламенты, FAQ |
| **LLM-Wiki** | Keyword + граф знаний (Markdown-файлы) | Структурированные знания: глоссарий, оргструктура, нормативка |
| **Гибридный fusion** | Reciprocal Rank Fusion (RRF) | Объединение результатов обоих поисков |

**План (3-4 дня):**
1. Развернуть LLM-Wiki как отдельный микросервис (рядом с ChromaDB в K8s)
2. API: `POST /search { query, top_k, mode: "rag"|"wiki"|"hybrid" }`
3. RRF-ранжирование: результаты обоих движков объединяются с весами
4. Кэширование частых запросов в Redis (TTL=1h)
5. UI: переключатель RAG / Wiki / Hybrid в интерфейсе

---

## 6. Профили организации

### Текущая реализация

- `GET /api/v1/orgs` — список организаций
- `GET /api/v1/orgs/:orgId` — детали: имя, участники, API-ключи
- Тариф (`billing_accounts.tier`) + лимиты (`subscription_tiers`)
- Billing dashboard: баланс, потребление, статистика по моделям

### Как расширяется под требования

**Профиль организации — это JSON-документ:**

```json
{
  "org_id": "uuid",
  "name": "Гринатом — отдел 42",
  "tier": "vip",
  "security_policy": {
    "dlp_enabled": true,
    "dsp_filter": true,
    "allowed_models": ["qwen2.5-14b", "qwen2.5-32b"],
    "max_tokens_per_request": 4096,
    "audit_level": "full"
  },
  "ldap_group": "cn=aither-vip,cn=groups,dc=greenatom,dc=ru",
  "api_keys": [...],
  "members": [...],
  "usage_limits": {
    "monthly_token_budget": 50000000,
    "alert_threshold": 0.8
  }
}
```

**Управление профилем:**
- **ИБ-политики** транслируются из Vault и применяются к профилю
- **LDAP-группа** определяет, кто может быть участником
- **SIEM-фид** — все события организации помечаются `org_id` для фильтрации
- **API Gateway management:** через `PATCH /api/v1/orgs/:orgId/profile`

---

## 7. Стратегия управления API Gateway

### Управление моделями

**Сейчас:** статический `catalog.yaml` → ConfigMap → Gateway.

**Целевая архитектура:**

```
Aither Admin UI / API
        │
        ▼
   catalog.yaml ──▶ Redis ──▶ Gateway (hot-reload, без рестарта)
        │
        ├── models: [{ name, endpoint, max_queue, weight }]
        ├── routing: [{ pattern → model, priority }]
        └── limits: [{ model: { max_concurrent, queue_size } }]
```

**Управление очередями:**

```yaml
# catalog.yaml
models:
  - id: qwen2.5-14b
    max_concurrent: 4
    queue_size: 50        # максимум запросов в очереди
    queue_timeout: 30s    # авто-отмена если дольше
    weight: 1.0           # приоритет при round-robin

  - id: qwen2.5-32b
    max_concurrent: 2
    queue_size: 20
    queue_timeout: 60s
    weight: 2.0
```

**API для управления (оператор):**
- `PATCH /api/v1/admin/catalog` — обновление параметров моделей
- `GET /api/v1/admin/queues` — текущие размеры очередей
- `POST /api/v1/admin/queues/drain` — сброс очереди для модели
- `GET /api/v1/admin/models/:id/stats` — статистика: avg_latency, queue_depth, errors

---

## 8. Мониторинг TTFT (Time To First Token)

**TTFT** — ключевая метрика пользовательского опыта. Измеряется от получения запроса Gateway до первого токена от vLLM.

**Реализация:**

```
Gateway получает запрос → timestamp T0
    │
    ▼
Rate Limit + Security (ingress) — < 5ms
    │
    ▼
Billing (reserve) — < 10ms
    │
    ▼
vLLM POST /v1/chat/completions → stream: true
    │
    ▼
Первый SSE-фрейм с токеном → timestamp T1
    │
TTFT = T1 - T0
```

**Метрики (Prometheus):**

| Метрика | Тип | Описание |
|---|---|---|
| `aither_ttft_seconds` | Histogram | Buckets: 0.1, 0.25, 0.5, 1, 2, 5, 10s |
| `aither_ttft_by_model` | Histogram | TTFT с разбивкой по model_id |
| `aither_ttft_by_tier` | Histogram | TTFT с разбивкой по тарифу (приоритет) |
| `aither_queue_wait_seconds` | Histogram | Время ожидания в очереди |

**Grafana-дашборд:**
- P50/P95/P99 TTFT по моделям (линейный график)
- Тепловая карта: час дня × день недели × TTFT
- Алерт: P95 TTFT > 5s → Telegram/SIEM
- Алерт: queue_depth > 80% от `max_queue` → автоскейлинг (Stage 6)

---

## Сводка: что нужно добавить в ROADMAP

| # | Задача | Приоритет | Оценка |
|---|---|---|---|
| 23a | **LDAP-аутентификация** | P0 (требование руководства) | 3 дня |
| 23b | **Чат опционально** | P2 | 1 день |
| 34 | **Security Gateway Egress** (ДСП-фильтр на выходе) | P0 | 3 дня |
| 35 | **SIEM-интеграция** (syslog CEF + security log storage) | P0 | 2 дня |
| 36 | **Vault-интеграция** (внешняя генерация API-ключей) | P0 | 4 дня |
| 37 | **LLM-Wiki + гибридный RAG** | P0 | 4 дня |
| 38 | **Профили организаций** (security policy per org) | P1 | 2 дня |
| 39 | **API Gateway management API** (очереди, модели) | P1 | 2 дня |
| 40 | **TTFT-мониторинг** | P1 | 1 день |

**Итого новые требования:** +22 дня (~4.5 недели). Все P0 — критические для руководства.

### Предлагаемый порядок (с учётом зависимостей):

```
Week 1:  #34 Security Egress + #35 SIEM (фундамент безопасности)
Week 2:  #36 Vault + #23a LDAP (корпоративная интеграция)
Week 3:  #37 LLM-Wiki + #38 Профили организаций
Week 4:  #39 Gateway management API + #23b Чат опционально
Week 5:  #40 TTFT-мониторинг + документация
```

---

## Текущая архитектура (для справки)

```
                    VPS1:10443 (nginx failover)
                    ┌───────┴───────┐
                    ▼               ▼
          VPS2:80 (primary)   VPS3:80 (backup)
          BFF :3000           BFF :3000
          │                   │ (pg-tunnel→VPS1→K8s)
          └───────┬───────────┘
                  │
          K8s Gateway :30900
          ┌───────┼───────┐
          ▼       ▼       ▼
     Security  Billing  Routing
          │       │       │
          └───────┼───────┘
                  ▼
          vLLM (14B / 32B)
```

**Что меняется в целевой архитектуре:**

```
Добавляются:
  - LDAP (внешний) ← BFF
  - Vault (внешний) ← BFF
  - Security Egress ← Gateway (после vLLM)
  - SIEM ← Gateway (syslog)
  - LLM-Wiki (K8s pod) ← рядом с ChromaDB
  - TTFT-метрики ← Gateway → Prometheus → Grafana
  - Admin API ← Gateway (управление очередями/моделями)
```
