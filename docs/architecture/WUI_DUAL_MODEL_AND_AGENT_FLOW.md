# WUI Dual Model и Agent Flow — архитектура переходов

**Версия:** 1.0 · **Дата:** 26 июля 2026 · **Статус:** Accepted
**Затронутые компоненты:** Web UI (SPA), BFF v0.5.0 (Fastify), Key Service (Redis), Model Gateway, vLLM (14B, 32B)
**Связанные ADR:** [ADR-CB-WEBUI-001](./ADR-CB-WEBUI-001.md)

---

## 0. Общая схема

```
                            ПОТОК А (Web UI — Браузер)
                            ═══════════════════════════

  Browser ──→ Web UI (SPA) ──→ BFF/API ──→ Auth ──→ AuthZ ──→ Key Service ──→ Model Gateway ──→ MODEL_A (qwen-14b) / MODEL_B (qwen-32b-base)
   🌐           Vanilla JS       Fastify    Redis    Scopes       Redis           Gateway           vLLM-поды K8s
                                 v0.5.0     сессий   (модели)    (токены)        + catalog

                            ПОТОК Б (AI Agent — API)
                            ═══════════════════════

  AI Agent ──→ Internet / Test Zone API ──→ API Key Validation ──→ Model Scope Validation ──→ Model Gateway ──→ MODEL_A / MODEL_B
   🤖           HTTPS :443 / HTTP :30080       hmac-токен              scope ∈ token            catalog.yaml        vLLM-поды
```

---

## 1. Поток А: Браузер → Web UI → Модели

### 1.1. Маршрут целиком

```
Browser
  │ HTTPS (TLS 1.2+)
  ▼
VPS1 nginx (:443, TLS-termination)
  │ HTTP (WireGuard, сеть 10.129.13.0/24)
  ▼
VPS2 nginx (:80, Docker)
  │ HTTP (localhost)
  ▼
BFF Fastify (:3000)
  │ HTTP (внутренняя сеть K8s 10.129.13.0/24)
  ▼
Model Gateway :30900 (K8s NodePort)
  │ HTTP (K8s Service DNS)
  ▼
vLLM 14B (:8000, K8s pod)  /  vLLM 32B (:8000, K8s pod)
```

Маршрутизация по моделям:
- **qwen-14b** (id: `14b`, type: `chat`) → `C14` = `http://vllm-14b-instruct.aither-inference.svc:8000`
- **qwen-32b-base** (id: `32b`, type: `completion`) → `G32` = `http://nginx-gateway-32b.aither-inference.svc:8000`

---

### 1.2. Переходы (по шагам)

#### Переход #1: Browser → Web UI (SPA)

| Параметр | Значение |
|---|---|
| **Протокол** | HTTPS (TLS 1.2+) через VPS1 nginx |
| **Аутентификация** | Отсутствует (SPA — публичная статика) |
| **Авторизация** | Отсутствует на уровне статики |
| **Таймаут** | Отсутствует (статический контент) |
| **Логирование** | nginx access.log на VPS1 и VPS2 |
| **Граница секретов** | Нет. HTML/JS/CSS — публичный контент, секретов не содержит |
| **Режим отказа** | HTTP 502 Bad Gateway — если VPS2 недоступен. HTTP 504 Gateway Timeout — если VPS2 не отвечает за 60 с. Браузер показывает белый экран или ошибку сети |

#### Переход #2: Web UI (SPA) → BFF/API

| Параметр | Значение |
|---|---|
| **Протокол** | HTTPS (браузер → VPS1 nginx) → HTTP (VPS1 → VPS2 nginx → BFF :3000). SPA отправляет `fetch()` к `/api/*` |
| **Аутентификация** | Cookie `session_id` (HttpOnly, SameSite=Strict) ИЛИ заголовок `Authorization: Bearer <token>` |
| **Авторизация** | BFF middleware `amw()` проверяет каждый запрос: сессионная cookie (Redis `aither-auth:session:<sid>`) или Bearer-токен (Redis `aither-auth:token:<hmac>`). Публичные эндпоинты (`/health`, `/api/v1/auth/*`) — без авторизации |
| **Таймаут** | BFF → backend: 300 с (`BFF_REQUEST_TIMEOUT_SECONDS`). Браузерный fetch: без явного таймаута (зависит от браузера, обычно 300 с) |
| **Логирование** | BFF: Fastify logger (pino). Все запросы: method, url, statusCode, responseTime. Auth-ошибки: уровень WARN |
| **Граница секретов** | `JWT_SECRET`, `SESSION_SECRET`, `AUTH_TOKEN_HASH_SECRET` — в env BFF. Cookie `session_id` — HttpOnly (недоступен JS). Браузер не видит секретов |
| **Режим отказа** | HTTP 401 — сессия истекла / токен недействителен (перенаправление на логин). HTTP 403 — недостаточно прав (scope). HTTP 429 — rate limit (60 с окно, 10 запросов). HTTP 503 — Redis недоступен |

