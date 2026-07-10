# Каталог моделей и балансировка нагрузки

> Статус: реализовано  
> Дата: 8 июля 2026  
> Репозиторий: `aither-project`  
> Компоненты: `gateway/catalog.py`, `gateway/catalog.yaml`, `gateway/gateway.py`, `portal/server.ts`, `portal/static/index.html`

---

## 1. Архитектура

```
Запрос: model="qwen2.5-32b"
        │
        ▼
┌──────────────────────────────────────────────┐
│                  GATEWAY                      │
│                                               │
│  ┌─────────────┐     ┌──────────────────┐    │
│  │  catalog.py  │────→│  catalog.yaml    │    │
│  │  resolve()   │     │  (реестр моделей) │    │
│  └──────┬──────┘     └──────────────────┘    │
│         │                                     │
│         │ backend_url + model_path            │
│         ▼                                     │
│  ┌──────────────────────────────────────┐    │
│  │           ROUTER                      │    │
│  │                                      │    │
│  │  qwen2.5-14b → http://vllm:8000      │    │
│  │  qwen2.5-32b → http://vllm-32b:8000  │    │
│  └──────────────────────────────────────┘    │
│                                               │
└──────────────────┬───────────────────────────┘
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
┌─────────────────┐  ┌──────────────────┐
│ vLLM 14B (n8)   │  │ vLLM 32B (n7)    │
│ Qwen2.5-14B     │  │ Qwen2.5-32B-GPTQ │
│ 2×RTX6000       │  │ 2×RTX6000        │
└─────────────────┘  └──────────────────┘
```

## 2. Компоненты

### 2.1 `catalog.yaml` — реестр моделей

```yaml
models:
  - name: qwen2.5-14b
    display_name: "Qwen 2.5 14B"
    backend: "http://vllm:8000"          # ← URL vLLM-пода
    model_path: "/models/Qwen2.5-14B-Instruct"
    max_tokens: 4096
    description: "Быстрая универсальная модель"
    tokens_per_ruble: 100                # ← цена
    tags: [chat, code, fast]
    status: active

  - name: qwen2.5-32b
    display_name: "Qwen 2.5 32B"
    backend: "http://vllm-32b:8000"
    model_path: "/models/Qwen2.5-32B-Instruct-GPTQ"
    max_tokens: 8192
    description: "Мощная модель для сложных задач"
    tokens_per_ruble: 30
    tags: [code, analysis, large-context]
    status: active
```

**Поля модели:**

| Поле | Тип | Описание |
|---|---|---|
| `name` | string | ID модели в API (используется в `model` при запросе) |
| `display_name` | string | Человеческое имя (показывается в интерфейсе) |
| `backend` | url | URL vLLM-пода (внутри кластера K8s) |
| `model_path` | path | Путь к модели на диске внутри пода |
| `max_tokens` | int | Максимальная длина вывода |
| `tokens_per_ruble` | int | Сколько токенов даёт 1 ₽ |
| `tags` | []string | Теги для UI-фильтрации |
| `status` | active/inactive | Если `inactive` — не загружается |

### 2.2 `catalog.py` — загрузчик и роутер

**Функции:**

| Функция | Назначение |
|---|---|
| `load_catalog()` | Загружает `catalog.yaml` → словарь `{name: entry}` |
| `list_models()` | Возвращает публичный список моделей (без внутренних полей) |
| `resolve(name)` | Ищет модель по имени → `(backend_url, model_path, error)` |
| `health_check(url)` | Проверяет `/health` на vLLM-бэкенде (кэш 30 сек) |
| `health_summary()` | Сводка здоровья всех бэкендов |

**Алгоритм `resolve()`:**

1. Точное совпадение: `model_name == entry.name`
2. Нечёткое: `model_name.lower() in entry.name.lower()`
3. По умолчанию: первая активная модель

### 2.3 Gateway — изменения

**Старый код (дни 1–8):**

```python
# Жёстко зашитая маршрутизация
if "saiga" in model.lower():
    self.vllm_url = VLLM_SAIGA_URL
    req_data["model"] = "/models/saiga_llama3_8b"
else:
    self.vllm_url = VLLM_URL
    req_data["model"] = "/models/Qwen2.5-14B-Instruct"
```

