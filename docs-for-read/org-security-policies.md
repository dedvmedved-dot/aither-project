# Профили безопасности организаций (#38)

**Дата:** 09.07.2026
**Статус:** ✅ Реализовано
**Компонент:** Портал (BFF)

---

## Обзор

Каждая организация в Aither Platform имеет настраиваемый профиль безопасности. Политики переопределяют глобальные настройки и могут быть строже (но не слабее) ограничений тарифного плана.

Пример: тариф VIP разрешает 10K RPM и все модели, но владелец организации может:
- Включить DLP-фильтрацию
- Ограничить доступные модели до конкретного списка
- Установить лимит в 500 токенов на запрос
- Запретить доступ с внешних IP

---

## Модель данных

Таблица `portal_org_policies` (шардирована по `org_id` — 1:1 с `portal_organizations`):

| Поле | Тип | По умолчанию | Описание |
|---|---|---|---|
| `org_id` | UUID PK | — | Ссылка на организацию |
| **DLP / Фильтрация контента** ||||
| `dlp_enabled` | BOOLEAN | `true` | Фильтр ДСП/конфиденциальных данных |
| `jailbreak_detection` | BOOLEAN | `true` | Детектор jailbreak-промптов |
| `sensitive_data_patterns` | TEXT[] | `{}` | Пользовательские regex для DLP |
| **Контроль доступа** ||||
| `allowed_ip_cidrs` | TEXT[] | `{}` | Белый список IP (пусто = любые) |
| `mfa_required` | BOOLEAN | `false` | Требовать MFA для входа |
| `session_timeout_min` | INTEGER | `1440` (24ч) | Время жизни JWT-сессии |
| **API-ключи** ||||
| `api_key_max_age_days` | INTEGER | `365` | Срок действия ключа (NULL = без срока) |
| `api_key_rotation_required` | BOOLEAN | `false` | Принудительная ротация ключей |
| **Rate limits (переопределение тарифа)** ||||
| `custom_rpm` | INTEGER | NULL | Кастомный RPM (NULL = из тарифа) |
| `custom_tpm` | INTEGER | NULL | Кастомный TPM |
| `max_concurrent_requests` | INTEGER | NULL | Макс. одновременных запросов |
| **Модели и токены** ||||
| `allowed_models` | TEXT[] | `{}` | Разрешённые модели (пусто = все) |
| `max_tokens_per_request` | INTEGER | NULL | Лимит токенов на запрос |
| **Хранение данных** ||||
| `chat_retention_days` | INTEGER | `90` | Автоудаление истории чатов |
| `audit_log_retention_days` | INTEGER | `365` | Хранение логов аудита |

---

## API

### GET `/api/v1/orgs/:orgId/policy`

Получить текущую политику безопасности организации. Доступ: любой участник.

**Ответ:**
```json
{
  "org_id": "uuid",
  "policy": {
    "dlp_enabled": true,
    "jailbreak_detection": true,
    "sensitive_data_patterns": [],
    "allowed_ip_cidrs": [],
    "mfa_required": false,
    "session_timeout_min": 1440,
    "api_key_max_age_days": 365,
    "api_key_rotation_required": false,
    "custom_rpm": null,
    "custom_tpm": null,
    "max_concurrent_requests": null,
    "allowed_models": [],
    "max_tokens_per_request": null,
    "chat_retention_days": 90,
    "audit_log_retention_days": 365
  }
}
```

Если для организации политика ещё не настроена — возвращаются значения по умолчанию.

### PUT `/api/v1/orgs/:orgId/policy`

Обновить политику безопасности. Доступ: только `owner`.

**Тело запроса** (все поля опциональны):
```json
{
  "dlp_enabled": false,
  "allowed_models": ["qwen2.5-14b"],
  "max_tokens_per_request": 2048,
  "chat_retention_days": 30
}
```

**Валидация:**
- `session_timeout_min` ≥ 5
- `api_key_max_age_days` ≥ 1 или null
- `custom_rpm`, `custom_tpm` ≥ 1 или null
- `max_concurrent_requests` ≥ 1 или null
- `max_tokens_per_request` ≥ 1 или null
- `chat_retention_days` ≥ 1

**Ответ:**
```json
{
  "org_id": "uuid",
  "policy": { /* полный объект политики после сохранения */ }
}
```

---

## Интеграция с Gateway

Политики передаются в Gateway через делегационный токен (`delegation_token`). Gateway проверяет:

| Политика | Где применяется |
|---|---|
| `dlp_enabled` | Перед отправкой промпта в модель |
| `jailbreak_detection` | Перед отправкой промпта в модель |
| `sensitive_data_patterns` | DLP-сканер промпта и ответа |
| `allowed_models` | Валидация `model` в запросе |
| `custom_rpm` / `custom_tpm` | Rate Limiter (Redis) |
| `max_tokens_per_request` | Параметр `max_tokens` → vLLM |

---

## Примеры использования

### 1. Строгая политика для production-команды

```bash
curl -X PUT /api/v1/orgs/uuid/policy \
  -H "Authorization: Bearer $JWT" \
  -d '{
    "dlp_enabled": true,
    "jailbreak_detection": true,
    "allowed_ip_cidrs": ["10.0.0.0/8", "172.16.0.0/12"],
    "allowed_models": ["qwen2.5-32b"],
    "max_tokens_per_request": 4096,
    "api_key_max_age_days": 30,
    "api_key_rotation_required": true,
    "chat_retention_days": 30
  }'
```

### 2. Публичный доступ с ограничениями

```bash
curl -X PUT /api/v1/orgs/uuid/policy \
  -d '{
    "dlp_enabled": true,
    "allowed_models": ["qwen2.5-14b"],
    "custom_rpm": 10,
    "custom_tpm": 1000,
    "max_tokens_per_request": 1024,
    "chat_retention_days": 7
  }'
```

### 3. Внутренняя R&D — без ограничений

```bash
curl -X PUT /api/v1/orgs/uuid/policy \
  -d '{
    "dlp_enabled": false,
    "jailbreak_detection": false,
    "allowed_ip_cidrs": ["10.129.0.0/16"],
    "max_tokens_per_request": null,
    "chat_retention_days": 365
  }'
```

---

## Файлы

| Файл | Описание |
|---|---|
| `portal/policies.ts` | Модуль: типы, DDL, `loadPolicy()`, `savePolicy()`, `validatePolicy()` |
| `portal/server.ts` | API-эндпоинты `GET/PUT /api/v1/orgs/:orgId/policy` |
| `portal/Dockerfile` | `COPY policies.ts` |

---

## Следующие шаги

- 🔲 UI в портале: вкладка «Безопасность» в настройках организации
- 🔲 Интеграция policy → delegation_token → Gateway enforcement
- 🔲 Аудит изменений политик (кто/когда/что поменял)
- 🔲 Наследование политик от родительской организации (для enterprise)
