# Usage Collector — подсистема учёта потребления токенов

## 1. Назначение и место в архитектуре

### Контекст

Usage Collector является компонентом **Gateway Aither** и обеспечивает точный учёт токенов, потреблённых каждым запросом к языковой модели. Подсистема находится на критическом пути обработки запроса:

```
Клиент → Портал → Gateway → [Usage Collector] → vLLM → Gateway → [Usage Collector] → Клиент
```

### Решаемая проблема

Базовая версия Gateway использовала **предварительную оценку** токенов (`reserve_amount`) для биллинга. Это приводило к:
- Переоценке: клиент списывал больше токенов, чем реально потребил (до 30-40%)
- Неточной статистике: невозможно определить реальную нагрузку на инфраструктуру
- Отсутствию аналитики: нет данных для пост-оптимизации и отчётности

Usage Collector заменяет оценочный механизм на **точный подсчёт** на основе метаданных от инференс-сервера (vLLM).

### Требования

**Функциональные:**
- F1. Точный подсчёт потреблённых токенов (prompt + completion)
- F2. Сохранение детальной записи о каждом запросе в PostgreSQL
- F3. Предоставление агрегированной статистики через API
- F4. Корректная обработка ошибочных и прерванных запросов

**Нефункциональные:**
- NF1. Задержка не более 5 мс на операцию учёта (не влияет на latency запроса)
- NF2. Атомарность: биллинг и учёт либо оба фиксируются, либо оба откатываются
- NF3. Горизонт хранения: сырые записи — 90 дней, агрегаты — постоянно

---

## 2. Алгоритм работы

### 2.1 Основной цикл обработки запроса

```
Шаг 1. Аутентификация JWT → извлечение org_id
Шаг 2. Rate Limiter (RPM + TPM)
Шаг 3. Предварительная оценка токенов
Шаг 4. Резервирование средств (billing_op reserve)
Шаг 5. Отправка запроса в vLLM
Шаг 6. Получение ответа от vLLM
Шаг 7. Извлечение usage.total_tokens из ответа
        ├─ Успех: billing_op settle (фактические токены)
        │         → INSERT в usage_records (статус: success)
        └─ Ошибка: billing_op refund (полная сумма)
                   → INSERT в usage_records (статус: error)
Шаг 8. Возврат ответа клиенту
```

### 2.2 Извлечение метрик из ответа vLLM

vLLM возвращает метрики в формате OpenAI:

```json
{
  "id": "cmpl-abc123",
  "object": "chat.completion",
  "model": "/models/Qwen2.5-14B-Instruct",
  "usage": {
    "prompt_tokens": 128,
    "completion_tokens": 256,
    "total_tokens": 384
  },
  "choices": [...]
}
```

Gateway извлекает поля:

| Поле ответа vLLM | Поле в usage_records | Назначение |
|---|---|---|
| `usage.prompt_tokens` | `input_tokens` | Токены входящего сообщения |
| `usage.completion_tokens` | `output_tokens` | Токены ответа модели |
| `usage.total_tokens` | `total_tokens` | Сумма (основание для биллинга) |
| Время выполнения | `latency_ms` | Для мониторинга производительности |

### 2.3 Обработка краевых случаев

| Ситуация | Действие |
|---|---|
| vLLM вернул ответ без `usage` | Использовать `reserve_amount` как оценку (fallback) |
| vLLM вернул ошибку (status ≠ 200) | Refund резерва, запись со статусом `error` |
| PostgreSQL недоступен | Записать в лог, продолжить обслуживание (fail open) |
| Прерванное соединение клиента | vLLM всё равно завершает инференс → settle по факту |

---

## 3. Структуры данных

### 3.1 Таблица usage_records (PostgreSQL)

