# Aither — Подключение AI-агентов

**Версия:** CB-WEBUI-01-R1 · **Дата:** 25 июля 2026

---

## Содержание

1. [Что такое AI-агент?](#что-такое-ai-агент)
2. [Подготовка: создание ключа](#подготовка-создание-ключа)
3. [Базовая настройка (переменные окружения)](#базовая-настройка-переменные-окружения)
4. [Claude Code](#claude-code)
5. [OpenAI Codex CLI](#openai-codex-cli)
6. [OpenCode](#opencode)
7. [Hermes Agent](#hermes-agent)
8. [OpenAI-совместимые клиенты](#openai-совместимые-клиенты)
9. [Python-клиент (openai library)](#python-клиент-openai-library)
10. [Проверка подключения](#проверка-подключения)
11. [Устранение проблем](#устранение-проблем)

---

## Что такое AI-агент?

**AI-агент** — это программа, которая автономно выполняет задачи, используя языковую модель как «мозг». Агенты могут:

- Писать и редактировать код
- Анализировать файлы и проекты
- Выполнять многошаговые задачи
- Взаимодействовать с файловой системой и инструментами

Для работы агенту нужен доступ к LLM — и Aither предоставляет этот доступ через API.

---

## Подготовка: создание ключа

Перед настройкой агента создайте **отдельный API-ключ**:

1. Войдите в Web UI: `https://fb1.spb.ru:443/`
2. Перейдите в раздел **🔑 API Ключи**
3. Нажмите **«+ Создать новый ключ»**
4. Название: `AI-агент [Имя агента]` (например, `AI-агент Claude Code`)
5. Модели: **Обе (14B и 32B)**
6. Нажмите **«Создать»**
7. ⚠️ **Скопируйте ключ!** Он потребуется для настройки.

> 💡 **Рекомендация:** Создавайте отдельный ключ для каждого агента. При проблемах можно отозвать ключ одного агента, не затрагивая другие.

Подробнее о ключах: [API KEY USER GUIDE](14_API_KEY_USER_GUIDE.md).

---

## Базовая настройка (переменные окружения)

Большинство агентов настраиваются через переменные окружения. Добавьте в ваш `~/.bashrc`, `~/.zshrc` или эквивалент:

```bash
# Aither API
export AITHER_API_KEY="athr_..."
export AITHER_BASE_URL="https://fb1.spb.ru:443"

# Или для внутренней сети:
# export AITHER_BASE_URL="http://10.129.13.78:30080"
```

Примените:
```bash
source ~/.bashrc
```

---

## Claude Code

**Claude Code** — AI-агент от Anthropic для разработки.

### Настройка

Claude Code поддерживает кастомные OpenAI-совместимые эндпоинты. Используйте Aither как провайдер:

```bash
# Установка Claude Code
npm install -g @anthropic-ai/claude-code

# Настройка для Aither
export OPENAI_API_KEY="athr_..."
export OPENAI_BASE_URL="https://fb1.spb.ru:443/v1"

# Запуск
claude
```

Альтернативно, настройте через конфигурацию Claude Code для использования OpenAI-совместимого провайдера с моделью `qwen-14b`.

---

## OpenAI Codex CLI

**OpenAI Codex CLI** — официальный CLI-агент от OpenAI.

### Настройка

```bash
# Установка
npm install -g @openai/codex

# Настройка для Aither
export OPENAI_API_KEY="athr_..."
export OPENAI_BASE_URL="https://fb1.spb.ru:443/v1"

# Запуск с указанием модели
codex --model qwen-14b
```

### Использование

```bash
# Работа в текущей директории
codex

# Конкретная задача
codex "Напиши функцию для сортировки на Python"
```

---

## OpenCode

**OpenCode** — терминальный AI-агент для разработки.

### Настройка

```bash
# Установка
pip install opencode

# Настройка для Aither
export OPENAI_API_KEY="athr_..."
export OPENAI_BASE_URL="https://fb1.spb.ru:443/v1"

# Запуск
opencode --model qwen-14b
```

---

## Hermes Agent

**Hermes Agent** (by Nous Research) — многофункциональный AI-ассистент.

### Настройка через конфигурацию

```bash
# Добавление Aither как провайдера
hermes config set provider.aither.api_key "athr_..."
hermes config set provider.aither.base_url "https://fb1.spb.ru:443/v1"
hermes config set provider.aither.models '["qwen-14b", "qwen-32b-base"]'

# Использование как модель по умолчанию
hermes config set model "aither/qwen-14b"
```

### Настройка через переменные окружения

```bash
export OPENAI_API_KEY="athr_..."
export OPENAI_BASE_URL="https://fb1.spb.ru:443/v1"
```

---

## OpenAI-совместимые клиенты

Aither совместим с OpenAI API. Любой инструмент, поддерживающий OpenAI, может использовать Aither:

### Общий шаблон настройки

```bash
export OPENAI_API_KEY="athr_..."
export OPENAI_BASE_URL="https://fb1.spb.ru:443/v1"
```

### Модели для использования

| Модель Aither | Назначение |
|---|---|
| `qwen-14b` | Чат, диалоги, инструкции (рекомендуется для агентов) |
| `qwen-32b-base` | Продолжение текста, генерация |

> ⚠️ Для агентов рекомендуется `qwen-14b` — она лучше следует инструкциям.

---

## Python-клиент (openai library)

Пример прямого использования Aither из Python-агента:

```python
from openai import OpenAI

# Настройка клиента на Aither
client = OpenAI(
    api_key="athr_...",
    base_url="https://fb1.spb.ru:443/v1"
)

# Чат с моделью
response = client.chat.completions.create(
    model="qwen-14b",
    messages=[
        {"role": "system", "content": "Ты — AI-агент для разработки."},
        {"role": "user", "content": "Напиши функцию на Python для парсинга JSON."}
    ],
    max_tokens=500
)

print(response.choices[0].message.content)
```

### Хранение ключа безопасно

```python
import os
from openai import OpenAI

# Ключ из переменной окружения (безопасно)
client = OpenAI(
    api_key=os.environ["AITHER_API_KEY"],
    base_url=os.environ.get("AITHER_BASE_URL", "https://fb1.spb.ru:443/v1")
)
```

---

## Проверка подключения

Проверьте, что агент может достучаться до Aither:

### curl

```bash
curl https://fb1.spb.ru:443/v1/models \
  -H "Authorization: Bearer athr_..."
```

Ожидаемый ответ: список моделей с HTTP 200.

### Python

```python
from openai import OpenAI

client = OpenAI(
    api_key="athr_...",
    base_url="https://fb1.spb.ru:443/v1"
)

models = client.models.list()
for model in models.data:
    print(f"✅ {model.id}")
```

### Что должно получиться

```
✅ qwen-14b
✅ qwen-32b-base
```

---

## Устранение проблем

### Агент не подключается

| Симптом | Возможная причина | Решение |
|---|---|---|
| `Connection refused` | Неверный URL | Проверьте `AITHER_BASE_URL` / `OPENAI_BASE_URL` |
| `401 Unauthorized` | Неверный или отозванный ключ | Проверьте ключ, создайте новый в Web UI |
| `404 Not Found` | Неверный путь API | URL должен заканчиваться на `/v1` |
| Таймаут | Сеть или нагрузка | Проверьте подключение, попробуйте позже |

### Агент работает, но ответы плохие

| Симптом | Возможная причина | Решение |
|---|---|---|
| Бессмысленные ответы | Используется qwen-32b-base | Переключите на `qwen-14b` |
| Ответы обрезаны | Маленький `max_tokens` | Увеличьте лимит токенов |
| Модель «забывает» контекст | Превышено контекстное окно (4096) | Уменьшите историю диалога |

### Ключ не работает

1. Проверьте статус ключа в Web UI (🔑 API Ключи)
2. Если статус «Отозван» — создайте новый
3. Проверьте формат: `Authorization: Bearer athr_...` (не забудьте `Bearer`!)

---

## Рекомендации

### Для продуктивной работы агентов

1. **Используйте `qwen-14b`** — она лучше понимает инструкции
2. **Ограничивайте контекст** — не передавайте больше 3000 слов за раз
3. **Создавайте отдельные ключи** — один ключ на одного агента
4. **Мониторьте использование** — проверяйте дату последнего использования в Web UI
5. **Отзывайте неиспользуемые ключи** — завершили проект → отзовите ключ

### Лимиты

| Параметр | Значение |
|---|---|
| Запросов в минуту | 300 |
| Одновременных запросов к 14B | ~4 |
| Контекстное окно | 4096 токенов |

Не запускайте нескольких агентов одновременно с интенсивной нагрузкой — они будут конкурировать за GPU.

---

## Связанные документы

- [API KEY USER GUIDE](14_API_KEY_USER_GUIDE.md) — создание и управление ключами
- [API GUIDE](04_API_GUIDE.md) — полное описание API
- [WEB UI GUIDE](13_WEB_UI_GUIDE.md) — основной интерфейс
- [DUAL ZONE ACCESS GUIDE](15_DUAL_ZONE_ACCESS_GUIDE.md) — Internet vs Test Zone
- [SECURITY RULES](09_SECURITY_RULES.md) — безопасность агентов и ключей
- [KNOWN LIMITATIONS](10_KNOWN_LIMITATIONS.md) — ограничения системы
