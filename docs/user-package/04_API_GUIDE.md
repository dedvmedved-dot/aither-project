# Aither — Руководство по API

**Версия:** CB-WEBUI-01-R1 · **Дата:** 25 июля 2026

---

## Содержание

1. [Общая информация](#общая-информация)
2. [Аутентификация](#аутентификация)
3. [Создание API-ключа](#создание-api-ключа)
4. [GET /v1/models — Список моделей](#get-v1models--список-моделей)
5. [POST /v1/chat/completions — Чат и completion](#post-v1chatcompletions--чат-и-completion)
6. [Коды ответов](#коды-ответов)
7. [Ограничения](#ограничения-rate-limiting)
8. [Примеры на разных языках](#примеры-на-разных-языках)

---

## Общая информация

| Параметр | Значение |
|---|---|
| **Базовый URL** | `https://fb1.spb.ru:443` |
| **Формат данных** | JSON |
| **Метод аутентификации** | Bearer token (API Key) |
| **Content-Type** | `application/json` |
| **TLS** | Доверенный сертификат Let's Encrypt (флаг `-k` не требуется) |

---

## Аутентификация

**Каждый** запрос должен содержать заголовок:

```
Authorization: Bearer ***
```

**Формат ключа:**
```
athr_<префикс>_<секретная_часть>
```

API-ключи создаются через **Web UI** (раздел 🔑 API Ключи) или выдаются администратором.

**Пример заголовка в curl:**
```bash
-H "Authorization: Bearer athr_..."
```

**Пример в Python:**
```python
headers = {"Authorization": "Bearer athr_..."}
```

> 🔐 **API-ключ чувствителен к регистру.** Не добавляйте лишних пробелов.

---

## Создание API-ключа

API-ключи создаются через **Web UI** — это основной способ:

### В Web UI

1. Войдите в Web UI: `https://fb1.spb.ru:443/`
2. Перейдите в раздел **🔑 API Ключи**
3. Нажмите **«+ Создать новый ключ»**
4. Введите название ключа
5. Выберите доступные модели: обе / только 14B / только 32B
6. Нажмите **«Создать»**
7. ⚠️ **Скопируйте полный ключ немедленно!** Он отображается только один раз.

### Через BFF API

```bash
# Создание токена через BFF
curl https://fb1.spb.ru:443/api/v1/tokens \
  -H "Authorization: Bearer ВАШ_API_КЛЮЧ" \
  -H "Content-Type: application/json" \
  -d '{"name": "Мой токен", "models": ["qwen-14b", "qwen-32b-base"]}'
```

### Отзыв ключа

В Web UI: найдите ключ в таблице → нажмите **«Отозвать»** → подтвердите.

Через BFF API:
```bash
curl -X DELETE https://fb1.spb.ru:443/api/v1/tokens/athr_XXXX \
  -H "Authorization: Bearer ВАШ_API_КЛЮЧ"
```

Подробнее: [API KEY USER GUIDE](14_API_KEY_USER_GUIDE.md).

---

## GET /v1/models — Список моделей

Возвращает список доступных моделей.

### Запрос

```bash
curl https://fb1.spb.ru:443/v1/models \
  -H "Authorization: Bearer ВАШ_API_КЛЮЧ"
```

### Ответ (HTTP 200)

```json
{
  "object": "list",
  "data": [
    {
      "id": "qwen-14b",
      "object": "model",
      "created": 1784759438,
      "owned_by": "aither"
    },
    {
      "id": "qwen-32b-base",
      "object": "model",
      "created": 1784759438,
      "owned_by": "aither"
    }
  ]
}
```

### Без аутентификации (HTTP 401)

```json
{"detail": "Valid API Key required (format: athr_...)"}
```

---

## POST /v1/chat/completions — Чат и Completion

Основной эндпоинт для взаимодействия с моделями.

### Параметры запроса

| Параметр | Тип | Обязательно | Описание |
|---|---|---|---|
| `model` | string | ✅ Да | ID модели: `qwen-14b` или `qwen-32b-base` |
| `messages` | array | ✅ Да | Список сообщений |
| `max_tokens` | integer | Нет | Макс. токенов в ответе (по умолчанию: 2048) |
| `temperature` | float | Нет | Креативность: 0.0–2.0 (по умолчанию: 0.7) |

### Сообщение (message)

```json
{"role": "user", "content": "Текст сообщения"}
```

Роли: `user` (пользователь), `assistant` (модель), `system` (системная инструкция).

### Параметры ответа

| Поле | Тип | Описание |
|---|---|---|
| `id` | string | Уникальный ID запроса |
| `object` | string | `"chat.completion"` |
| `model` | string | Использованная модель |
| `choices[0].message.role` | string | `"assistant"` |
| `choices[0].message.content` | string | Текст ответа |
| `choices[0].finish_reason` | string | `"stop"` (успех) или `"length"` (обрезано) |
| `usage.prompt_tokens` | integer | Токенов в запросе |
| `usage.completion_tokens` | integer | Токенов в ответе |
| `usage.total_tokens` | integer | Всего токенов |

---

## Коды ответов

| Код | Значение | Действие |
|---|---|---|
| **200** | Успех | Ответ получен |
| **401** | Ошибка аутентификации | Проверить API-ключ (формат: `athr_...`) |
| **404** | Модель не найдена | Проверить `model` |
| **422** | Неверный формат | Проверить JSON |
| **429** | Rate limit | Подождать минуту |
| **500** | Ошибка сервера | Повторить позже, сообщить |
| **504** | Таймаут | Модель не ответила вовремя |

---

## Ограничения (Rate Limiting)

| Параметр | Значение |
|---|---|
| Лимит запросов | 300 запросов/минуту |
| Burst | 20 запросов |
| Одновременные (14B) | ~4 (очередь GPU) |

При превышении лимита: **HTTP 429**.

---

## Примеры на разных языках

### curl (Linux / macOS)

```bash
# Список моделей
curl https://fb1.spb.ru:443/v1/models \
  -H "Authorization: Bearer ВАШ_API_КЛЮЧ"

# Чат с 14B
curl https://fb1.spb.ru:443/v1/chat/completions \
  -H "Authorization: Bearer ВАШ_API_КЛЮЧ" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-14b","messages":[{"role":"user","content":"Привет!"}],"max_tokens":100}'

# Completion с 32B
curl https://fb1.spb.ru:443/v1/chat/completions \
  -H "Authorization: Bearer ВАШ_API_КЛЮЧ" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-32b-base","messages":[{"role":"user","content":"Продолжи: В начале было"}],"max_tokens":50}'

# Создание токена через BFF
curl https://fb1.spb.ru:443/api/v1/tokens \
  -H "Authorization: Bearer ВАШ_API_КЛЮЧ" \
  -H "Content-Type: application/json" \
  -d '{"name":"Мой токен","models":["qwen-14b","qwen-32b-base"]}'

# Отзыв токена
curl -X DELETE https://fb1.spb.ru:443/api/v1/tokens/athr_XXXX \
  -H "Authorization: Bearer ВАШ_API_КЛЮЧ"
```

### Python

```python
import requests

KEY = "athr_..."
BASE = "https://fb1.spb.ru:443"
HEADERS = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

# Список моделей
r = requests.get(f"{BASE}/v1/models", headers=HEADERS)
print("Модели:", [m["id"] for m in r.json()["data"]])

# Чат с 14B
r = requests.post(f"{BASE}/v1/chat/completions", headers=HEADERS, json={
    "model": "qwen-14b",
    "messages": [{"role": "user", "content": "Привет! Как дела?"}],
    "max_tokens": 100
})
print("14B:", r.json()["choices"][0]["message"]["content"])

# Completion с 32B
r = requests.post(f"{BASE}/v1/chat/completions", headers=HEADERS, json={
    "model": "qwen-32b-base",
    "messages": [{"role": "user", "content": "Продолжи: Искусственный интеллект"}],
    "max_tokens": 50
})
print("32B:", r.json()["choices"][0]["message"]["content"])

# Создание токена
r = requests.post(f"{BASE}/api/v1/tokens", headers=HEADERS, json={
    "name": "Мой токен",
    "models": ["qwen-14b", "qwen-32b-base"]
})
print("Новый ключ:", r.json())

# Обработка ошибок
if r.status_code != 200:
    print(f"Ошибка {r.status_code}: {r.json().get('detail', r.text)}")
```

### PowerShell (Windows)

```powershell
$Key = "athr_..."
$Base = "https://fb1.spb.ru:443"
$Headers = @{
    "Authorization" = "Bearer $Key"
    "Content-Type" = "application/json"
}

# Список моделей
$models = Invoke-RestMethod -Uri "$Base/v1/models" -Headers $Headers
Write-Host "Модели: $($models.data.id -join ', ')"

# Чат с 14B
$body = @{
    model = "qwen-14b"
    messages = @(@{role="user"; content="Привет! Как дела?"})
    max_tokens = 100
} | ConvertTo-Json -Depth 3

$response = Invoke-RestMethod -Uri "$Base/v1/chat/completions" `
    -Method Post -Headers $Headers -Body $body
Write-Host "14B: $($response.choices[0].message.content)"

# Completion с 32B
$body = @{
    model = "qwen-32b-base"
    messages = @(@{role="user"; content="Продолжи: Искусственный интеллект"})
    max_tokens = 50
} | ConvertTo-Json -Depth 3

$response = Invoke-RestMethod -Uri "$Base/v1/chat/completions" `
    -Method Post -Headers $Headers -Body $body
Write-Host "32B: $($response.choices[0].message.content)"
```

---

## Связанные документы

- [USER GUIDE](03_USER_GUIDE.md) — полное руководство
- [WEB UI GUIDE](13_WEB_UI_GUIDE.md) — основной интерфейс
- [QUICK START](02_QUICK_START.md) — быстрый старт
- [API KEY USER GUIDE](14_API_KEY_USER_GUIDE.md) — управление API-ключами
- [AI AGENT CONNECTION PRIMER](16_AI_AGENT_CONNECTION_PRIMER.md) — подключение агентов
- [KNOWN LIMITATIONS](10_KNOWN_LIMITATIONS.md) — ограничения
- [FAQ](08_FAQ.md) — частые вопросы
