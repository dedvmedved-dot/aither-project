# Aither Platform — API Reference

**Версия:** v1  
**Базовый URL:** `http://130.17.1.90/api/v1`  
**Аутентификация:** `Authorization: Bearer ak-...`

---

## Быстрый старт

### 1. Получить API-ключ

Войдите в [портал](http://130.17.1.90) → выберите организацию → **API-ключи** → **Создать ключ**.

Ключ имеет формат `ak-` + 48 hex-символов:
```
ak-0ea262c1d10ca1476d8b0da8ee78a26e9ef5fbb75e1a1936
```

### 2. Отправить запрос

```bash
curl -X POST http://130.17.1.90/api/v1/chat/completions \
  -H "Authorization: Bearer *** \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-14b",
    "messages": [{"role": "user", "content": "Привет! Расскажи о себе."}],
    "max_tokens": 500,
    "temperature": 0.7
  }'
```

### 3. Получить ответ

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "model": "/models/Qwen2.5-14B-Instruct",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Привет! Я — языковая модель Qwen..."
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 33,
    "completion_tokens": 150,
    "total_tokens": 183
  }
}
```

---

## Модели

| ID | Модель | Макс. токенов | GPU |
|---|---|---|---|
| `qwen2.5-14b` | Qwen 2.5 14B Instruct | 4096 | 1× RTX 6000 |
| `qwen2.5-32b` | Qwen 2.5 32B Instruct GPTQ | 4096 | 1× RTX 6000 |

Узнать список моделей:
```bash
curl http://130.17.1.90/api/v1/models
```

---

## POST /api/v1/chat/completions

OpenAI-совместимый эндпоинт для инференса.

### Параметры запроса

| Параметр | Тип | По умолчанию | Описание |
|---|---|---|---|
| `model` | string | `qwen2.5-14b` | ID модели |
| `messages` | array | **обязательно** | История сообщений |
| `max_tokens` | integer | 2048 | Максимум токенов в ответе |
| `temperature` | float | 0.7 | Креативность (0–2) |
| `stream` | boolean | false | Потоковый режим (пока не поддерживается) |

### Формат messages

```json
[
  {"role": "system", "content": "Ты — полезный ассистент."},
  {"role": "user", "content": "Сколько будет 2+2?"}
]
```

Роли: `system`, `user`, `assistant`.

### Коды ответов

| Код | Описание |
|---|---|
| 200 | Успешный ответ |
| 400 | Неверный запрос (нет messages) |
| 401 | Неверный или отозванный API-ключ |
| 402 | Недостаточно средств на балансе |
| 403 | Заблокировано (security: prompt injection / DLP) |
| 429 | Превышен rate limit (60 RPM / 100K TPM) |
| 502 | Gateway недоступен |

### Ошибки

```json
{
  "error": "insufficient_balance",
  "detail": "insufficient balance: 500, reserved: 0, need: 256",
  "required": 256,
  "balance": 500
}
```

```json
{
  "error": "security_violation",
  "reason": "prompt_injection: pattern 'ignore\\s+(all\\s+)?(previous|prior|above|earlier)\\s...'"
}
```

---

## Python SDK (пример)

```python
import requests

API_KEY = "ak-your-key-here"
BASE = "http://130.17.1.90/api/v1"

def chat(messages: list, model="qwen2.5-14b", max_tokens=2048, temperature=0.7):
    resp = requests.post(
        f"{BASE}/chat/completions",
        headers={
            "Authorization": f"Bearer ***            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
    )
    resp.raise_for_status()
    return resp.json()

# Пример использования
response = chat([
    {"role": "user", "content": "Напиши функцию bubble sort на Python"}
])
print(response["choices"][0]["message"]["content"])
```

---

## Node.js SDK (пример)

```javascript
const API_KEY = "ak-your-key-here";
const BASE = "http://130.17.1.90/api/v1";

async function chat(messages, model = "qwen2.5-14b", maxTokens = 2048, temperature = 0.7) {
  const resp = await fetch(`${BASE}/chat/completions`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ***      "Content-Type": "application/json",
    },
    body: JSON.stringify({ model, messages, max_tokens: maxTokens, temperature }),
  });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

// Пример
const response = await chat([
  { role: "user", content: "Объясни, что такое Kubernetes" }
]);
console.log(response.choices[0].message.content);
```

---

## Безопасность

### Фильтры

| Тип | Что блокируется |
|---|---|
| **Prompt Injection** | `ignore all instructions`, `DAN mode`, `system prompt override` (23 EN + 6 RU паттернов) |
| **DLP** | Номера карт, паспорта РФ, СНИЛС, ИНН, телефоны, email, API-ключи, AWS-ключи |

### Rate Limiting

- **60 запросов/мин** на организацию
- **100 000 токенов/мин** на организацию
- При превышении — HTTP 429

### Биллинг

- Каждый запрос резервирует токены с баланса организации
- После ответа списывается фактическое количество токенов
- Авто-пополнение при регистрации: 100 000 токенов (до 10 раз)

---

## Архитектура

```
Клиент (curl / Python / JS)
  │
  ▼
Nginx (VPS2:80)
  │  /api/v1/chat/completions
  ▼
BFF (Fastify, VPS2:3000)
  │  API key → delegation token → Gateway
  ▼
Gateway (K8s, NodePort 30900)
  │  ├── JWT RS256 ✓
  │  ├── Security (prompt injection + DLP)
  │  ├── Rate Limit (Redis)
  │  ├── Billing (PostgreSQL)
  │  └── Model routing
  ▼
vLLM (K8s, GPU-ноды)
  │  ├── Qwen 2.5 14B (n8)
  │  └── Qwen 2.5 32B (n7)
```

---

## Управление ключами

### Создать ключ (через портал)

1. Войдите в портал → выберите организацию
2. Вкладка «API-ключи»
3. Нажмите «Создать ключ»
4. Скопируйте ключ (показывается **только один раз**)

### Отозвать ключ

1. В списке ключей нажмите «Отозвать»
2. Ключ мгновенно деактивируется

### Срок действия

- Ключи не имеют срока действия по умолчанию
- `expires_at` — опциональное поле (можно задать при создании)

---

## Лимиты и квоты

| Ресурс | Лимит | Примечание |
|---|---|---|
| RPM (запросов/мин) | 60 | На организацию |
| TPM (токенов/мин) | 100 000 | На организацию |
| max_tokens | 4096 | Лимит модели |
| API-ключей | не ограничено | На организацию |
| Стартовый баланс | 100 000 | При регистрации |
| Авто-пополнений | 10 | По 100 000 каждое |

---

## FAQ

**Q: Как пополнить баланс?**  
A: Пока доступно авто-пополнение (100K × 10). ЮKassa в разработке.

**Q: Поддерживается ли streaming (SSE)?**  
A: Пока нет. Ответ возвращается целиком. Streaming — в дорожной карте.

**Q: Можно ли использовать несколько ключей?**  
A: Да, создавайте сколько угодно ключей на организацию.

**Q: Как посмотреть статистику использования?**  
A: В портале → организация → «Использование». Или через делегирование.

**Q: Какие модели доступны?**  
A: `qwen2.5-14b` и `qwen2.5-32b`. Новые модели добавляются в каталог.
