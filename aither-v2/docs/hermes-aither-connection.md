# Инструкция: подключение Aither к Hermes Agent

## Краткий вердикт

| Аспект | Статус |
|---|---|
| Чат с моделями qwen-14b / qwen-32b-base | ✅ Возможно |
| Tool calling (function calling) | ❌ Модели не поддерживают |
| Прямое подключение без адаптера | ❌ Несовместимые эндпоинты |
| Подключение через локальный прокси | ✅ Практично |

**Главное ограничение:** Hermes Agent требует tool calling для файловых операций, терминала, поиска — а Qwen-модели Aither этого не умеют. Поэтому Aither можно использовать только как **вспомогательный чат-провайдер**, но не как основной движок Hermes.

---

## Архитектура Aither

```
Пользователь → fb1.spb.ru:10443 (nginx/VPS)
                 ├── /api/v1/chat     → Portal Backend → vLLM (qwen-14b / qwen-32b-base)
                 ├── /api/v1/auth/*   → Portal Backend → Identity (JWT-сессии)
                 ├── /api/v1/api-keys → Portal Backend → AI Platform (API-ключи)
                 └── /v1/identity/*   → Identity (напрямую)
```

**Ключевое различие:**
- **API-ключ** (`aither_82c28ede_...`) — для Gateway/AI Platform, генерируется в ЛК
- **JWT-токен** — для чата, получается через `/api/v1/auth/login`

API-ключ **нельзя** напрямую использовать как Bearer-токен для чата — эндпоинт `/api/v1/chat` требует JWT.

---

## Способ 1: Локальный прокси-адаптер (рекомендуемый)

Hermes ожидает OpenAI-совместимый эндпоинт `/v1/chat/completions`, а Aither отдаёт чат на `/api/v1/chat`. Прокси решает несовпадение путей и вопрос с SSL.

### Шаг 1. Создать прокси-скрипт

```python
# ~/aither-proxy.py
"""
Aither → Hermes adapter proxy.
Translates OpenAI-standard /v1/chat/completions → Aither /api/v1/chat.
"""
from flask import Flask, request, Response
import httpx
import json

app = Flask(__name__)

AITHER_URL = "https://fb1.spb.ru:10443"
AITHER_JWT = "ВАШ_JWT_ТОКЕН"  # ← заменить после получения (Шаг 2)

@app.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    body = request.get_json(force=True)
    with httpx.Client(base_url=AITHER_URL, verify=False, timeout=120.0) as client:
        resp = client.post(
            "/api/v1/chat",
            json={
                "model": body.get("model", "qwen-14b"),
                "messages": body.get("messages", []),
                "max_tokens": body.get("max_tokens", 512),
                "temperature": body.get("temperature", 0.7),
            },
            headers={
                "Authorization": f"Bearer {AITHER_JWT}",
                "Content-Type": "application/json",
            },
        )
    return Response(resp.content, status=resp.status_code, mimetype="application/json")

@app.route("/v1/models", methods=["GET"])
def list_models():
    """Return models Aither supports, in OpenAI format."""
    return {
        "object": "list",
        "data": [
            {"id": "qwen-14b", "object": "model"},
            {"id": "qwen-32b-base", "object": "model"},
        ],
    }

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=9999)
```

### Шаг 2. Получить JWT-токен

Замените `USERNAME` и `PASSWORD` на реальные учётные данные пользователя Aither:

```bash
curl -sk https://fb1.spb.ru:10443/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"YOUR_USERNAME","password":"YOUR_PASSWORD"}'
```

Ответ:
```json
{"token": "eyJ...JWT_TOKEN...", "user": {...}}
```

Скопируйте `token` и вставьте в `AITHER_JWT` в скрипте прокси.

### Шаг 3. Запустить прокси

```bash
pip install flask httpx
python3 ~/aither-proxy.py
```

Прокси слушает на `http://127.0.0.1:9999`.

### Шаг 4. Проверить

```bash
curl -s http://127.0.0.1:9999/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-14b","messages":[{"role":"user","content":"Привет! Кто ты?"}],"max_tokens":50}'
```

### Шаг 5. Настроить Hermes

```bash
hermes config set model.provider custom:aither
hermes config set model.model qwen-14b
hermes config set model.base_url http://127.0.0.1:9999/v1
hermes config set model.api_key noop
```

Или в `~/.hermes/config.yaml`:

```yaml
model:
  provider: custom:aither
  model: qwen-14b           # или qwen-32b-base
  base_url: http://127.0.0.1:9999/v1
  api_key: "noop"           # прокси сам подставляет JWT
```

### Шаг 6. Использовать

```bash
hermes chat -q "Привет!" --model qwen-14b --provider custom:aither
```

### Автозапуск прокси (systemd)

```ini
# ~/.config/systemd/user/aither-proxy.service
[Unit]
Description=Aither → Hermes Proxy

[Service]
ExecStart=/usr/bin/python3 %h/aither-proxy.py
Restart=on-failure

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now aither-proxy
```

---

## Способ 2: Прямое подключение (если Gateway Aither поддерживает OpenAI API)

Если в будущем Aither Gateway добавит прямую поддержку OpenAI-совместимого API с аутентификацией по API-ключу — можно подключиться без прокси:

```yaml
# ~/.hermes/config.yaml
model:
  provider: custom:aither
  model: qwen-14b
  base_url: https://fb1.spb.ru:10443/v1   # если Gateway будет на этом пути
  api_key: ${AITHER_API_KEY}
```

```bash
# ~/.hermes/.env
AITHER_API_KEY=aither_82c28ede_Cq9SJZnGjCiTNAC5xrjGrsNGYAp1L5GUe0BTVDqjQY7zJIho1yF2bAG8jO-wS9l5
```

На текущий момент этот способ **не работает** — Gateway не принимает API-ключ как Bearer-токен для чата.

---

## Доступные модели

| model | Тип | max_tokens | Примечание |
|---|---|---|---|
| `qwen-14b` | Instruct / чат | ~8192 | Нативный chat completions |
| `qwen-32b-base` | Completion-only | ~8192 | BFF авто-конвертирует chat → completion |

---

## SSL-сертификат

Aither использует самоподписанный сертификат на `fb1.spb.ru:10443`. Прокси (Способ 1) автоматически отключает проверку (`verify=False`). При прямом подключении (Способ 2) потребуется `verify: false` в конфигурации провайдера или добавление сертификата в доверенные.

---

## Важно: tool calling не работает

Hermes Agent использует OpenAI function calling для вызова инструментов (terminal, file, browser, web_search). Qwen-модели Aither **не обучены function calling** — они вернут обычный текст, а не structured tool call.

**Последствия:**
- Hermes **не сможет** выполнять команды, читать/писать файлы, искать в интернете
- Работает только **простой чат** (вопрос-ответ)
- Для полноценной работы Hermes должен использовать модель с поддержкой tool calling (DeepSeek, GPT-4, Claude)

**Рекомендация:** использовать Aither как дополнительный чат-провайдер (быстрые вопросы), а основным оставить DeepSeek (текущая модель `deepseek-v4-pro`).
