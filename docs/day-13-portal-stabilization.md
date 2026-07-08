# День 13-14: Стабилизация портала и чата (07-08.07.2026)

## TL;DR

| Что сделано | Статус |
|---|---|
| OAuth (Яндекс/Google/GitHub) — восстановлены после потери env vars | ✅ |
| Чат — исправлен 500 (req.user → p.user_id) | ✅ |
| Баланс — отображается в UI (1 000 000 токенов) | ✅ |
| Dev-вход удалён с лендинга | ✅ |
| Подсветка кода — исправлены hljs-артефакты | ✅ |
| Кнопка копирования кода — добавлена | ✅ |
| org_id в чатах — таблица + BFF + фронтенд | ✅ |
| Обе модели (14B + 32B) работают через чат | ✅ |

---

## 1. Архитектура после исправлений

![Архитектура Aither — день 13](diagrams/day13-architecture.svg)

**Текущий поток запроса (чат):**

```
Браузер → VPS2:80 (Nginx) → VPS2:3000 (BFF)
  ├─ OAuth: Яндекс / Google / GitHub → JWT-токен
  ├─ Chat API: /api/v1/chats → /api/v1/chats/{id}/messages
  └─ Billing: /api/v1/billing?org_id=...

BFF → Gateway K8s :30900 (Delegation JWT RS256)
  ├─ Security check (prompt injection + DLP)
  ├─ Billing (reserve → inference → settle)
  └─ vLLM:
       ├─ 14B → n8:30900 (Qwen2.5-14B-Instruct)
       └─ 32B → n7:30901 (Qwen2.5-32B-Instruct)
```

---

## 2. Исправленные баги

![Карта исправлений](diagrams/day13-fixes.svg)

### 2.1. OAuth — переменные окружения теряются при перезапуске

**Симптом:** После перезапуска BFF все три провайдера возвращают «not configured».

**Причина:** Процесс `node dist/server.js` запускается через `nohup`, но без загрузки `.env`.

**Исправление:**

```bash
cd /root/aither-project/portal
set -a && . ./.env && set +a
nohup node dist/server.js > /tmp/bff.log 2>&1 &
```

**Результат:** Все три OAuth возвращают `302 Redirect` на провайдера.

---

### 2.2. Чат — 500 ошибка при отправке сообщения

**Симптом:**

```json
{"statusCode":500,"error":"Internal Server Error",
 "message":"Cannot read properties of undefined (reading 'user_id')"}
```

**Причина:** В `dist/server.js` строка 738 использовала `req.user.user_id`, но `req.user` нигде не устанавливается. Функция `auth()` возвращает декодированный JWT-пейлоад в переменную `p`, а не в `req.user`.

**Исправление:**

```diff
- user_id: req.user.user_id
+ user_id: p.user_id
```

---

### 2.3. Чат — insufficient_balance / org_id не сохранялся

**Симптом:** После исправления `req.user` ошибка сменилась на:

```
insufficient_balance: invalid input syntax for type uuid: "unknown"
```

**Причина:** Таблица `chats` не имела колонки `org_id`. При создании чата `org_id` не передавался и не сохранялся. Delegation-токен содержал `org_id: null` → Gateway пытался найти `billing_account` с org_id='unknown'.

**Исправление (3 уровня):**

1. **БД:** `ALTER TABLE chats ADD COLUMN org_id uuid REFERENCES portal_organizations(org_id)`
2. **BFF:** INSERT принимает и сохраняет `org_id`, delegation-токен использует `chat.org_id || org_id`
3. **Фронтенд:** `createChat()` передаёт `org_id: state.chatOrgId`

---

### 2.4. Баланс всегда 0 в UI

**Симптом:** В локальной БД 1 000 000 токенов, но чат показывает «Баланс: 0 токенов».

**Причина:** API возвращает `{total_tokens: 1000000}`, а фронтенд читал `data.balance`.

**Исправление:**

```diff
- ${formatNumber(data.balance || 0)}
+ ${formatNumber(data.total_tokens || 0)}
```

---

### 2.5. Dev-вход на лендинге

**Симптом:** Кнопка «Войти (dev)» с полем ввода имени оставалась на странице входа.

**Исправление:** Удалён HTML-блок с `<input id="login-name">` и `<button onclick="doLogin()">`.

---

### 2.6. hljs-артефакты в блоках кода

