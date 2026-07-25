# Aither — Руководство по подключению AI-агентов

**Версия:** CB-WEBUI-01-R1 · **Дата:** 26 июля 2026

---

## Содержание

1. [Требования](#требования)
2. [Получение API-ключа через Web UI](#получение-api-ключа-через-web-ui)
3. [Базовые URL](#базовые-url)
4. [Доступные модели](#доступные-модели)
5. [Формат заголовка Authorization](#формат-заголовка-authorization)
6. [Пример: Python](#пример-python)
7. [Пример: shell / curl](#пример-shell--curl)
8. [Пример: конфигурация Hermes Agent](#пример-конфигурация-hermes-agent)
9. [Пример: OpenAI-совместимый клиент](#пример-openai-совместимый-клиент)
10. [Таймауты](#таймауты)
11. [Повтор запросов (retry)](#повтор-запросов-retry)
12. [Примечания по TLS](#примечания-по-tls)
13. [Правила хранения секретов](#правила-хранения-секретов)
14. [Процедура отзыва ключа](#процедура-отзыва-ключа)
15. [Диагностика ошибок](#диагностика-ошибок)

---

## Требования

Для подключения AI-агента к платформе Aither необходимы:

| Компонент | Описание |
|---|---|
| **API-ключ** | Токен формата `athr_XXXXXXXX_...`. Создаётся через Web UI. |
| **Базовый URL** | `https://fb1.spb.ru:443` (Internet) или `http://10.129.13.78:30080` (Test Zone) |
| **Сетевая связность** | Исходящий доступ на порт 443 (Internet) или 30080 (Test Zone) |
| **OpenAI-совместимый клиент** | Любая библиотека/инструмент, умеющие работать с OpenAI Chat Completions API |

> 💡 Aither предоставляет OpenAI-совместимый API. Если ваш агент поддерживает OpenAI — он поддерживает Aither.

---

## Получение API-ключа через Web UI

API-ключ (токен) — это персональный идентификатор, дающий программам и агентам доступ к моделям Aither.

### Пошаговая инструкция

1. **Войдите в Web UI:** `https://fb1.spb.ru:443/`
2. Перейдите в раздел **🔑 API Ключи** (верхнее меню).
3. Нажмите кнопку **«+ Создать новый ключ»**.
4. **Заполните форму:**

   | Поле | Описание | Рекомендация |
   |---|---|---|
   | **Название** | Описательное имя ключа | `AI-агент ИмяАгента` (например, `AI-агент Python скрипт`) |
   | **Модели** | К каким моделям дать доступ | **Обе (14B и 32B)** — для максимальной гибкости |

5. Нажмите **«Создать»**.
6. ⚠️ **СКОПИРУЙТЕ КЛЮЧ НЕМЕДЛЕННО!** Полный ключ отображается **только один раз**. После закрытия окна восстановить его невозможно.

### Что делать, если ключ не сохранён?

Отзовите ключ и создайте новый. Полный ключ не восстанавливается.

> 💡 **Рекомендация:** Создавайте отдельный ключ для каждого агента. Это позволит отозвать ключ одного агента, не затрагивая другие.

---

## Базовые URL

Aither предоставляет **две точки доступа**. Функционально они идентичны, различаются сетевым расположением и протоколом.

### Internet (основная)

```
https://fb1.spb.ru:443
```

| Параметр | Значение |
|---|---|
| **Доступ** | Открытый (из любой точки интернета) |
| **Протокол** | HTTPS |
| **TLS** | Let's Encrypt (доверенный сертификат) |
| **Использование** | Повседневная работа, удалённый доступ |

### Test Zone (внутренняя сеть)

```
http://10.129.13.78:30080
```

| Параметр | Значение |
|---|---|
| **Доступ** | Внутренняя сеть / VPN |
| **Протокол** | HTTP |
| **TLS** | Отсутствует |
| **Использование** | Тестирование из изолированной среды, доступ без интернета |

> ⚠️ **Важно:** API-ключи и учётные записи — общие. Один ключ работает в обеих зонах. Лимиты запросов (300/мин) суммируются по обеим зонам.

---

## Доступные модели

| Идентификатор | Обозначение | Назначение | Контекстное окно |
|---|---|---|---|
| `qwen-14b` | **MODEL_A** | Чат, диалоги, следование инструкциям (рекомендуется для агентов) | 4096 токенов |
| `qwen-32b-base` | **MODEL_B** | Продолжение текста, генерация (base-модель, без инструктивной настройки) | 4096 токенов |

> ⚠️ **Для AI-агентов рекомендуется `qwen-14b` (MODEL_A)** — она лучше понимает инструкции и ведёт диалог. `qwen-32b-base` (MODEL_B) — базовая генеративная модель без инструктивной настройки; может давать бессвязные ответы при использовании в режиме чата.

### Проверка доступных моделей

```bash
curl https://fb1.spb.ru:443/v1/models \
  -H "Authorization: Bearer athr_XXXXXXXX_..."
```

Ожидаемый ответ (HTTP 200):
```json
{
  "object": "list",
  "data": [
    {"id": "qwen-14b", "object": "model", "owned_by": "aither"},
    {"id": "qwen-32b-base", "object": "model", "owned_by": "aither"}
  ]
}
```

---

## Формат заголовка Authorization

**Каждый** запрос к API должен содержать HTTP-заголовок:

```
Authorization: Bearer athr_XXXXXXXX_...
```

### Правила

- Ключ указывается **после** `Bearer` через пробел.
- **Регистр важен:** `Bearer`, а не `bearer` или `BEARER`.
- Ключ чувствителен к регистру.
- Не добавляйте лишних пробелов в начале/конце ключа.
- Не заключайте ключ в кавычки в заголовке.

### Неправильно ❌

```
Authorization: bearer athr_XXXXXXXX_...     # «bearer» с маленькой буквы
Authorization: Bearer "athr_XXXXXXXX_..."    # кавычки вокруг ключа
Authorization: Bearer  athr_XXXXXXXX_...     # двойной пробел
Authorization: athr_XXXXXXXX_...             # отсутствует «Bearer»
```

### Правильно ✅

```
Authorization: Bearer athr_XXXXXXXX_...
```

---

## Пример: Python

### Зависимости

```bash
pip install openai requests
```

### Вариант 1: библиотека `openai` (рекомендуется)

```python
import os
from openai import OpenAI

# Конфигурация
API_KEY = os.environ.get("AITHER_API_KEY", "athr_XXXXXXXX_...")
BASE_URL = os.environ.get("AITHER_BASE_URL", "https://fb1.spb.ru:443")

# Инициализация клиента
client = OpenAI(
    api_key=API_KEY,
    base_url=f"{BASE_URL}/v1"
)

# Запрос к модели
try:
    response = client.chat.completions.create(
        model="qwen-14b",               # MODEL_A — рекомендуется для агентов
        messages=[
            {"role": "system", "content": "Ты — AI-агент для разработки на Python."},
            {"role": "user", "content": "Напиши функцию для парсинга JSON с обработкой ошибок."}
        ],
        max_tokens=500,
        temperature=0.7,
        timeout=120                       # таймаут в секундах
    )

    # Вывод ответа
    answer = response.choices[0].message.content
    usage = response.usage
    print(f"Ответ: {answer}")
    print(f"Токенов: запрос={usage.prompt_tokens}, ответ={usage.completion_tokens}, всего={usage.total_tokens}")

except Exception as e:
    print(f"Ошибка: {e}")
```

### Вариант 2: библиотека `requests` (без openai)

```python
import os
import requests
import time
import json

API_KEY = os.environ.get("AITHER_API_KEY", "athr_XXXXXXXX_...")
BASE_URL = os.environ.get("AITHER_BASE_URL", "https://fb1.spb.ru:443")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": "qwen-14b",
    "messages": [
        {"role": "system", "content": "Ты — AI-агент для разработки на Python."},
        {"role": "user", "content": "Напиши функцию для парсинга JSON с обработкой ошибок."}
    ],
    "max_tokens": 500,
    "temperature": 0.7
}

# Запрос с повторными попытками при ошибках
max_retries = 3
for attempt in range(max_retries):
    try:
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120                         # таймаут в секундах
        )

        if response.status_code == 200:
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
            print(f"Ответ: {answer}")
            break
        elif response.status_code == 429:
            # Rate limit — ждём и повторяем
            wait = int(response.headers.get("Retry-After", 60))
            print(f"Rate limit (429), ожидание {wait}с...")
            time.sleep(wait)
        elif response.status_code >= 500:
            # Серверная ошибка — повторяем
            wait = 2 ** attempt
            print(f"Ошибка сервера ({response.status_code}), попытка {attempt+1}/{max_retries}, ожидание {wait}с...")
            time.sleep(wait)
        else:
            print(f"Ошибка {response.status_code}: {response.text}")
            break
    except requests.exceptions.Timeout:
        print(f"Таймаут, попытка {attempt+1}/{max_retries}")
        time.sleep(2 ** attempt)
    except requests.exceptions.ConnectionError as e:
        print(f"Ошибка соединения: {e}")
        break
```

### Получение списка моделей (Python)

```python
from openai import OpenAI

client = OpenAI(
    api_key="athr_XXXXXXXX_...",
    base_url="https://fb1.spb.ru:443/v1"
)

models = client.models.list()
for model in models.data:
    print(f"✅ {model.id}")
```

---

## Пример: shell / curl

### Проверка соединения и список моделей

```bash
curl -s https://fb1.spb.ru:443/v1/models \
  -H "Authorization: Bearer athr_XXXXXXXX_..."
```

### Запрос к MODEL_A (qwen-14b)

```bash
curl -s https://fb1.spb.ru:443/v1/chat/completions \
  -H "Authorization: Bearer athr_XXXXXXXX_..." \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-14b",
    "messages": [
      {"role": "system", "content": "Ты — AI-агент для разработки."},
      {"role": "user", "content": "Напиши функцию на Python для парсинга JSON."}
    ],
    "max_tokens": 500,
    "temperature": 0.7
  }'
```

### Запрос к MODEL_B (qwen-32b-base)

```bash
curl -s https://fb1.spb.ru:443/v1/chat/completions \
  -H "Authorization: Bearer athr_XXXXXXXX_..." \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-32b-base",
    "messages": [
      {"role": "user", "content": "Продолжи текст: В начале было"}
    ],
    "max_tokens": 50
  }'
```

### Запрос через Test Zone

```bash
curl -s http://10.129.13.78:30080/v1/chat/completions \
  -H "Authorization: Bearer athr_XXXXXXXX_..." \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-14b",
    "messages": [
      {"role": "user", "content": "Привет! Расскажи о себе."}
    ],
    "max_tokens": 100
  }'
```

### Скрипт с повторными попытками (bash)

```bash
#!/bin/bash
API_KEY="athr_XXXXXXXX_..."
BASE_URL="https://fb1.spb.ru:443"
MAX_RETRIES=3
TIMEOUT=120

for attempt in $(seq 1 $MAX_RETRIES); do
    response=$(curl -s -w "\n%{http_code}" \
        --max-time "$TIMEOUT" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"model":"qwen-14b","messages":[{"role":"user","content":"Привет!"}],"max_tokens":50}' \
        "$BASE_URL/v1/chat/completions")

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        echo "✅ Успех: $body" | python3 -m json.tool 2>/dev/null || echo "$body"
        exit 0
    elif [ "$http_code" = "429" ]; then
        echo "⚠️ Rate limit (429), попытка $attempt/$MAX_RETRIES, ждём 60с..."
        sleep 60
    elif [ "$http_code" -ge 500 ]; then
        wait=$((2 ** attempt))
        echo "⚠️ Ошибка сервера ($http_code), попытка $attempt/$MAX_RETRIES, ждём ${wait}с..."
        sleep "$wait"
    else
        echo "❌ Ошибка $http_code: $body"
        exit 1
    fi
done

echo "❌ Исчерпаны попытки"
exit 1
```

---

## Пример: конфигурация Hermes Agent

### Добавление Aither как провайдера

```bash
# Ключ API
hermes config set provider.aither.api_key "athr_XXXXXXXX_..."

# Базовый URL (Internet, с /v1)
hermes config set provider.aither.base_url "https://fb1.spb.ru:443/v1"

# Или для Test Zone:
# hermes config set provider.aither.base_url "http://10.129.13.78:30080/v1"

# Список моделей
hermes config set provider.aither.models '["qwen-14b", "qwen-32b-base"]'

# Установка модели по умолчанию (MODEL_A, рекомендуется для агентов)
hermes config set model "aither/qwen-14b"
```

### Проверка конфигурации

```bash
hermes config get provider.aither
hermes config get model
```

### Использование через переменные окружения (альтернатива)

```bash
export OPENAI_API_KEY="athr_XXXXXXXX_..."
export OPENAI_BASE_URL="https://fb1.spb.ru:443/v1"
```

> 💡 **Совет:** Не указывайте реальный ключ в истории командной строки. Используйте `hermes config set` или читайте ключ из файла:
> ```bash
> export OPENAI_API_KEY="$(cat ~/.aither-key)"
> ```

---

## Пример: OpenAI-совместимый клиент

Aither полностью совместим с OpenAI Chat Completions API. Любой инструмент, поддерживающий кастомный `base_url`, может использовать Aither.

### Универсальный шаблон настройки

Для **любого** OpenAI-совместимого клиента установите переменные окружения:

```bash
export OPENAI_API_KEY="athr_XXXXXXXX_..."
export OPENAI_BASE_URL="https://fb1.spb.ru:443/v1"
```

### Пример: Claude Code (через OpenAI-совместимый режим)

```bash
npm install -g @anthropic-ai/claude-code

export OPENAI_API_KEY="athr_XXXXXXXX_..."
export OPENAI_BASE_URL="https://fb1.spb.ru:443/v1"

claude --model qwen-14b
```

### Пример: OpenCode

```bash
pip install opencode

export OPENAI_API_KEY="athr_XXXXXXXX_..."
export OPENAI_BASE_URL="https://fb1.spb.ru:443/v1"

opencode --model qwen-14b
```

### Пример: Aider

```bash
pip install aider-chat

export OPENAI_API_KEY="athr_XXXXXXXX_..."
export OPENAI_API_BASE="https://fb1.spb.ru:443/v1"

aider --model openai/qwen-14b
```

### Пример: LangChain

```python
import os
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="qwen-14b",
    api_key="athr_XXXXXXXX_...",
    base_url="https://fb1.spb.ru:443/v1",
    temperature=0.7,
    max_tokens=500,
    timeout=120,
    max_retries=3
)

response = llm.invoke("Напиши функцию быстрой сортировки на Python.")
print(response.content)
```

### Пример: LiteLLM

```python
from litellm import completion

response = completion(
    model="openai/qwen-14b",
    messages=[{"role": "user", "content": "Привет!"}],
    api_base="https://fb1.spb.ru:443/v1",
    api_key="athr_XXXXXXXX_..."
)
print(response.choices[0].message.content)
```

> 💡 **Ключевой принцип:** В любом OpenAI-совместимом клиенте укажите:
> - `api_key` (или `OPENAI_API_KEY`) = `"athr_XXXXXXXX_..."`
> - `base_url` (или `OPENAI_BASE_URL`) = `"https://fb1.spb.ru:443/v1"`
> - `model` = `"qwen-14b"` (MODEL_A) или `"qwen-32b-base"` (MODEL_B)

---

## Таймауты

### Рекомендуемые значения

| Сценарий | Таймаут | Пояснение |
|---|---|---|
| **Быстрый ответ** (до 100 токенов) | 30 с | Приветствия, короткие ответы |
| **Обычный ответ** (до 500 токенов) | 60–120 с | Типичный диалог агента |
| **Длинный ответ** (до 2048 токенов) | 180–300 с | Генерация кода, большие тексты |
| **Проверка соединения** (`/v1/models`) | 10 с | Быстрый health-check |

### Настройка таймаута в Python

```python
# Библиотека openai
from openai import OpenAI

client = OpenAI(
    api_key="athr_XXXXXXXX_...",
    base_url="https://fb1.spb.ru:443/v1",
    timeout=120.0,          # общий таймаут в секундах (float)
    max_retries=2            # автоматические повторы при ошибках
)

# Таймаут на уровне запроса (переопределяет клиентский)
response = client.chat.completions.create(
    model="qwen-14b",
    messages=[{"role": "user", "content": "Привет!"}],
    timeout=60.0
)
```

```python
# Библиотека requests
import requests

response = requests.post(
    "https://fb1.spb.ru:443/v1/chat/completions",
    headers={"Authorization": "Bearer athr_XXXXXXXX_..."},
    json={"model": "qwen-14b", "messages": [{"role": "user", "content": "Привет!"}]},
    timeout=(10, 120)        # (connect_timeout, read_timeout) в секундах
)
```

### Настройка таймаута в curl

```bash
curl --max-time 120 \       # общий таймаут в секундах
     --connect-timeout 10 \ # таймаут соединения
     https://fb1.spb.ru:443/v1/chat/completions \
     -H "Authorization: Bearer athr_XXXXXXXX_..." \
     -H "Content-Type: application/json" \
     -d '{"model":"qwen-14b","messages":[{"role":"user","content":"Привет!"}]}'
```

### Настройка таймаута в Hermes Agent

```bash
# Глобальный таймаут для провайдера (в секундах)
hermes config set provider.aither.timeout 120
```

---

## Повтор запросов (retry)

### Стратегия retry

При сбоях рекомендуется использовать **экспоненциальную задержку с джиттером**:

| Попытка | Задержка | Комулятивное время |
|---|---|---|
| 1 (исходный запрос) | — | — |
| 2 (первый повтор) | ~1–2 с | ~2 с |
| 3 (второй повтор) | ~2–4 с | ~6 с |
| 4 (третий повтор) | ~4–8 с | ~14 с |

> 💡 **Рекомендуемое количество повторов:** 2–3. Не более 5 — при систематических сбоях дальнейшие попытки бессмысленны.

### Когда повторять

| Код | Действие |
|---|---|
| **429** (Rate Limit) | Повторить через `Retry-After` (обычно 60 с) |
| **500** (Internal Server Error) | Повтор через экспоненциальную задержку |
| **502** (Bad Gateway) | Повтор через экспоненциальную задержку |
| **503** (Service Unavailable) | Повтор через экспоненциальную задержку |
| **504** (Gateway Timeout) | Повтор через экспоненциальную задержку |
| **Таймаут соединения** | Повтор через экспоненциальную задержку (проверить сеть) |

### Когда НЕ повторять

| Код | Действие |
|---|---|
| **401** (Unauthorized) | ❌ Не повторять — ключ недействителен |
| **403** (Forbidden) | ❌ Не повторять — доступ запрещён |
| **404** (Not Found) | ❌ Не повторять — ресурс не существует |
| **422** (Unprocessable) | ❌ Не повторять — неверный формат запроса |

### Готовый retry-декоратор (Python)

```python
import time
import random
import functools

def retry_on_server_error(max_retries=3, base_delay=1.0):
    """Декоратор: повтор при 429, 5xx и таймаутах."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    status = getattr(result, 'status_code', None)
                    if status == 429:
                        wait = 60 + random.uniform(0, 5)
                        print(f"[retry] Rate limit (429), ожидание {wait:.0f}с...")
                    elif status and status >= 500:
                        wait = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        print(f"[retry] Ошибка сервера ({status}), попытка {attempt+1}/{max_retries+1}, ожидание {wait:.1f}с...")
                    elif status == 200:
                        return result
                    else:
                        return result   # 4xx — не повторяем
                    if attempt < max_retries:
                        time.sleep(wait)
                    else:
                        return result
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        print(f"[retry] {type(e).__name__}: {e}, попытка {attempt+1}/{max_retries+1}, ожидание {wait:.1f}с...")
                        time.sleep(wait)
            raise last_exception
        return wrapper
    return decorator
```

---

## Примечания по TLS

### Internet-зона (`https://fb1.spb.ru:443`)

| Параметр | Значение |
|---|---|
| **Сертификат** | Let's Encrypt (доверенный) |
| **Проверка сертификата** | Включена по умолчанию |
| **Флаг `-k` в curl** | ❌ Не требуется |
| **`verify=False` в Python** | ❌ Не требуется (и опасно!) |

### Test Zone (`http://10.129.13.78:30080`)

| Параметр | Значение |
|---|---|
| **Протокол** | HTTP (без шифрования) |
| **TLS** | Отсутствует |
| **Использование** | Только во внутренней сети / через VPN |

> ⚠️ **НИКОГДА не отключайте проверку сертификатов** (`verify=False`, `-k`) для Internet-зоны. Если вы получаете ошибку сертификата:
> 1. Проверьте системное время (`date`) — расхождение >5 мин ломает проверку.
> 2. Убедитесь, что корневые сертификаты обновлены.
> 3. Проверьте URL — возможно, вы ошибочно используете `http://` вместо `https://`.

### Обновление системных сертификатов

```bash
# Debian / Ubuntu / Astra Linux
apt update && apt install -y ca-certificates

# RHEL / CentOS / RED OS
dnf update -y ca-certificates
```

---

## Правила хранения секретов

### ✅ Правильно

| Метод | Пример |
|---|---|
| **Переменная окружения** | `export AITHER_API_KEY="athr_XXXXXXXX_..."` |
| **Файл `.env` (вне Git)** | `echo 'AITHER_API_KEY=athr_...' > .env` + `.env` в `.gitignore` |
| **Менеджер паролей** | KeePass, Bitwarden, HashiCorp Vault |
| **Файл с правами 600** | `echo "athr_..." > ~/.aither-key && chmod 600 ~/.aither-key` |
| **systemd-credentials** | `LoadCredential=aither-api-key:/etc/aither/key` |

### ❌ Неправильно

| Метод | Почему плохо |
|---|---|
| **Хардкодить в исходном коде** | Попадёт в Git, виден всем с доступом к репозиторию |
| **Коммитить в Git** | Останется в истории навсегда |
| **Публиковать в скриншотах** | Ключ виден всем |
| **Передавать в мессенджерах** | Может быть перехвачен / сохранён в логах |
| **Один ключ на всё** | При компрометации пострадают все агенты и скрипты |

### Если ключ попал в Git

```bash
# 1. Немедленно отзовите ключ в Web UI (раздел 🔑 API Ключи)
# 2. Создайте новый ключ
# 3. Удалите ключ из истории (если возможно):
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all
# 4. Или используйте BFG Repo-Cleaner:
#    bfg --delete-files .env
```

### Рекомендации по организации ключей

| Тип использования | Стратегия |
|---|---|
| **AI-агент (разработка)** | Отдельный ключ на каждого агента |
| **Автоматизация (cron-задачи)** | Отдельный ключ с читаемым именем |
| **Разовое тестирование** | Создать и отозвать сразу после |
| **Продакшн** | Отдельный ключ, регулярная ротация |

---

## Процедура отзыва ключа

### Через Web UI

1. Войдите в Web UI: `https://fb1.spb.ru:443/`
2. Перейдите в раздел **🔑 API Ключи**.
3. Найдите нужный ключ по названию или префиксу (`athr_XXXXXXXX`).
4. Нажмите **«Отозвать»**.
5. Подтвердите действие.

### Что происходит после отзыва

- Ключ **немедленно** становится недействительным.
- Все запросы с этим ключом начинают возвращать **HTTP 401**.
- Статус ключа в таблице меняется на «Отозван».
- Восстановить отозванный ключ **нельзя**.

### Когда отзывать ключ

- ✅ Ключ был случайно опубликован (GitHub, чат, скриншот).
- ✅ Ключ потерян (не сохранили при создании).
- ✅ Ключ больше не нужен (агент отключён, проект завершён).
- ✅ Подозрение на компрометацию (необычная активность).
- ✅ Плановая ротация ключей.

### Через BFF API (автоматизация)

```bash
curl -X DELETE https://fb1.spb.ru:443/api/v1/tokens/athr_XXXXXXXX \
  -H "Authorization: Bearer athr_YYYYYYYY_..."
```

> ⚠️ Для отзыва через API требуется **другой** действующий ключ.

---

## Диагностика ошибок

### HTTP 401 — Unauthorized

**Симптом:** `{"detail": "Valid API Key required (format: athr_...)"}`

| Причина | Решение |
|---|---|
| Ключ отозван | Проверьте статус в Web UI (🔑 API Ключи), создайте новый |
| Опечатка в ключе | Сверьте ключ с сохранённой копией |
| Неверный формат заголовка | Должно быть: `Authorization: Bearer athr_...` (не `bearer`, не `"athr_..."`) |
| Лишние пробелы | Проверьте, нет ли пробелов в начале/конце ключа |
| Ключ перепутан | Убедитесь, что используется Aither-ключ (`athr_...`), а не ключ другого сервиса |
| Просрочен ключ | API-ключи Aither не имеют срока действия, но могут быть отозваны |

**Проверка в curl:**
```bash
# Корректный запрос (должен вернуть 200)
curl -s -o /dev/null -w "%{http_code}" \
  https://fb1.spb.ru:443/v1/models \
  -H "Authorization: Bearer athr_XXXXXXXX_..."
# Ожидаемый вывод: 200

# Запрос БЕЗ ключа (должен вернуть 401)
curl -s -o /dev/null -w "%{http_code}" \
  https://fb1.spb.ru:443/v1/models
# Ожидаемый вывод: 401
```

---

### HTTP 403 — Forbidden

**Симптом:** доступ запрещён, несмотря на валидный ключ.

| Причина | Решение |
|---|---|
| Ключ не имеет доступа к запрошенной модели | При создании ключа выбраны не все модели. Отзовите ключ и создайте новый с доступом к обеим моделям |
| Попытка доступа к административному эндпоинту | API-ключи пользователей дают доступ только к `/v1/chat/completions` и `/v1/models` |
| Ключ заблокирован администратором | Свяжитесь с владельцем платформы |

---

### HTTP 404 — Not Found

**Симптом:** `{"detail": "Not Found"}` или пустой ответ.

| Причина | Решение |
|---|---|
| Неверный путь API | Путь должен быть `/v1/chat/completions` (не `/v1/chat`, не `/api/v1/...`) |
| Опечатка в URL | Проверьте полный URL: `https://fb1.spb.ru:443/v1/chat/completions` |
| Неверный метод HTTP | Должен быть `POST` для `/v1/chat/completions`, `GET` для `/v1/models` |
| Модель не найдена | Проверьте имя модели: `qwen-14b` или `qwen-32b-base` (без лишних символов) |

**Проверка в curl:**
```bash
# Правильный путь
curl -s -o /dev/null -w "%{http_code}" \
  https://fb1.spb.ru:443/v1/models \
  -H "Authorization: Bearer athr_XXXXXXXX_..."
# Ожидаемый вывод: 200

# Неправильный путь
curl -s -o /dev/null -w "%{http_code}" \
  https://fb1.spb.ru:443/api/v1/models \
  -H "Authorization: Bearer athr_XXXXXXXX_..."
# Ожидаемый вывод: 404
```

---

### HTTP 429 — Too Many Requests (Rate Limit)

**Симптом:** `{"detail": "Rate limit exceeded"}` или `429 Too Many Requests`.

| Причина | Решение |
|---|---|
| Превышен лимит 300 запросов/минуту | Подождите 60 с и повторите. Используйте заголовок `Retry-After` |
| Много одновременных запросов к MODEL_A | Модель 14B обслуживает ~4 одновременных запроса. Отправляйте запросы последовательно или с задержкой |
| Несколько агентов работают одновременно | Координируйте запуск агентов, добавьте задержки между запросами |

**Рекомендации по снижению нагрузки:**
```python
import time

# Задержка между запросами
time.sleep(0.5)  # минимум 200 мс между запросами

# Очередь с семафором для ограничения параллелизма
import asyncio
semaphore = asyncio.Semaphore(2)  # не более 2 одновременных запросов

async def call_model(messages):
    async with semaphore:
        # ... запрос к Aither ...
```

---

### HTTP 5xx — Ошибка сервера

**Симптом:** `500 Internal Server Error`, `502 Bad Gateway`, `503 Service Unavailable`, `504 Gateway Timeout`.

| Код | Вероятная причина | Решение |
|---|---|---|
| **500** | Внутренняя ошибка сервера (сбой vLLM, ошибка Gateway) | Повторить через 2–4 с. Если повторяется — сообщить администратору |
| **502** | Gateway не может достучаться до vLLM-пода | Повторить через 2–4 с. Вероятно, временный сбой |
| **503** | Сервис временно недоступен (перезапуск, обслуживание) | Подождать 30–60 с, повторить. Проверить статус системы |
| **504** | Модель не ответила вовремя (длинный запрос, высокая нагрузка) | Уменьшить `max_tokens`, разбить запрос на несколько, повторить |

**Алгоритм обработки 5xx:**
```python
import time
import random

def call_with_retry(payload, max_retries=3):
    for attempt in range(max_retries):
        response = requests.post(..., json=payload, timeout=120)
        if response.status_code == 200:
            return response.json()
        if response.status_code == 429:
            time.sleep(60 + random.uniform(0, 5))
        elif response.status_code >= 500:
            wait = (2 ** attempt) + random.uniform(0, 1)
            print(f"5xx ({response.status_code}), повтор через {wait:.1f}с...")
            time.sleep(wait)
        else:
            # 4xx — не повторяем
            raise Exception(f"Клиентская ошибка: {response.status_code} {response.text}")
    raise Exception("Исчерпаны попытки")
```

---

### Таймаут (Timeout)

**Симптом:** запрос не завершается в течение ожидаемого времени.

| Причина | Решение |
|---|---|
| Модель перегружена (очередь GPU) | Подождать 10–30 с, повторить. Рассмотреть переход на другую модель |
| Слишком большой `max_tokens` | Уменьшите `max_tokens` до 500–1000. Разбейте задачу на несколько запросов |
| Проблемы сети | Проверьте соединение: `ping fb1.spb.ru` (Internet) или `ping 10.129.13.78` (Test Zone) |
| Слишком маленький таймаут на клиенте | Увеличьте таймаут: минимум 60 с для обычных запросов, 180 с для длинных |
| Модель «зависла» | Остановите запрос (Ctrl+C), подождите 10 с, проверьте `/v1/models`, повторите |

**Проверка сетевой связности:**
```bash
# Internet-зона
curl -s -o /dev/null -w "HTTP %{http_code}, время: %{time_total}с\n" \
  --max-time 10 \
  https://fb1.spb.ru:443/v1/models \
  -H "Authorization: Bearer athr_XXXXXXXX_..."

# Test Zone
curl -s -o /dev/null -w "HTTP %{http_code}, время: %{time_total}с\n" \
  --max-time 10 \
  http://10.129.13.78:30080/v1/models \
  -H "Authorization: Bearer athr_XXXXXXXX_..."
```

---

### Сводная таблица кодов

| Код | Значение | Повторять? | Стратегия |
|---|---|---|---|
| **200** | Успех | — | Обработать ответ |
| **401** | Ошибка аутентификации | ❌ Нет | Проверить ключ, формат заголовка |
| **403** | Доступ запрещён | ❌ Нет | Проверить права ключа на модели |
| **404** | Не найдено | ❌ Нет | Проверить URL и `model` |
| **422** | Неверный формат | ❌ Нет | Проверить JSON запроса |
| **429** | Rate limit | ✅ Да | `Retry-After`, не более 3 раз |
| **500** | Внутренняя ошибка | ✅ Да | Экспоненциальная задержка, 2–3 раза |
| **502** | Bad Gateway | ✅ Да | Экспоненциальная задержка, 2–3 раза |
| **503** | Сервис недоступен | ✅ Да | Задержка 30–60 с, 2–3 раза |
| **504** | Таймаут шлюза | ✅ Да | Уменьшить запрос, повторить 1–2 раза |
| **Таймаут** | Нет ответа | ✅ Да | Увеличить таймаут, проверить сеть |

---

## Связанные документы

- [API KEY USER GUIDE](../user-package/14_API_KEY_USER_GUIDE.md) — создание и управление ключами
- [API GUIDE](../user-package/04_API_GUIDE.md) — полное описание API
- [WEB UI GUIDE](../user-package/13_WEB_UI_GUIDE.md) — основной интерфейс
- [DUAL ZONE ACCESS GUIDE](../user-package/15_DUAL_ZONE_ACCESS_GUIDE.md) — Internet vs Test Zone
- [SECURITY RULES](../user-package/09_SECURITY_RULES.md) — безопасность агентов и ключей
- [KNOWN LIMITATIONS](../user-package/10_KNOWN_LIMITATIONS.md) — ограничения системы
- [AI AGENT CONNECTION PRIMER](../user-package/16_AI_AGENT_CONNECTION_PRIMER.md) — краткое руководство по агентам
