# Aither — Подключение AI-агентов

**Версия:** CB-WEBUI-03 · **Дата:** 24 августа 2026

---

## Содержание

1. [Что такое AI-агент?](#что-такое-ai-агент)
2. [Подготовка: создание ключа](#подготовка-создание-ключа)
3. [Базовая настройка (OpenAI-совместимый клиент)](#базовая-настройка-openai-совместимый-клиент)
4. [Hermes Agent](#hermes-agent)
5. [Python-клиент (openai library)](#python-клиент-openai-library)
6. [Проверка подключения](#проверка-подключения)
7. [Устранение проблем](#устранение-проблем)

---

## Что такое AI-агент?

**AI-агент** — это программа, которая автономно выполняет задачи, используя языковую модель как «мозг». Для работы агенту нужен доступ к LLM — Aither предоставляет этот доступ через OpenAI-совместимый API.

---

## Подготовка: создание ключа

Перед настройкой агента создайте **отдельный API-ключ**:

1. Войдите в Web UI: `https://fb1.spb.ru:10443/` (или `http://10.129.13.78:30080/` в тестовой зоне)
2. Перейдите в раздел **🔑 API Ключи**
3. Нажмите **«+ Создать новый ключ»**
4. Укажите название (например, `AI-агент`)
5. Нажмите **«Создать»**
6. ⚠️ **Скопируйте ключ!** Полный ключ показывается только один раз.

> 💡 Создавайте отдельный ключ для каждого агента — при проблемах можно отозвать ключ одного агента, не затрагивая другие.

---

## Базовая настройка (OpenAI-совместимый клиент)

Aither совместим с OpenAI API. Любой **OpenAI-compatible client** может использовать Aither со следующей универсальной конфигурацией:

```bash
export OPENAI_API_KEY="aither_..."
export OPENAI_BASE_URL="https://fb1.spb.ru:10443/api/v1"
```

Внутренняя (тестовая) зона:

```bash
export OPENAI_API_KEY="aither_..."
export OPENAI_BASE_URL="http://10.129.13.78:30080/api/v1"
```

Активные модели:

| Модель | Описание |
|---|---|
| `qwen3-32b` | Qwen3-32B (AWQ), контекст 64K |
| `qwen3.8-27b` | Qwen3.8-27B (FP8), контекст 16K |

Обе модели используют scope **`model:qwen3:chat`**.

> ⚠️ Конкретный AI-agent CLI (Claude Code, Codex и т.п.) может иметь собственный синтаксис конфигурации. В разделе выше приведён универсальный OpenAI-совместимый формат. Сверяйтесь с документацией конкретного клиента.

---

## Hermes Agent

Hermes Agent (by Nous Research) — AI-ассистент, работающий как OpenAI-совместимый клиент.

Для подключения Aither как OpenAI-совместимого провайдера используйте универсальную конфигурацию:

```bash
export OPENAI_API_KEY="aither_..."
export OPENAI_BASE_URL="https://fb1.spb.ru:10443/api/v1"
```

и укажите модель `qwen3-32b` или `qwen3.8-27b` в настройках клиента.

> Примечание: внутренний executor платформы Aither — Hermes. AI Codex не является внутренним executor Aither.

---

## Python-клиент (openai library)

```python
from openai import OpenAI

client = OpenAI(
    api_key="aither_...",
    base_url="https://fb1.spb.ru:10443/api/v1",
)

response = client.chat.completions.create(
    model="qwen3-32b",
    messages=[
        {"role": "system", "content": "Ты — AI-агент для разработки."},
        {"role": "user", "content": "Напиши функцию на Python для парсинга JSON."},
    ],
    max_tokens=2048,
)

print(response.choices[0].message.content)
```

### Безопасное хранение ключа

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["AITHER_API_KEY"],
    base_url=os.environ.get("AITHER_BASE_URL", "https://fb1.spb.ru:10443/api/v1"),
)
```

---

## Проверка подключения

### curl

```bash
curl https://fb1.spb.ru:10443/api/v1/models \
  -H "Authorization: Bearer aither_..."
```

Ожидаемый ответ (HTTP 200):

```json
{"object":"list","data":[
  {"id":"qwen3-32b","object":"model","owned_by":"aither"},
  {"id":"qwen3.8-27b","object":"model","owned_by":"aither"}
]}
```

### Python

```python
from openai import OpenAI

client = OpenAI(
    api_key="aither_...",
    base_url="https://fb1.spb.ru:10443/api/v1",
)

models = client.models.list()
for model in models.data:
    print(f"✅ {model.id}")
```

Ожидаемый вывод:

```
✅ qwen3-32b
✅ qwen3.8-27b
```

---

## Устранение проблем

| Симптом | Возможная причина | Решение |
|---|---|---|
| `401 Unauthorized` | Неверный/отозванный ключ или неверный формат | Ключ должен начинаться с `aither_`; проверьте ключ в Web UI |
| `403 Forbidden` | Нет scope `model:qwen3:chat` | Создайте ключ с доступом к активным моделям |
| `404 Not Found` | Неверный путь API или неверная модель | Base URL заканчивается на `/api/v1`; модель — `qwen3-32b` или `qwen3.8-27b` |
| `400 Bad Request` | Некорректный запрос (например, невалидный `max_tokens`) | `max_tokens` — целое, 1…4096 |
| Ответы обрезаны | Малый `max_tokens` | Увеличьте до 2048 (макс. 4096) |
| Таймаут | Сеть или нагрузка | Проверьте подключение, попробуйте позже |

---

## Связанные документы

- [API KEY USER GUIDE](14_API_KEY_USER_GUIDE.md) — создание и управление ключами
- [MODEL USAGE GUIDE](17_MODEL_USAGE_GUIDE.md) — как выбирать модель
- [API GUIDE](04_API_GUIDE.md) — полное описание API
- [SECURITY RULES](09_SECURITY_RULES.md) — безопасность агентов и ключей
- [KNOWN LIMITATIONS](10_KNOWN_LIMITATIONS.md) — ограничения системы