#### Переход #3: BFF → Auth (аутентификация)

| Параметр | Значение |
|---|---|
| **Протокол** | Внутренний вызов функции `auth_req()` в BFF (in-process). Внешний: HTTP POST к `aither-identity:8000/v1/identity/auth` для non-admin пользователей |
| **Аутентификация** | Admin: `hmac.compare_digest` логина и SHA-256 хеша пароля с `ADMIN_PASSWORD_HASH` из env. Non-admin: делегирование в Identity Service |
| **Авторизация** | Admin → роль `administrator`. Non-admin → роль из ответа Identity Service |
| **Таймаут** | Identity Service: 10 с (httpx.AsyncClient). BFF in-process: мгновенно |
| **Логирование** | BFF: `log.info("Login via identity: %s role=%s", ...)`. Ошибки: `log.warning("Identity login failed for %s: %s", ...)` |
| **Граница секретов** | `ADMIN_USERNAME`, `ADMIN_PASSWORD_HASH` — env BFF. Identity Service URL — env. Пароли не логируются |
| **Режим отказа** | Identity Service недоступен: HTTP 401. Неверные учётные данные: HTTP 401. Redis недоступен: HTTP 503 |

#### Переход #4: BFF → AuthZ (авторизация / проверка прав)

| Параметр | Значение |
|---|---|
| **Протокол** | In-process в BFF: функция `ck(req, required_scope)` |
| **Аутентификация** | Уже выполнена на шаге #3. Контекст: `req.state.auth_scope` — `"admin"` (строка) или `["model:14b:chat", ...]` (список) |
| **Авторизация** | Admin: полный доступ. Пользователь: проверка `required_scope in scopes`. Scopes моделей: `model:14b:chat`, `model:32b:chat-adapter`, `model:32b:completion` |
| **Таймаут** | In-process — мгновенно |
| **Логирование** | BFF: ошибки авторизации → HTTP 403 в ответе (не отдельный лог) |
| **Граница секретов** | Список scope'ов в метаданных токена (Redis). Сами scope-строки — не секреты |
| **Режим отказа** | Нет нужного scope → HTTP 403. Admin всегда проходит |

#### Переход #5: BFF → Key Service (управление API-ключами)

| Параметр | Значение |
|---|---|
| **Протокол** | Redis (TCP :6379). Ключ: `hmac.new(AUTH_TOKEN_HASH_SECRET, raw_token, sha256)` |
| **Аутентификация** | Ключ хранится как HMAC-SHA256 от `raw_token` с секретом `AUTH_TOKEN_HASH_SECRET`. Redis: ключ `aither-auth:token:<hmac>` → JSON метаданные |
| **Авторизация** | Создание токенов: только admin. Просмотр: admin видит все, пользователь — только свои (`owner == username`). Отзыв: admin или владелец токена |
| **Таймаут** | Redis — мгновенно (в процессе запроса). TTL сессии: 86400 с (24 ч) |
| **Логирование** | BFF логирует создание/отзыв в рамках HTTP-запроса (Fastify logger) |
| **Граница секретов** | `AUTH_TOKEN_HASH_SECRET` — env BFF. Raw-токен (формат `athr_...`) — возвращается клиенту **один раз** при создании. Хранится в Redis только HMAC. Полный токен восстановить невозможно |
| **Режим отказа** | Redis недоступен → HTTP 503. Токен не найден → HTTP 404. Попытка отозвать чужой токен → HTTP 403 |

#### Переход #6: BFF → Model Gateway → MODEL_A / MODEL_B