```sql
CREATE TABLE IF NOT EXISTS usage_records (
    id            SERIAL PRIMARY KEY,
    org_id        UUID NOT NULL,
    request_id    VARCHAR(8),          -- ссылка на billing_ledger.reference
    model         VARCHAR(64),         -- имя модели (qwen2.5-14b и др.)
    input_tokens  INTEGER NOT NULL,    -- prompt_tokens
    output_tokens INTEGER NOT NULL,    -- completion_tokens
    total_tokens  INTEGER NOT NULL,    -- сумма для биллинга
    status        VARCHAR(16) NOT NULL DEFAULT 'success',  -- success | error
    latency_ms    INTEGER,             -- время выполнения запроса в мс
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_usage_org_time ON usage_records (org_id, created_at DESC);
CREATE INDEX idx_usage_model     ON usage_records (model);
```

### 3.2 Ключи Redis (оперативный учёт)

| Ключ | Тип | TTL | Назначение |
|---|---|---|---|
| `usage:{org_id}:{date}` | counter | 48h | Счётчик запросов за день |
| `usage:tk:{org_id}:{date}` | counter | 48h | Сумма токенов за день |
| `rl:{org_id}:rpm:{window}` | counter | 120s | Rate limit: запросы в минуту |
| `rl:{org_id}:tpm:{window}` | counter | 120s | Rate limit: токены в минуту |

---

## 4. Схемы

### 4.1 Архитектура потока данных

```graphviz
digraph usage_collector_architecture {
    rankdir=TB;
    splines=ortho;
    nodesep=0.8;
    ranksep=1.0;
    fontname="Helvetica";
    labelloc="t";
    label="Usage Collector — архитектура потока данных";
    fontsize=16;
    
    node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10];
    edge [fontname="Helvetica", fontsize=9, color="#37474F", arrowsize=0.8];
    
    subgraph cluster_gateway {
        label="Gateway Aither";
        style="filled,rounded,dashed";
        fillcolor="#FFF3E0";
        color="#E65100";
        
        auth [label="JWT Auth\norg_id", fillcolor="#FFE0B2", color="#BF360C"];
        ratelimit [label="Rate Limiter\nRPM + TPM", fillcolor="#FFE0B2", color="#BF360C"];
        reserve [label="Billing Reserve\nbilling_op(reserve)", fillcolor="#FFE0B2", color="#BF360C"];
        proxy [label="Proxy to vLLM\nзамер latency", fillcolor="#FFE0B2", color="#BF360C"];
        collector [label="Usage Collector\nизвлечение usage\n+ INSERT record", fillcolor="#FFCC80", color="#E65100"];
        settle [label="Billing Settle\nbilling_op(settle)", fillcolor="#FFE0B2", color="#BF360C"];
        
        auth -> ratelimit -> reserve -> proxy -> collector -> settle;
    }
    
    subgraph cluster_storage {
        label="Хранилища";
        style="filled,rounded,dashed";
        fillcolor="#EDE7F6";
        color="#4527A0";
        
        pg [label="PostgreSQL\nusage_records\nbilling_ledger", fillcolor="#D1C4E9", color="#311B92"];
        redis [label="Redis\nсчётчики\nrate limits", fillcolor="#D1C4E9", color="#311B92"];
    }
    
    subgraph cluster_vllm {
        label="Инференс-сервер";
        style="filled,rounded,dashed";
        fillcolor="#FCE4EC";
        color="#C62828";
        
        vllm [label="vLLM\nQwen2.5-14B", fillcolor="#F8BBD0", color="#880E4F"];
    }
    
    proxy -> vllm [label="POST /v1/chat/completions", color="#1565C0"];
    vllm -> proxy [label="response\n+ usage.total_tokens", color="#2E7D32"];
    
    collector -> pg [label="INSERT", color="#4527A0"];
    collector -> redis [label="INCR usage:*", color="#4527A0"];
    settle -> pg [label="UPDATE billing", color="#4527A0"];
    reserve -> pg [label="UPDATE billing", color="#4527A0"];
    ratelimit -> redis [label="INCR rl:*", color="#4527A0"];
}
```

### 4.2 Конечный автомат обработки запроса

