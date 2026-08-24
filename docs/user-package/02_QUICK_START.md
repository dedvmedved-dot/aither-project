# Aither — Быстрый старт

**Время на выполнение:** 5 минут
**Что нужно:** учётная запись Web UI (получите у администратора)

---

## Содержание

- [🌐 Web UI (рекомендуется)](#рекомендуемый-способ--web-ui)
- [💻 Для разработчиков: curl / Python / PowerShell](#для-разработчиков-curl--python--powershell)

---

## Рекомендуемый способ — Web UI

### Шаг 1: Откройте Web UI

Откройте браузер и перейдите:

**Internet:** `https://fb1.spb.ru:10443/`
**Test Zone:** `http://10.129.13.78:30080/`

> Сертификат HTTPS — доверенный (Let's Encrypt). Предупреждений браузера быть не должно.

### Шаг 2: Войдите

Введите имя пользователя и пароль, полученные от администратора.

### Шаг 3: Откройте Чат

Нажмите **💬 Чат** в верхнем меню.

### Шаг 4: Выберите модель

В выпадающем списке выберите:
- **qwen3-32b (Чат)** — для диалогов
- **qwen3.8-27b (Базовая)** — для продолжения текста

### Шаг 5: Отправьте сообщение

Введите текст и нажмите **Enter**.

### Шаг 6: Получите ответ

Модель ответит в чате. Используйте кнопку **📋 Копировать** для сохранения ответа.

### Шаг 7: Проверьте обе модели

Переключитесь на другую модель и отправьте ещё один запрос.

✅ **Вы освоили Aither!** Переходите к [тестовым заданиям](05_TEST_ASSIGNMENT.md).

---

## Для разработчиков: curl / Python / PowerShell

---

## Шаг 1: Проверка подключения

Откройте терминал (командную строку) и выполните:

### curl (Linux / macOS / WSL)
```bash
curl https://fb1.spb.ru:10443/api/v1/models \
  -H "Authorization: Bearer ВАШ_API_КЛЮЧ"
```

### PowerShell (Windows)
```powershell
Invoke-RestMethod -Uri "https://fb1.spb.ru:10443/api/v1/models" `
  -Headers @{"Authorization"="Bearer ВАШ_API_КЛЮЧ"}
```

### Python
```python
import requests
response = requests.get(
    "https://fb1.spb.ru:10443/api/v1/models",
    headers={"Authorization": "Bearer ВАШ_API_КЛЮЧ"}
)
print(response.json())
```

**Ожидаемый ответ:**
```json
{
  "object": "list",
  "data": [
    {"id": "qwen3-32b", "object": "model", "owned_by": "aither"},
    {"id": "qwen3.8-27b", "object": "model", "owned_by": "aither"}
  ]
}
```

> Если получили ошибку `401` — проверьте API-ключ. Если таймаут — проверьте подключение к интернету.
> **API-ключи имеют префикс `aither_`.** Создать ключ можно в Web UI: 🔑 API Ключи → Создать.

---

## Шаг 2: Список моделей

Вы уже получили список моделей на шаге 1. Система предоставляет **две модели**:

| Модель | Тип | Для чего |
|---|---|---|
| `qwen3-32b` | Чат (instruct) | Диалоги, вопросы-ответы |
| `qwen3.8-27b` | Базовая (completion) | Продолжение текста |

---

## Шаг 3: Первый запрос к 14B (чат)

### curl
```bash
curl https://fb1.spb.ru:10443/api/v1/chat/completions \
  -H "Authorization: Bearer ВАШ_API_КЛЮЧ" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-32b",
    "messages": [{"role": "user", "content": "Привет! Расскажи, что ты умеешь."}],
    "max_tokens": 200
  }'
```

### Python
```python
import requests
response = requests.post(
    "https://fb1.spb.ru:10443/api/v1/chat/completions",
    headers={"Authorization": "Bearer ВАШ_API_КЛЮЧ", "Content-Type": "application/json"},
    json={
        "model": "qwen3-32b",
        "messages": [{"role": "user", "content": "Привет! Расскажи, что ты умеешь."}],
        "max_tokens": 200
    }
)
print(response.json()["choices"][0]["message"]["content"])
```

**Ожидаемый ответ:** Осмысленный текст на русском языке.

---

## Шаг 4: Запрос к 32B (completion)

Модель 32B — базовая, она продолжает текст, а не ведёт диалог.

### curl
```bash
curl https://fb1.spb.ru:10443/api/v1/chat/completions \
  -H "Authorization: Bearer ВАШ_API_КЛЮЧ" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.8-27b",
    "messages": [{"role": "user", "content": "Продолжи: Однажды в студёную зимнюю пору"}],
    "max_tokens": 100
  }'
```

### Python
```python
response = requests.post(
    "https://fb1.spb.ru:10443/api/v1/chat/completions",
    headers={"Authorization": "Bearer ВАШ_API_КЛЮЧ", "Content-Type": "application/json"},
    json={
        "model": "qwen3.8-27b",
        "messages": [{"role": "user", "content": "Продолжи: Однажды в студёную зимнюю пору"}],
        "max_tokens": 100
    }
)
print(response.json()["choices"][0]["message"]["content"])
```

> ⚠️ **Важно:** 32B — базовая модель. Ответ может быть не в формате диалога. Это нормально.

---

## Что дальше?

- ✅ **Вы выполнили первый запрос!** Система работает.
- 🌐 **Web UI** — основной интерфейс. Откройте `https://fb1.spb.ru:10443/`.
- 📖 Переходите к [WEB UI GUIDE](13_WEB_UI_GUIDE.md) — полное описание Web UI.
- 🧪 Выполните [TEST ASSIGNMENT](05_TEST_ASSIGNMENT.md) — обязательные задания.
- 🔑 Создайте API-ключ для автоматизации: [API KEY USER GUIDE](14_API_KEY_USER_GUIDE.md).
- 🐛 Если что-то не работает — заполните [BUG REPORT](06_BUG_REPORT_TEMPLATE.md).