| Параметр | Значение |
|---|---|
| **Протокол** | HTTP/1.1 + SSE (Server-Sent Events для streaming). BFF → Gateway: `POST /v1/chat/completions` (14B) или `POST /v1/completions` (32B) |
| **Аутентификация** | BFF подставляет upstream auth token: `Authorization: Bearer <BFF_14B_UPSTREAM_AUTH_TOKEN>` или `<BFF_32B_GATEWAY_AUTH_TOKEN>` |
| **Авторизация** | Scope уже проверен на шаге #4. Gateway не делает авторизации пользователя — он доверяет BFF |
| **Таймаут** | 300 с (`BFF_REQUEST_TIMEOUT_SECONDS`). Gateway → vLLM: без явного таймаута (зависит от `max_tokens`) |
| **Логирование** | BFF: Fastify logger (request/response). Gateway: access-лог, catalog-лог. vLLM: usage-метаданные |
| **Граница секретов** | `BFF_14B_UPSTREAM_AUTH_TOKEN`, `BFF_32B_GATEWAY_AUTH_TOKEN` — env BFF. Не передаются клиенту |
| **Режим отказа** | Gateway недоступен → HTTP 502 (core_unreachable). Модель не найдена → HTTP 400 (unknown model). vLLM OOM → HTTP 500. Таймаут → HTTP 504. Rate limit Redis → fail-open (пропускает запрос с WARNING) |

---

### 1.3. Сводная таблица переходов (Поток А)

| # | Переход | Протокол | Аутентификация | Авторизация | Таймаут | Секреты |
|---|---|---|---|---|---|---|
| 1 | Browser → Web UI | HTTPS → HTTP | Нет | Нет | — | Нет |
| 2 | Web UI → BFF | HTTPS → HTTP | Cookie / Bearer | Scope (admin/user/scopes) | 300 с | JWT_SECRET, SESSION_SECRET (env) |
| 3 | BFF → Auth | In-process / HTTP | login+password | Admin vs Identity delegate | 10 с | ADMIN_PASSWORD_HASH (env) |
| 4 | BFF → AuthZ | In-process | Контекст `auth_scope` | Scope ∈ required | 0 с | Нет |
| 5 | BFF → Key Service | Redis TCP | HMAC-SHA256 | Admin / owner | 0 с | AUTH_TOKEN_HASH_SECRET (env) |
| 6 | BFF → Gateway → vLLM | HTTP+SSE | Upstream auth token | Доверие BFF | 300 с | BFF_*_UPSTREAM_AUTH_TOKEN (env) |

---

## 2. Поток Б: AI Agent → Internet/Test Zone API → Модели

### 2.1. Маршрут целиком

```
AI Agent (CLI / SDK / Python)
  │ HTTPS :443 (Internet) / HTTP :30080 (Test Zone)
  ▼
VPS1 nginx :443 / K8s NodePort :30080
  │ HTTP (WireGuard / внутренняя сеть)
  ▼
BFF Fastify (:3000, через VPS2 nginx)
  │ проверка API-ключа (Redis HMAC)
  │ проверка scope (model:14b:chat / model:32b:completion)
  │ rate limiting (Redis Lua-подобная логика)
  ▼
Model Gateway :30900
  │ catalog.yaml → resolve(model_name) → backend_url
  ▼
vLLM 14B / vLLM 32B
```

### 2.2. Переходы (по шагам)

#### Переход #7: AI Agent → Internet API / Test Zone API