```graphviz
digraph usage_state_machine {
    rankdir=LR;
    splines=ortho;
    nodesep=0.6;
    ranksep=0.8;
    fontname="Helvetica";
    labelloc="t";
    label="Usage Collector — конечный автомат запроса";
    fontsize=16;
    
    node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=9];
    edge [fontname="Helvetica", fontsize=8, color="#37474F"];
    
    start [label="START", shape=circle, fillcolor="#C8E6C9", color="#2E7D32", width=0.5];
    auth_state [label="AUTH\nJWT verify", fillcolor="#BBDEFB", color="#0D47A1"];
    rl_state [label="RATE LIMIT\nRPM+TPM check", fillcolor="#BBDEFB", color="#0D47A1"];
    reserve_state [label="RESERVE\nbilling_op", fillcolor="#FFE0B2", color="#BF360C"];
    proxy_state [label="PROXY\n→ vLLM", fillcolor="#FFE0B2", color="#BF360C"];
    collect_state [label="COLLECT\nextract usage", fillcolor="#FFCC80", color="#E65100"];
    settle_state [label="SETTLE\nbilling + record", fillcolor="#C8E6C9", color="#2E7D32"];
    error_state [label="ERROR\nrefund + record", fillcolor="#F8BBD0", color="#C62828"];
    end_state [label="END", shape=circle, fillcolor="#C8E6C9", color="#2E7D32", width=0.5];
    
    # Error states
    auth_fail [label="401\nunauthorized", fillcolor="#F8BBD0", color="#C62828"];
    rl_fail [label="429\nrate limited", fillcolor="#F8BBD0", color="#C62828"];
    reserve_fail [label="402\nno balance", fillcolor="#F8BBD0", color="#C62828"];
    proxy_fail [label="502\nvLLM error", fillcolor="#F8BBD0", color="#C62828"];
    
    start -> auth_state;
    auth_state -> auth_fail [label="fail"];
    auth_state -> rl_state [label="ok"];
    rl_state -> rl_fail [label="exceeded"];
    rl_state -> reserve_state [label="ok"];
    reserve_state -> reserve_fail [label="insufficient"];
    reserve_state -> proxy_state [label="ok"];
    proxy_state -> proxy_fail [label="error"];
    proxy_state -> collect_state [label="ok"];
    collect_state -> settle_state [label="success"];
    collect_state -> error_state [label="error"];
    
    settle_state -> end_state;
    error_state -> end_state;
    auth_fail -> end_state;
    rl_fail -> end_state;
    reserve_fail -> end_state;
    proxy_fail -> end_state;
}
```

---

## 5. Интеграция

### 5.1 API-эндпоинты

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/v1/usage/` | Сводка: всего запросов, всего токенов, сегодня |
| GET | `/v1/usage/history?limit=N` | Детальная история транзакций (billing_ledger) |
| GET | `/v1/usage/stats?days=N` | NEW: агрегация usage_records по дням |

### 5.2 Зависимости

| Компонент | Тип зависимости | При отказе |
|---|---|---|
| PostgreSQL | Обязательная | Запись в лог, fail open |
| Redis | Оперативная | Счётчики today пропускаются |
| vLLM | Источник данных | usage = reserve_amount |

### 5.3 Конфигурация (env vars)

| Переменная | По умолчанию | Описание |
|---|---|---|
| `USAGE_RETENTION_DAYS` | 90 | Горизонт хранения usage_records |
| `PG_URL` | (из secret) | Строка подключения к PostgreSQL |

---

## 6. Безопасность

### Модель угроз

| Угроза | Вероятность | Влияние | Мера |
|---|---|---|---|
| Подделка usage в ответе vLLM | Низкая | Высокое | vLLM во внутренней сети |
| SQL-инъекция через model name | Низкая | Высокое | Параметризованные запросы |
| Переполнение usage_records | Средняя | Среднее | Автоочистка через 90 дней |
| Утечка org_id в логах | Средняя | Среднее | Маскирование в production |

---

## 7. Тестирование

### Методика

1. Отправить запрос с известным промптом через Gateway
2. Проверить, что в `usage_records` появилась запись
3. Сравнить `total_tokens` с ответом vLLM
4. Проверить агрегацию через `/v1/usage/stats`
5. Имитировать ошибку vLLM → проверить refund и status=error