**Новый код (день 9):**

```python
# Динамическая маршрутизация через каталог
from catalog import list_models, resolve

backend_url, model_path, err = resolve(model)
if err:
    return 400 {"error": "unknown_model", "available": [...]}

self.vllm_url = backend_url
req_data["model"] = model_path
```

**Новые эндпоинты:**

| Эндпоинт | Ответ |
|---|---|
| `GET /v1/models` | Список моделей из каталога |
| `GET /v1/models/health` | Статус всех vLLM-бэкендов |

### 2.4 Портал — изменения

**BFF:**

```typescript
// Новый прокси-эндпоинт
app.get("/api/v1/models", async (_r, reply) => {
    const r = await fetch(CORE_API + "/v1/models");
    return reply.send(await r.json());
});
```

**Фронтенд:**

```javascript
// Состояние
state.availableModels = [];  // динамический список моделей

// Загрузка при открытии дашборда
const modelsR = await api('/api/v1/models');
state.availableModels = modelsR.data.data;

// Динамический выпадающий список
<select onchange="onChatModelChange(this.value)">
  ${state.availableModels.map(m => 
    `<option value="${m.id}">${m.display_name}</option>`
  ).join('')}
</select>
```

---

## 3. Добавление новой модели

Пошаговая инструкция:

### Шаг 1: Развернуть vLLM-под

```yaml
# manifests/vllm-new-model.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-new-model
spec:
  template:
    spec:
      runtimeClassName: nvidia
      nodeSelector:
        kubernetes.io/hostname: bootsman-k8s-clnt01-n7-gpu  # целевой узел
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        command: ["python3", "-m", "vllm.entrypoints.openai.api_server"]
        args:
          - "--model"
          - "/models/NewModel-7B"       # путь к модели
          - "--dtype"
          - "half"
          - "--max-model-len"
          - "4096"
        resources:
          limits:
            nvidia.com/gpu: "1"
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-new-model       # ← имя сервиса = backend URL
spec:
  selector:
    app: vllm-new-model
  ports:
  - port: 8000
```

```bash
kubectl apply -f manifests/vllm-new-model.yaml
```

### Шаг 2: Прописать модель в каталог

```yaml
# gateway/catalog.yaml — добавить:
  - name: new-model-7b
    display_name: "NewModel 7B"
    backend: "http://vllm-new-model:8000"    # ← имя K8s-сервиса
    model_path: "/models/NewModel-7B"
    max_tokens: 4096
    tokens_per_ruble: 200
    tags: [chat]
    status: active
```

### Шаг 3: Обновить Gateway

```bash
# Обновить ConfigMap с catalog.yaml
kubectl create configmap gateway-catalog --from-file=catalog.yaml=gateway/catalog.yaml \
  --dry-run=client -o yaml | kubectl apply -f -

# Перезапустить Gateway
kubectl rollout restart deployment/gateway
```

### Шаг 4: Проверить

```bash
# Модель появилась в каталоге?
curl http://<gateway>/v1/models | jq '.data[].id'

# Запрос к новой модели
curl -X POST http://<gateway>/v1/chat/completions \
  -H "Authorization: Bearer <delegation-token>" \
  -H "Content-Type: application/json" \
  -d '{"model":"new-model-7b","messages":[{"role":"user","content":"Привет!"}]}'
```

---

## 4. Балансировка нагрузки

### 4.1 Текущий механизм

Маршрутизация **по имени модели** (model-based routing):

- Клиент указывает `model: "qwen2.5-14b"` → запрос идёт на `http://vllm:8000`
- Клиент указывает `model: "qwen2.5-32b"` → запрос идёт на `http://vllm-32b:8000`

Это **не** round-robin балансировка — каждая модель привязана к конкретному vLLM-поду.

### 4.2 Когда нужно масштабировать

Если одной модели нужно несколько реплик (высокая нагрузка):

```yaml
# Увеличить количество реплик
spec:
  replicas: 3  # было 1
```

K8s автоматически распределит запросы между подами через `Service` (round-robin на уровне iptables).

### 4.3 Health Check

Gateway кэширует статус бэкендов на 30 секунд:

