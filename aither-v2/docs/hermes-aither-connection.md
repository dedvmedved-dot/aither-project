# Hermes Agent — подключение к Aither

**Stages:** Stage 01 → 19+  
**Status:** CURRENT (обновлено 07.08.2026)  
**Applicable to:** Все конфигурации Aither после миграции Qwen2.5/Qwen3

---

## Обзор

Aither предоставляет два способа подключения Hermes Agent:

1. **Прямой доступ к vLLM** (через port-forward) — для администраторов с доступом к Kubernetes
2. **Через Aither Portal API** — для внешних пользователей через `athr_` API-ключ

---

## Текущие модели

| Display | Model ID | Scope | Эндпоинт |
|---------|----------|-------|----------|
| Qwen2.5-32B-Instruct-AWQ | `qwen2.5-32b-instruct` | `model:32b:chat` | `/v1/chat/completions` |
| Qwen3-32B-AWQ | `qwen3-32b` | `model:qwen3:chat` | `/v1/chat/completions` |

Обе модели — **чат/инструкционные**, поддерживают tool calling.

---

## Способ 1: Прямой доступ к vLLM (администратор)

### Port-forward

```bash
kubectl port-forward svc/vllm-32b-instruct-awq 9999:8000 -n aither-inference &
kubectl port-forward svc/vllm-qwen3-32b-awq 9998:8000 -n aither-inference &
```

> ⚠️ Operational example only. Not executed during repository-cleanup task.

### Hermes config

```yaml
model:
  max_tokens: 16000

compression:
  enabled: false

auxiliary:
  compression_provider: none

custom_providers:
  - name: aither-32b
    base_url: http://localhost:9999/v1
    api_key: "<VLLM_API_KEY>"
    model: qwen2.5-32b-instruct
    context_length: 65536
    max_tokens: 16000

  - name: aither-qwen3-32b
    base_url: http://localhost:9998/v1
    api_key: "<VLLM_API_KEY>"
    model: qwen3-32b
    context_length: 65536
    max_tokens: 16000
```

> `<VLLM_API_KEY>` — placeholder. Никаких реальных ключей.

### Запуск

```bash
hermes chat --provider custom:aither-32b --model qwen2.5-32b-instruct
hermes chat --provider custom:aither-qwen3-32b --model qwen3-32b
```

---

## Способ 2: Через Aither Portal API (внешний пользователь)

### Создание API-ключа

1. Войдите в портал: `https://fb1.spb.ru:10443`
2. Вкладка «🔑 API-ключи» → «Создать ключ»
3. Назначение: «AI Agent»
4. Модели: обе (или выберите нужную)
5. Сохраните ключ (формат: `athr_...`)

### Hermes config

```yaml
model:
  max_tokens: 16000

compression:
  enabled: false

custom_providers:
  - name: aither
    base_url: https://fb1.spb.ru:10443/v1
    api_key: "athr_..."   # ваш ключ из портала
    model: qwen3-32b      # или qwen2.5-32b-instruct
    max_tokens: 16000
```

### Запуск

```bash
hermes chat --provider custom:aither --model qwen3-32b
```

Не нужен kubectl и port-forward.

---

## Настройки Hermes

| Параметр | Значение | Статус |
|----------|---------|--------|
| `model.max_tokens` | `16000` | CURRENT REPORTED CONFIG |
| `compression.enabled` | `false` | CURRENT REPORTED CONFIG |
| `auxiliary.compression_provider` | `none` | CURRENT REPORTED CONFIG |
| `context_length` | `65536` | CURRENT REPORTED CONFIG |

> Это текущая рекомендованная конфигурация для работы с локальными vLLM-эндпоинтами Qwen2.5/Qwen3. Не является универсальной рекомендацией для всех моделей.

---

## Историческая архитектура

> **HISTORICAL DOCUMENT** — Architecture before Qwen2.5/Qwen3 migration.

```
До миграции:
├── vLLM 14B Instruct (N8) — qwen-14b, chat
├── vLLM 32B GPTQ (N7) — qwen-32b-base, completion-only
├── Completion adapter в Portal Backend для 32B
└── Gateway-nginx для 32B
```

После миграции обе модели — Instruct, обе используют native `/v1/chat/completions`.