| Параметр | Значение |
|---|---|
| **Протокол** | Internet: HTTPS (TLS 1.2+, Let's Encrypt, домен `fb1.spb.ru:443`). Test Zone: HTTP (`10.129.13.78:30080`) |
| **Аутентификация** | Заголовок `Authorization: Bearer athr_<prefix>_<secret>` |
| **Авторизация** | На этом шаге — нет. Только транспортный уровень |
| **Таймаут** | Клиент (агент) задаёт самостоятельно. nginx: 60 с proxy_read_timeout |
| **Логирование** | VPS1 nginx: access.log. VPS2 nginx: access.log |
| **Граница секретов** | API-ключ (`athr_...`) передаётся в заголовке. При HTTPS — шифруется. При HTTP (Test Zone) — открытый текст. **Никогда не передавать ключ через HTTP в недоверенной сети** |
| **Режим отказа** | Сеть недоступна → Connection Refused. Сертификат недействителен → TLS Error (только Internet). nginx не отвечает → HTTP 502/504 |

#### Переход #8: API → API Key Validation

| Параметр | Значение |
|---|---|
| **Протокол** | BFF in-process: извлечение `Bearer` из заголовка, вычисление `hmac.new(AUTH_TOKEN_HASH_SECRET, raw_token, sha256)`, Redis `GET aither-auth:token:<hmac>` |
| **Аутентификация** | HMAC-SHA256 от raw-токена. Сравнение с хранимым ключом. Поиск в сете `aither-auth:token:all` |
| **Авторизация** | Проверка `meta.revoked == False`. Обновление `last_used_at` в Redis |
| **Таймаут** | Redis — мгновенно. Отказ Redis → fail-open (пропускает запрос с WARNING) |
| **Логирование** | BFF: при ошибке — HTTP 401 "Token not found or revoked" |
| **Граница секретов** | `AUTH_TOKEN_HASH_SECRET` — env BFF. Raw-токен не хранится в открытом виде. HMAC необратим без секрета |
| **Режим отказа** | Токен не найден в Redis → HTTP 401. Токен `revoked: true` → HTTP 401. Redis недоступен → fail-open (пропускает, WARNING в лог) |

#### Переход #9: API Key Validation → Model Scope Validation

| Параметр | Значение |
|---|---|
| **Протокол** | In-process: BFF `ck(req, required_scope)` |
| **Аутентификация** | Уже выполнена на шаге #8 |
| **Авторизация** | Проверка: `required_scope ∈ meta.scopes`. Для чата: `model:14b:chat`. Для 32B-чата: `model:32b:chat-adapter`. Для completion: `model:32b:completion` |
| **Таймаут** | In-process — мгновенно |
| **Логирование** | При отказе → HTTP 403 в ответе |
| **Граница секретов** | Scope-строки в метаданных токена — не секреты, но определяют поверхность атаки (какие модели доступны) |
| **Режим отказа** | Scope отсутствует → HTTP 403. 14B запрошен как completion → HTTP 422 (Unprocessable Entity) |

#### Переход #10: BFF → Model Gateway → Модели

| Параметр | Значение |
|---|---|
| **Протокол** | HTTP/1.1 + SSE. BFF проксирует запрос: `POST /v1/chat/completions` (14B) или `POST /v1/completions` (32B) |
| **Аутентификация** | Upstream auth token: `Authorization: Bearer <BFF_14B_UPSTREAM_AUTH_TOKEN>` (14B) или `<BFF_32B_GATEWAY_AUTH_TOKEN>` (32B). Gateway проверяет токен |
| **Авторизация** | Gateway: catalog.yaml — resolve модели. Если модель не в каталоге → HTTP 400 "unknown_model" |
| **Таймаут** | 300 с. Gateway health-check кэш: 30 с |
| **Логирование** | BFF: Fastify logger. Gateway: model name, backend URL, токены (prompt/completion) |
| **Граница секретов** | Upstream токены в env BFF. vLLM не требует клиентской аутентификации (внутренний трафик) |
| **Режим отказа** | Gateway недоступен → HTTP 502. Модель не найдена в catalog.yaml → HTTP 400. vLLM-под не health → catalog health_check кэш 30 с → HTTP 502. GPU OOM → HTTP 500. Стрим оборвался → HTTP 500 / частичный ответ |

---

### 2.3. Сводная таблица переходов (Поток Б)

| # | Переход | Протокол | Аутентификация | Авторизация | Таймаут | Секреты |
|---|---|---|---|---|---|---|
| 7 | Agent → API | HTTPS / HTTP | Bearer athr_... | Нет | 60 с (nginx) | API-ключ в заголовке |
| 8 | API → Key Validation | Redis TCP | HMAC-SHA256 | revoked check | 0 с | AUTH_TOKEN_HASH_SECRET |
| 9 | Key → Scope Validation | In-process | Контекст meta.scopes | Scope ∈ required | 0 с | Нет |
| 10 | BFF → Gateway → vLLM | HTTP+SSE | Upstream auth token | catalog.yaml resolve | 300 с | BFF_*_UPSTREAM_AUTH_TOKEN |

---

## 3. Модели и их параметры

| Параметр | MODEL_A | MODEL_B |
|---|---|---|
| **API ID** | `14b` | `32b` |
| **Полное имя** | `qwen-14b` | `qwen-32b-base` |
| **Тип** | `chat` | `completion` |
| **vLLM-под** | `vllm-14b-instruct` (нода n8) | `vllm-32b` (нода n7) |
| **Бэкенд URL** | `http://vllm-14b-instruct.aither-inference.svc:8000` | `http://nginx-gateway-32b.aither-inference.svc:8000` |
| **Эндпоинт** | `/v1/chat/completions` | `/v1/completions` |
| **Контекстное окно** | 4096 токенов | 8192 токенов |
| **GPU** | 2× RTX 6000 Ada (n8) | 2× RTX 6000 Ada (n7) |
| **VRAM** | ~28 GB | ~40 GB (GPTQ) |
| **Scope для доступа** | `model:14b:chat` | `model:32b:completion`, `model:32b:chat-adapter` |
| **Режим отказа** | 14B-чат — основной. При недоступности → HTTP 502 | 32B — для сложных задач. При недоступности → HTTP 502 |

---

## 4. Rate Limiting

| Параметр | Значение |
|---|---|
| **Механизм** | Redis INCR с окном 60 с |
| **Ключ** | `rl:sha256(authorization_header):<window>` или `rl:ip:<ip>:<window>` |
| **Лимит** | 10 запросов / 60 с (на ключ/IP) |
| **Redis недоступен** | Fail-open: пропускает запрос, пишет WARNING в лог |
| **Конфигурация** | `RATE_LIMIT_ENABLED`, `RATE_LIMIT_WINDOW_SECONDS`, `RATE_LIMIT_MAX_REQUESTS` |

---

## 5. Границы секретов (полная карта)

| Секрет | Где хранится | Кто имеет доступ | Формат | Ротация |
|---|---|---|---|---|
| `JWT_SECRET` | env BFF | BFF (Fastify) | строка | Ручная, через env |
| `SESSION_SECRET` | env BFF | BFF | строка | Ручная, через env |
| `AUTH_TOKEN_HASH_SECRET` | env BFF | BFF | строка | Ручная, через env. **Смена инвалидирует все токены** |
| `ADMIN_PASSWORD_HASH` | env BFF | BFF | SHA-256 | Ручная, через env |
| `ADMIN_USERNAME` | env BFF | BFF | строка | Ручная, через env |
| `BFF_14B_UPSTREAM_AUTH_TOKEN` | env BFF | BFF → Gateway | Bearer-токен | Ручная, синхронно с Gateway |
| `BFF_32B_GATEWAY_AUTH_TOKEN` | env BFF | BFF → Gateway | Bearer-токен | Ручная, синхронно с Gateway |
| API-ключ (raw) | Клиент (env / менеджер паролей) | Только клиент | `athr_<prefix>_<secret>` | Отзыв + создание нового |
| API-ключ (HMAC) | Redis `aither-auth:token:<hmac>` | BFF | SHA-256 HMAC | Автоматически при смене `AUTH_TOKEN_HASH_SECRET` |
| Cookie `session_id` | Браузер (HttpOnly) | BFF → Redis | UUID | TTL 24 ч, авто-очистка Redis |

---

## 6. Режимы отказов — сводная матрица

| Компонент | Тип отказа | HTTP-код | Поведение |
|---|---|---|---|
| VPS1 nginx (Internet) | Недоступен | Connection Refused / 502 | Браузер: ошибка сети |
| VPS2 nginx | Недоступен | 502 | VPS1 возвращает 502 |
| BFF | Не запущен | 502 | nginx возвращает 502 |
| Redis | Недоступен | 503 (для логина/токенов); fail-open для RL | Логин невозможен; запросы пропускаются |
| Identity Service | Недоступен | 401 | Только admin может войти |
| API-ключ | Не найден / отозван | 401 | "Token not found or revoked" |
| Scope | Отсутствует | 403 | "Forbidden" |
| Rate Limit | Превышен | 429 | Retry-After: 60 с |
| Gateway | Недоступен | 502 | "core_unreachable" |
| Модель в catalog.yaml | Не найдена | 400 | "unknown_model" с списком доступных |
| vLLM-под | Недоступен | 502 | Health-check кэш 30 с |
| GPU OOM | Ошибка инференса | 500 | vLLM возвращает 500 |
| BFF upstream token | Неверный | 401 / 403 | Gateway отклоняет запрос |

---

## 7. Диаграмма последовательности (упрощённая)

### 7.1. Поток А: Браузерный чат

```
Browser         VPS1 nginx      VPS2 nginx      BFF:3000        Redis           Gateway:30900   vLLM:8000
  │                │               │               │               │               │               │
  │──GET / ───────→│               │               │               │               │               │
  │←──SPA (HTML)───│               │               │               │               │               │
  │                │               │               │               │               │               │
  │──POST /api/v1/auth/login──────→│──────────────→│               │               │               │
  │                │               │               │──compare_digest│              │               │
  │                │               │               │──SET session──→│               │               │
  │←──Set-Cookie: session_id──────────────────────│               │               │               │
  │                │               │               │               │               │               │
  │──POST /api/v1/chat (Cookie)───→│──────────────→│               │               │               │
  │                │               │               │──GET session─→│               │               │
  │                │               │               │←──role=admin──│               │               │
  │                │               │               │──ck(scope)────│               │               │
  │                │               │               │──INCR rl key─→│               │               │
  │                │               │               │               │               │               │
  │                │               │               │──POST /v1/chat/completions─────→│               │
  │                │               │               │               │               │──POST /v1/chat/completions──→│
  │                │               │               │               │               │               │──generate──│
  │                │               │               │               │               │←──SSE chunks│               │
  │                │               │               │←──SSE chunks──────────────────│               │
  │←──SSE stream──────────────────────────────────│               │               │               │
```

### 7.2. Поток Б: AI Agent (API-ключ)

```
Agent           VPS1/VPS2       BFF:3000        Redis           Gateway:30900   vLLM:8000
  │                │               │               │               │               │
  │──POST /v1/chat/completions────→│               │               │               │
  │  Authorization: Bearer athr_…  │               │               │               │
  │                │               │──hmac(token)──│               │               │
  │                │               │──GET token───→│               │               │
  │                │               │←──meta (scopes, revoked)──────│               │
  │                │               │──ck(scope)────│               │               │
  │                │               │──INCR rl─────→│               │               │
  │                │               │               │               │               │
  │                │               │──POST /v1/chat/completions─────→│               │
  │                │               │  Authorization: Bearer <upstream_token>        │               │
  │                │               │               │               │──POST─────────→│
  │                │               │               │               │←──SSE chunks──│
  │                │               │←──SSE chunks──────────────────│               │
  │←──SSE stream──────────────────│               │               │               │
```

---

## 8. Примечания

1. **BFF v0.5.0** (Fastify, порт 3000) заменил Python FastAPI BFF, который ранее работал на порту 8000. Кодовая база: TypeScript, JWT-сессии (HS256), делегирование через Redis.

2. **Доверенный upstream**: BFF использует предварительно сконфигурированные upstream-токены для доступа к Gateway. Gateway не проверяет конечного пользователя — это задача BFF.

3. **Fail-open для Rate Limiter**: при недоступности Redis запросы пропускаются. Это компромисс между доступностью и защитой от перегрузки.

4. **Test Zone (HTTP)**: данные передаются открытым текстом. API-ключи при использовании Test Zone не защищены транспортным шифрованием. Рекомендуется только для внутренней доверенной сети.

5. **Один API-ключ — две зоны**: токены работают и через Internet (HTTPS :443), и через Test Zone (HTTP :30080). Зона прозрачна для BFF.

6. **Модель 32B через chat-адаптер**: эндпоинт `/api/v1/chat` преобразует messages в completion-формат через функцию `cvt()`: `<|user|>\n...\n<|assistant|>\n`. Scope: `model:32b:chat-adapter`.

7. **Redis как Key Service**: все API-ключи хранятся в Redis (in-memory). При потере Redis все токены теряются и требуют пересоздания.

---

## 9. Связанные документы

- [ADR-CB-WEBUI-001: Архитектура Web UI с двухзонным доступом](./ADR-CB-WEBUI-001.md)
- [Руководство по API-ключам](../user-package/14_API_KEY_USER_GUIDE.md)
- [Подключение AI-агентов](../user-package/16_AI_AGENT_CONNECTION_PRIMER.md)
- [Двухзонный доступ](../user-package/15_DUAL_ZONE_ACCESS_GUIDE.md)
- [Каталог моделей](../model-catalog.md)
- [Архитектура платформы](../../offline-deploy/docs/01-architecture.md)
- [Исходный код BFF](../../deploy/bff-app-v0.5.0.py)
- [Исходный код BFF (TypeScript)](../../portal/bff/src/server.ts)
