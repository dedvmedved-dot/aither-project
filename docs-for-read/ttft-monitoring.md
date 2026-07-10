# TTFT-мониторинг (#40)

**Дата:** 09.07.2026
**Статус:** ✅ Реализовано
**Компоненты:** Gateway (Python)

---

## Обзор

Prometheus-совместимый мониторинг производительности Gateway: Time To First Token (TTFT) per model, счётчики запросов/токенов/ошибок, активные соединения.

---

## Метрики

### `/metrics` — Prometheus scrape endpoint

| Метрика | Тип | Описание |
|---|---|---|
| `gateway_ttft_seconds` | histogram | TTFT per model (buckets: 0.1–60s) |
| `gateway_requests_total` | counter | Запросов: model, org_id, status |
| `gateway_tokens_total` | counter | Токенов: model, org_id, type |
| `gateway_billing_errors_total` | counter | Биллинг-ошибок: org_id, error |
| `gateway_drain_blocks_total` | counter | Блокировок по drain: model |
| `gateway_active_requests` | gauge | Активных запросов в данный момент |
| `gateway_uptime_seconds` | gauge | Аптайм процесса |

### `/admin/metrics` — JSON-сводка для человека

```json
{
  "active_requests": 2,
  "total_requests": 15234,
  "total_tokens": 8500000,
  "ttft_by_model": {
    "qwen2.5-14b": {
      "count": 12340,
      "avg_seconds": 1.234,
      "p50_seconds": 0.85,
      "p95_seconds": 3.2,
      "p99_seconds": 8.5
    },
    "qwen2.5-32b": {
      "count": 2894,
      "avg_seconds": 2.891,
      "p50_seconds": 2.1,
      "p95_seconds": 7.5,
      "p99_seconds": 18.3
    }
  }
}
```

---

## Как измеряется TTFT

```
t0: запрос поступает в Gateway
t1: Gateway отправляет запрос в vLLM
t2: vLLM возвращает ответ
TTFT = t2 - t1 (полное время ответа vLLM)
```

С non-streaming режимом измеряется полное время запроса (proxy round-trip). При внедрении streaming (SSE) можно измерять время до первого токена (`data:` чанка).

---

## Интеграция с Prometheus

Добавить в `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'aither-gateway'
    scrape_interval: 15s
    static_configs:
      - targets: ['gateway:8080']
    metrics_path: /metrics
```

---

## Файлы

| Файл | Описание |
|---|---|
| `gateway/metrics.py` | Класс Metrics: histogram, counters, gauge, Prometheus text renderer |
| `gateway/gateway.py` | Интеграция: /metrics, /admin/metrics, TTFT timing, счётчики |

---

## Следующие шаги

- 🔲 Prometheus AlertManager: P95 > 5s → алерт
- 🔲 Streaming TTFT (SSE — время до первого токена)
- 🔲 Per-user метрики (сейчас per-org)
- 🔲 Grafana dashboard