```python
def health_check(backend_url: str) -> bool:
    # Проверяет GET <backend>/health
    # Кэш: HEALTH_TTL = 30 сек
```

Доступно через API:

```bash
curl http://<gateway>/v1/models/health
```

Ответ:

```json
{
  "object": "health",
  "backends": {
    "qwen2.5-14b": {"backend": "http://vllm:8000", "alive": true},
    "qwen2.5-32b": {"backend": "http://vllm-32b:8000", "alive": true}
  }
}
```

---

## 5. Ценообразование (tokens_per_ruble)

Каждая модель имеет свою цену:

| Модель | Токенов за 1 ₽ | ~300 слов | ~1000 слов |
|---|---|---|---|
| Qwen 2.5 14B | 100 | 3 ₽ | 10 ₽ |
| Qwen 2.5 32B | 30 | 10 ₽ | 33 ₽ |

Цена настраивается в `catalog.yaml` → `tokens_per_ruble`.

Расчёт резерва перед запросом (в gateway.py):

```python
reserve_amount = (max_tokens + input_tokens) * TOKEN_COST
```

Где `TOKEN_COST` — из переменной окружения (по умолчанию 1, можно переопределить).

---

## 6. Развёртывание

### 6.1 K8s ConfigMap + Deployment

```yaml
# manifests/gateway-catalog.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: gateway-catalog
data:
  catalog.yaml: |
    models:
      - name: qwen2.5-14b
        display_name: "Qwen 2.5 14B"
        backend: "http://vllm:8000"
        model_path: "/models/Qwen2.5-14B-Instruct"
        max_tokens: 4096
        tokens_per_ruble: 100
        tags: [chat, code, fast]
        status: active
      - name: qwen2.5-32b
        display_name: "Qwen 2.5 32B"
        backend: "http://vllm-32b:8000"
        model_path: "/models/Qwen2.5-32B-Instruct-GPTQ"
        max_tokens: 8192
        tokens_per_ruble: 30
        tags: [code, analysis, large-context]
        status: active
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gateway
spec:
  template:
    spec:
      containers:
      - name: gateway
        volumeMounts:
        - name: catalog
          mountPath: /app/catalog.yaml
          subPath: catalog.yaml
        env:
        - name: CATALOG_PATH
          value: "/app/catalog.yaml"
      volumes:
      - name: catalog
        configMap:
          name: gateway-catalog
```

```bash
kubectl apply -f manifests/gateway-catalog.yaml
kubectl rollout restart deployment/gateway
```

### 6.2 Портал (VPS2)

```bash
# Пересобрать BFF
cd portal && npx tsc

# Залить на VPS2
scp dist/server.js root@130.17.1.90:/root/aither-project/portal/dist/
scp static/index.html root@130.17.1.90:/root/aither-project/portal/static/

# Перезапустить
ssh root@130.17.1.90 'kill $(pgrep -f "node.*server"); cd /root/aither-project/portal && node dist/server.js &>/tmp/portal.log & disown'
```

---

## 7. Тестирование

### 7.1 Каталог моделей

```bash
# Через BFF (портал)
curl http://130.17.1.90/api/v1/models

# Через Gateway напрямую
curl http://10.129.13.78:32293/v1/models
```

### 7.2 Маршрутизация

```bash
# 32B модель
curl -X POST http://130.17.1.90/api/v1/chats/<chatId>/messages \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"content":"Напиши функцию быстрой сортировки","model":"qwen2.5-32b"}'
```

### 7.3 Health Check

```bash
curl http://10.129.13.78:32293/v1/models/health
```

---

## 8. Устранение неполадок

| Симптом | Причина | Решение |
|---|---|---|
| `unknown_model` | Модель не найдена в каталоге | Проверить `catalog.yaml`, перезапустить Gateway |
| Gateway возвращает пустой список моделей | `catalog.yaml` не смонтирован | Проверить `kubectl describe pod gateway-xxx` |
| `502 vllm_error` | vLLM-под не отвечает | `kubectl get pods \| grep vllm`, проверить логи |
| Портал показывает старые модели | `index.html` не обновлён | Очистить кэш браузера, перезалить `index.html` |
| Модель есть в каталоге, но нет в UI | BFF не может достучаться до Gateway | Проверить `CORE_API` в переменных окружения |
