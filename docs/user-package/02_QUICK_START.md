# Aither — Быстрый старт

**Время на выполнение:** 5 минут
**Что нужно:** API-ключ (получите у владельца проекта)

---

## Содержание

1. [Проверка подключения](#шаг-1-проверка-подключения)
2. [Список моделей](#шаг-2-список-моделей)
3. [Первый запрос к 14B](#шаг-3-первый-запрос-к-14b-чат)
4. [Запрос к 32B](#шаг-4-запрос-к-32b-completion)
5. [Что дальше?](#что-дальше)

---

## Шаг 1: Проверка подключения

Откройте терминал (командную строку) и выполните:

### curl (Linux / macOS / WSL)
```bash
curl -k https://fb1.spb.ru:443/v1/models \
  -H "Authorization: Bearer ВАШ_API_КЛЮЧ"
```

### PowerShell (Windows)
```powershell
Invoke-RestMethod -Uri "https://fb1.spb.ru:443/v1/models" `
  -Headers @{"Authorization"="Bearer ВАШ_API_КЛЮЧ"} `
  -SkipCertificateCheck
```

### Python
```python
import requests
response = requests.get(
    "https://fb1.spb.ru:443/v1/models",
    headers={"Authorization": "Bearer ВАШ_API_КЛЮЧ"},
    verify=False
)
print(response.json())
```

**Ожидаемый ответ:**
```json
{
  "object": "list",
  "data": [
    {"id": "qwen-14b", "object": "model", "owned_by": "aither"},
    {"id": "qwen-32b-base", "object": "model", "owned_by": "aither"}
  ]
}
```

> Если получили ошибку `401` — проверьте API-ключ. Если `000` или таймаут — проверьте подключение к интернету.

---

## Шаг 2: Список моделей

Вы уже получили список моделей на шаге 1. Система предоставляет **две модели**:

| Модель | Тип | Для чего |
|---|---|---|
| `qwen-14b` | Чат (instruct) | Диалоги, вопросы-ответы |
| `qwen-32b-base` | Базовая (completion) | Продолжение текста |

---

## Шаг 3: Первый запрос к 14B (чат)

### curl
```bash
curl -k https://fb1.spb.ru:443/v1/chat/completions \
  -H "Authorization: Bearer ВАШ_API_КЛЮЧ" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-14b",
    "messages": [{"role": "user", "content": "Привет! Расскажи, что ты умеешь."}],
    "max_tokens": 200
  }'
```

### PowerShell
```powershell
$body = @{
    model = "qwen-14b"
    messages = @(@{role="user"; content="Привет! Расскажи, что ты умеешь."})
    max_tokens = 200
} | ConvertTo-Json -Depth 3

Invoke-RestMethod -Uri "https://fb1.spb.ru:443/v1/chat/completions" `
  -Method Post `
  -Headers @{"Authorization"="Bearer ВАШ_API_КЛЮЧ"; "Content-Type"="application/json"} `
  -Body $body `
  -SkipCertificateCheck
```

### Python
```python
import requests
response = requests.post(
    "https://fb1.spb.ru:443/v1/chat/completions",
    headers={"Authorization": "Bearer ВАШ_API_КЛЮЧ", "Content-Type": "application/json"},
    json={
        "model": "qwen-14b",
        "messages": [{"role": "user", "content": "Привет! Расскажи, что ты умеешь."}],
        "max_tokens": 200
    },
    verify=False
)
print(response.json()["choices"][0]["message"]["content"])
```

**Ожидаемый ответ:** Осмысленный текст на русском языке.

---

## Шаг 4: Запрос к 32B (completion)

Модель 32B — базовая, она продолжает текст, а не ведёт диалог.

### curl
```bash
curl -k https://fb1.spb.ru:443/v1/chat/completions \
  -H "Authorization: Bearer ВАШ_API_КЛЮЧ" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-32b-base",
    "messages": [{"role": "user", "content": "Продолжи: Однажды в студёную зимнюю пору"}],
    "max_tokens": 100
  }'
```

### Python
```python
response = requests.post(
    "https://fb1.spb.ru:443/v1/chat/completions",
    headers={"Authorization": "Bearer ВАШ_API_КЛЮЧ", "Content-Type": "application/json"},
    json={
        "model": "qwen-32b-base",
        "messages": [{"role": "user", "content": "Продолжи: Однажды в студёную зимнюю пору"}],
        "max_tokens": 100
    },
    verify=False
)
print(response.json()["choices"][0]["message"]["content"])
```

> ⚠️ **Важно:** 32B — базовая модель. Ответ может быть не в формате диалога. Это нормально.

---

## Что дальше?

- ✅ **Вы выполнили первый запрос!** Система работает.
- 📖 Переходите к [USER GUIDE](03_USER_GUIDE.md) — полное описание возможностей.
- 🧪 Выполните [TEST ASSIGNMENT](05_TEST_ASSIGNMENT.md) — обязательные задания.
- 🐛 Если что-то не работает — заполните [BUG REPORT](06_BUG_REPORT_TEMPLATE.md).

---

## Быстрая проверка (всё в одном)

```bash
# Замените ВАШ_API_КЛЮЧ на реальный ключ
KEY="ВАШ_API_КЛЮЧ"
ENDPOINT="https://fb1.spb.ru:443"

echo "1. Модели:" && curl -sk "$ENDPOINT/v1/models" -H "Authorization: Bearer $KEY" | python3 -m json.tool
echo "2. Чат 14B:" && curl -sk "$ENDPOINT/v1/chat/completions" -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d '{"model":"qwen-14b","messages":[{"role":"user","content":"Привет"}],"max_tokens":50}' | python3 -m json.tool
echo "3. Готово!"
```