**Симптом:** В коде появляются строки вида `"hljs-keyword">if` — обрывки HTML-спанов подсветки.

**Причина:** Функция `highlightCode()` выполняла замены в порядке: keywords → strings. String-регекс `/([\"'`])(?:(?!\1|\\).|\\.)*\1/g` матчил `"hljs-keyword"` внутри уже созданного `<span class="hljs-keyword">` и оборачивал его повторно:

```html
<!-- Было (правильно): -->
<span class="hljs-keyword">if</span>

<!-- Стало (битый HTML): -->
<span class=<span class="hljs-string">"hljs-keyword"</span>>if</span>
```

**Исправление:** Изменён порядок замен — strings ПЕРЕД keywords:

```
1. Strings → 2. Triple-strings → 3. Comments → 4. Numbers → 5. Keywords
```

Также `highlightCode` теперь не запускается во время стриминга (`if (!state.chatStreaming)`).

---

### 2.7. Кнопка копирования кода

Добавлена кнопка «📋 Копировать» над каждым блоком кода. Использует `navigator.clipboard.writeText()` с fallback на `document.execCommand('copy')` для HTTP.

---

## 3. Текущее состояние инфраструктуры

| Компонент | Узел | Статус |
|---|---|---|
| Nginx (портал) | VPS2:80 | ✅ static + proxy |
| BFF (Fastify) | VPS2:3000 | ✅ OAuth + Chat API + Billing |
| PostgreSQL (portal) | VPS2 Docker | ✅ users, orgs, chats, billing |
| Gateway (Python) | n8 K8s:30900 | ✅ JWT + Security + Billing |
| PostgreSQL (K8s) | n8 K8s | ✅ aither |
| Redis | n8 K8s | ✅ rate limit |
| vLLM 14B | n8:30900 | ✅ Qwen2.5-14B-Instruct |
| vLLM 32B | n7:30901 | ✅ Qwen2.5-32B-Instruct |
| ChromaDB | n7:8000 | ✅ RAG-документы |

---

## 4. Место в дорожной карте

| Этап | Задач | Выполнено |
|---|---|---|
| 1. MVP | 7 | 7 ✅ |
| 2. Биллинг + каталог | 4 | 4 ✅ |
| 3. Observability + продакшен | 5 | 3 (60%) |
| 4. RAG + кастомизация | 4 | 1 (ChromaDB) |
| 5. Продакшен-класс | 6 | 0 |
| 6. Эксплуатация | 6 | 0 |

**Готовность:** ~50% (MVP + биллинг + базовый Observability + OAuth + чат)

---

## 5. План на завтра (09.07.2026)

| # | Задача | Приоритет | Почему |
|---|---|---|---|
| 1 | **ЮKassa боевой режим** | 🔴 Критично | Демонстрация без реальных платежей несерьёзна |
| 2 | **Проверка портала специалистами** | 🔴 Критично | Фидбек от реальных пользователей |
| 3 | **RAG — индексация документов** | 🟡 Средний | Внутренняя документация, техподдержка |
| 4 | **Каталог моделей в UI** | 🟡 Средний | Выбор модели из каталога вместо хардкода |
| 5 | **Parsec** | 🟢 Низкий | Требование госсектора, но не блокирует демо |

---

## 6. Коммиты

| SHA | Описание |
|---|---|
| _будет_ | `docs: день 13-14 — стабилизация портала и чата` |
| — | `fix: req.user → p.user_id в chat messages` |
| — | `fix: org_id в таблице chats + BFF + фронтенд` |
| — | `fix: data.balance → data.total_tokens в UI` |
| — | `fix: удалён dev-вход с лендинга` |
| — | `fix: hljs-артефакты — strings перед keywords` |
| — | `feat: кнопка копирования кода в чате` |

---

## 7. Ключевые выводы

1. **Переменные окружения** — критическая точка отказа. Нужен systemd-сервис для BFF с `EnvironmentFile`.
2. **Тестирование чата выявило каскад багов** — `req.user` → `org_id` → `balance` — исправление одного вскрывало следующий.
3. **Фронтенд-баги маскируются под backend-ошибки** — `data.balance` vs `data.total_tokens` выглядело как «баланс не сохранился».
4. **Regex-порядок в highlightCode** — классический баг: обработка HTML строковым regex после того как в текст добавлены HTML-теги.
5. **Портал готов к демонстрации** — OAuth, чат с 2 моделями, биллинг, копирование кода — всё работает.
