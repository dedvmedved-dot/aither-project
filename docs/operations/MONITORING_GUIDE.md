# Aither AI Platform — Руководство по мониторингу

**Версия:** OPS-01-R2 | **Дата:** 26 июля 2026
**Статус:** 🟡 Ручной мониторинг (автоматизированный не развёрнут)

---

## Monitoring Inventory — инвентаризация

### ✅ Реализовано и доступно

| Компонент | Статус | Примечание |
|-----------|--------|------------|
| Health endpoints сервисов | ✅ Работает | HTTP GET /health на каждом сервисе |
| metrics-server | ✅ Работает | `kubectl top nodes` и `kubectl top pods` |
| NVIDIA DCGM exporter | ✅ Развёрнут | GPU-метрики экспортируются (gpu-operator) |
| Ручные проверки kubectl | ✅ Доступно | Проверка подов, деплойментов, логов |
| `kubectl logs` | ✅ Доступно | Логи всех подов через CLI |

### ❌ НЕ реализовано

| Компонент | Статус | Причина |
|-----------|--------|---------|
| Prometheus | ❌ Не развёрнут | Нет подов, сервисов, конфигураций |
| Grafana | ❌ Не развёрнут | Нет подов, сервисов |
| Alertmanager | ❌ Не развёрнут | Нет подов |
| kube-state-metrics | ❌ Не развёрнут | Нет подов |
| ServiceMonitors / PodMonitors | ❌ CRD отсутствуют | `error: resource type not found` |
| PrometheusRules | ❌ CRD отсутствуют | `error: resource type not found` |
| Loki / централизованные логи | ❌ Не развёрнут | Логи только через `kubectl logs` |
| node-exporter | ❌ Не развёрнут | Нет системных метрик узлов |
| Cert-manager | ❌ CRD отсутствуют | Мониторинг сертификатов — вручную |
| Дашборды мониторинга | ❌ Нет | Grafana не развёрнут |

### Текущий уровень мониторинга

**Уровень: ручной (Manual Health Checks).** Оператор вручную проверяет статус кластера командами `kubectl`, эндпоинтами `/health` и `kubectl logs`. Автоматическое оповещение (алертинг) **отсутствует**.

---

## 1. Эндпоинты здоровья (Health Endpoints)

Актуальные эндпоинты для ручной проверки:

| Сервис | URL | Ожидаемый ответ | Проверка |
|--------|-----|-----------------|----------|
| Portal (Internet) | https://fb1.spb.ru:443/health | 200 OK | `curl -sk https://fb1.spb.ru/health` |
| Portal (Test Zone) | http://10.129.13.78:30080/health | 200 OK | `curl -s http://10.129.13.78:30080/health` |
| BFF (внутренний) | http://aither-bff:3000/health | 200 OK | `kubectl exec ... -- curl -s http://aither-bff:3000/health` |
| AI Platform | http://aither-ai-platform:8000/health | 200 OK | `kubectl exec ... -- curl -s http://aither-ai-platform:8000/health` |
| Identity | http://aither-identity:8000/health | 200 OK | `kubectl exec ... -- curl -s http://aither-identity:8000/health` |
| vLLM 14B | http://vllm-14b-instruct:8000/health | 200 OK | `kubectl exec ... -- curl -s http://vllm-14b-instruct:8000/health` |
| vLLM 32B | http://vllm-32b-gptq:8000/health | 200 OK | `kubectl exec ... -- curl -s http://vllm-32b-gptq:8000/health` |
| Redis | redis-cli ping (через exec) | PONG | `kubectl exec deploy/aither-redis-rate-limit -n aither-inference -- redis-cli ping` |

---

## 2. Prometheus/Grafana — Runtime Deployment

### Текущий статус: ❌ NOT IMPLEMENTED

**Prometheus, Grafana и Alertmanager не развёрнуты в кластере.** По состоянию на 26.07.2026:

- `kubectl get pods -A | grep -Ei 'prometheus|grafana'` — **нет результатов**
- `kubectl get services -A | grep -Ei 'prometheus|grafana'` — **нет результатов**
- `kubectl get servicemonitors,podmonitors,prometheusrules -A` — **CRD не установлены** (`error: resource type not found`)
- ConfigMap/Secret для мониторинга — **отсутствуют**

**Текущий уровень мониторинга:** ручные проверки здоровья (раздел 3) и проверки статуса Kubernetes.

**Примечание:** NVIDIA DCGM exporter развёрнут через gpu-operator (экспортирует GPU-метрики на порту 9400), но метрики **не собираются** — Prometheus отсутствует.

### Рекомендуемый стек (план внедрения)

Для внедрения автоматизированного мониторинга рекомендуется:
1. Установить **kube-prometheus-stack** (Prometheus + Grafana + Alertmanager + kube-state-metrics + node-exporter)
2. Настроить **ServiceMonitors** для сбора метрик сервисов
3. Создать **PrometheusRules** для алертов
4. Настроить **Grafana dashboards**
5. Настроить маршруты оповещений **Alertmanager**

---

## 3. Ручные проверки (Manual Checks)

### Комплексная проверка здоровья

```bash
# Проверка всех деплойментов
for dep in aither-portal aither-portal-frontend aither-portal-backend \
           aither-bff aither-identity aither-ai-platform \
           vllm-14b-instruct vllm-32b-gptq \
           aither-redis-rate-limit nginx-gateway-32b; do
    ready=$(kubectl get deployment $dep -n aither-inference \
        -o jsonpath='{.status.readyReplicas}' 2>/dev/null)
    desired=$(kubectl get deployment $dep -n aither-inference \
        -o jsonpath='{.spec.replicas}' 2>/dev/null)
    echo "$dep: $ready/$desired ready"
done
```

### Проверка ресурсов узлов

```bash
# Использование CPU/памяти на узлах
kubectl top nodes

# Использование ресурсов подами
kubectl top pods -n aither-inference
kubectl top pods -n aiops
```

### Проверка GPU

```bash
# Проверка GPU на vLLM 14B
kubectl exec -n aither-inference deployment/vllm-14b-instruct -- \
    nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu \
    --format=csv,noheader 2>/dev/null

# Проверка GPU на vLLM 32B
kubectl exec -n aither-inference deployment/vllm-32b-gptq -- \
    nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu \
    --format=csv,noheader 2>/dev/null
```

### Проверка перезапусков подов

```bash
# Подсчёт перезапусков
kubectl get pods -n aither-inference -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.containerStatuses[0].restartCount}{"\n"}{end}'

# Выявление CrashLoop
kubectl get pods -n aither-inference | grep -vE 'Running|Completed'
```

### Проверка Redis

```bash
kubectl exec -n aither-inference deployment/aither-redis-rate-limit -- redis-cli ping
```

---

## 4. Логи

```bash
# BFF логи (последние 100 строк, следование)
kubectl logs -n aither-inference deployment/aither-bff --tail=100 -f

# Все логи с фильтрацией ошибок
kubectl logs -n aither-inference deployment/aither-bff --tail=200 | grep -i error

# Логи GPU-подов
kubectl logs -n aither-inference deployment/vllm-14b-instruct --tail=50
kubectl logs -n aither-inference deployment/vllm-32b-gptq --tail=50

# Логи Portal (frontend + backend)
kubectl logs -n aither-inference deployment/aither-portal-frontend --tail=50
kubectl logs -n aither-inference deployment/aither-portal-backend --tail=50

# Логи AI Platform
kubectl logs -n aither-inference deployment/aither-ai-platform --tail=100

# Логи nginx-шлюза
kubectl logs -n aither-inference deployment/nginx-gateway-32b --tail=100
```

### Поиск по логам

```bash
# Поиск 5xx ошибок за последние 15 минут
kubectl logs -n aither-inference deployment/nginx-gateway-32b --since=15m \
    | grep -E 'HTTP/[0-9.]+" 5[0-9][0-9]'

# Подсчёт кодов ответа
kubectl logs -n aither-inference deployment/nginx-gateway-32b --tail=500 \
    | grep -oP 'HTTP/\d\.\d" \K\d{3}' | sort | uniq -c | sort -rn
```

---

## 5. Ключевые метрики (рекомендуемые — не внедрены)

> ⚠️ **Все метрики ниже — рекомендуемые для будущего внедрения Prometheus. На данный момент НЕ собираются автоматически.**

### Производительность API

| Метрика | Описание | Порог тревоги |
|---------|----------|---------------|
| request_rate | Запросов/сек | >100 (нагрузка) |
| error_rate_5xx | Доля 5xx ошибок | >1% |
| error_rate_4xx | Доля 4xx ошибок | >5% |
| latency_p95 | 95-й перцентиль задержки | >30s для 32B |
| latency_p50 | Медианная задержка | >5s |

### Ресурсы

| Метрика | Описание | Порог тревоги |
|---------|----------|---------------|
| gpu_utilization | Загрузка GPU | >90% |
| gpu_memory_used | Использование VRAM | >90% |
| gpu_temperature | Температура GPU | >85°C |
| pod_cpu | CPU подов | >80% requests |
| pod_memory | Память подов | >80% requests |
| node_disk | Диск узлов | >80% |

### Доступность

| Метрика | Порог тревоги |
|---------|---------------|
| Pod restarts | >0 за 5 минут |
| CrashLoopBackOff | Любой |
| Health check failures | >2 подряд |
| Deployment not ready | >30s |

---

## 6. Alert Thresholds — рекомендуемые пороги алертов

> ⚠️ **НЕ внедрены. Использовать при настройке PrometheusRules после развёртывания Prometheus.**

### Критические алерты (Severity: critical) — немедленное реагирование

| Алерт | Условие | Длительность | PromQL (шаблон) |
|-------|---------|-------------|------------------|
| **InstanceDown** | Pod не Ready | 1m | `kube_pod_status_ready{condition="false"} == 1` |
| **GPUOffline** | GPU не обнаружен | 1m | `absent(DCGM_FI_DEV_GPU_TEMP)` |
| **HighGPUUsage** | GPU > 95% | 5m | `DCGM_FI_DEV_GPU_UTIL > 95` |
| **VRAMExhausted** | VRAM > 95% | 1m | `DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_TOTAL * 100 > 95` |
| **High5xxRate** | 5xx > 5% | 5m | `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05` |
| **RedisDown** | Redis недоступен | 1m | `redis_up == 0` |

### Предупреждающие алерты (Severity: warning) — реагирование в течение рабочего дня

| Алерт | Условие | Длительность | PromQL (шаблон) |
|-------|---------|-------------|------------------|
| **HighCPUUsage** | Pod CPU > 80% requests | 10m | `rate(container_cpu_usage_seconds_total[5m]) / kube_pod_container_resource_requests{resource="cpu"} > 0.8` |
| **HighMemoryUsage** | Pod Memory > 80% requests | 10m | `container_memory_working_set_bytes / kube_pod_container_resource_requests{resource="memory"} > 0.8` |
| **HighDiskUsage** | Диск > 80% | 5m | `(node_filesystem_size_bytes - node_filesystem_free_bytes) / node_filesystem_size_bytes * 100 > 80` |
| **High4xxRate** | 4xx > 10% | 10m | аналогично 5xx |
| **LatencyP95High** | P95 > 10s (14B) / P95 > 30s (32B) | 5m | `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 30` |
| **PodRestarts** | Перезапуски > 0 | 5m | `rate(kube_pod_container_status_restarts_total[5m]) > 0` |

### Информационные алерты (Severity: info)

| Алерт | Условие | Назначение |
|-------|---------|------------|
| **CertificateExpiringSoon** | Сертификат истекает < 30 дней | Предупреждение о необходимости обновления |
| **HighModelQueue** | Очередь запросов > 10 | Предупреждение о росте очереди vLLM |
| **SlowRequests** | P50 > 5s (14B) / P50 > 15s (32B) | Деградация производительности |

---

## 7. Alert Ownership — ответственные за алерты

| Роль | Зона ответственности | Алерты |
|------|---------------------|--------|
| **DevOps / SRE** | Инфраструктура, узлы, сеть | InstanceDown, HighDiskUsage, HighCPUUsage, HighMemoryUsage, NodeNotReady |
| **MLOps / AI Infra** | GPU, vLLM, модели | GPUOffline, HighGPUUsage, VRAMExhausted, HighModelQueue |
| **Backend-разработчик (BFF)** | API-шлюз, BFF | High5xxRate, High4xxRate, LatencyP95High, SlowRequests |
| **Platform Team** | AI Platform, Identity | Health check failures, PodRestarts |
| **Security / Admin** | Сертификаты, Redis | CertificateExpiringSoon, RedisDown |
| **Первая линия (Level 1)** | Общий мониторинг | Все алерты — первичная сортировка и эскалация |

### Матрица эскалации

| Severity | Время реакции | Эскалация при отсутствии реакции |
|----------|--------------|----------------------------------|
| critical | 15 минут | L1 → DevOps Lead через 30 мин |
| warning | 4 часа (рабочее время) | L1 → Team Lead через 8 часов |
| info | Следующий рабочий день | Без эскалации |

---

## 8. Notification Route — рекомендуемая цепочка оповещения

> ⚠️ **НЕ внедрено. Использовать при настройке Alertmanager.**

### Основной маршрут

```
Алерт (Prometheus) → Alertmanager → Email → Telegram (дублирование)
```

### Конфигурация Alertmanager (шаблон)

```yaml
route:
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'email-critical'
  routes:
    - match:
        severity: critical
      receiver: 'email-critical'
      continue: true
    - match:
        severity: critical
      receiver: 'telegram-critical'
    - match:
        severity: warning
      receiver: 'email-warning'
    - match:
        severity: info
      receiver: 'email-info'

receivers:
  - name: 'email-critical'
    email_configs:
      - to: 'devops@fb1.spb.ru'
        send_resolved: true
        headers:
          Subject: '[CRITICAL] Aither Platform Alert'

  - name: 'telegram-critical'
    telegram_configs:
      - bot_token: '<TELEGRAM_BOT_TOKEN>'
        chat_id: <CHAT_ID>
        parse_mode: 'HTML'
        message: '{{ template "telegram.default" . }}'

  - name: 'email-warning'
    email_configs:
      - to: 'devops@fb1.spb.ru'
        send_resolved: true

  - name: 'email-info'
    email_configs:
      - to: 'devops@fb1.spb.ru'
        send_resolved: false
```

### Рабочее время / дежурства

| Период | Канал оповещения | Примечание |
|--------|-----------------|------------|
| Рабочее время (Пн–Пт, 09:00–18:00 МСК) | Email + Telegram | Все severity |
| Нерабочее время | Telegram (critical only) | warning/info — отложенные |

---

## 9. Dashboard Inventory — рекомендуемые дашборды

> ⚠️ **НЕ внедрены. Графана не развёрнута. Использовать при развёртывании.**

| Дашборд | Назначение | Источник |
|---------|------------|----------|
| **Aither Platform Overview** | Сводная панель: здоровье сервисов, запросы, ошибки | Создать вручную |
| **GPU Node Dashboard** | NVIDIA DCGM: температура, утилизация, VRAM, throttling | DCGM Exporter Dashboard (Grafana ID: 12239) |
| **vLLM Inference Dashboard** | Запросы, задержки, throughput, очереди | Создать вручную (метрики vLLM `/metrics`) |
| **Kubernetes Cluster Dashboard** | Поды, узлы, ресурсы (kube-state-metrics) | Kubernetes Cluster (Grafana ID: 315) |
| **NGINX Gateway Dashboard** | RPS, коды ответа, задержки upstream | NGINX Ingress (Grafana ID: 9614) |
| **Redis Dashboard** | Подключения, память, hit rate, latency | Redis Dashboard (Grafana ID: 763) |
| **Node Exporter Dashboard** | CPU, память, диск, сеть узлов | Node Exporter Full (Grafana ID: 1860) |

---

## 10. SLI/SLO — для стадии Controlled Beta

> ⚠️ **Определены для стадии Controlled Beta. Метрики собираются вручную, без привязки к Prometheus.**

### Service Level Indicators (SLI)

| Индикатор | Определение | Цель | Метод измерения |
|-----------|-------------|------|-----------------|
| **Availability** | Доля успешных health-check за период | 99.5% | Ручная проверка `/health` раз в 30 мин |
| **Latency** | P95 задержки ответа API (32B) | ≤ 30s | Логи nginx/заголовки ответа |
| **Error Rate** | Доля 5xx ответов | < 1% | `kubectl logs` nginx-gateway |
| **GPU Uptime** | Доступность GPU-подов | 99.5% | `kubectl get pods` readiness |

### Service Level Objectives (SLO)

| SLO | Значение | Период | Бюджет ошибок |
|-----|---------|--------|---------------|
| Доступность портала | 99.5% | 30 дней | 3.6 часа downtime |
| Успешные инференс-запросы | 99.0% | 30 дней | 7.2 часа degraded |
| P95 latency (32B) ≤ 30s | 95% запросов | Скользящие 7 дней | 5% запросов > 30s допустимо |

### Текущий статус SLI (26.07.2026)

> 📝 **Заполняется оператором вручную при каждой проверке.**

| Дата | Availability | Error Rate | GPU Up | Примечание |
|------|-------------|------------|--------|------------|
| 26.07.2026 | — | — | — | Первичная инвентаризация |

---

## 11. Log Retention — политика хранения логов

### Текущее состояние

Логи подов хранятся локально в Kubernetes и доступны через `kubectl logs`. **Централизованный сбор логов отсутствует (Loki не развёрнут).**

### Политика хранения (рекомендуемая, после внедрения)

| Тип логов | Хранение (hot) | Хранение (warm/cold) | Примечание |
|-----------|----------------|----------------------|------------|
| API-логи (BFF, nginx) | 7 дней | 30 дней | Для отладки и аудита |
| Логи моделей (vLLM) | 3 дня | 14 дней | Высокий объём |
| Системные логи (kube-system) | 7 дней | 14 дней | Для диагностики |
| Аудиторные логи (Portal) | 7 дней | 90 дней | Для compliance |
| Логи безопасности | 30 дней | 365 дней | Для расследований |

### Ручная очистка (текущий метод)

```bash
# Просмотр размера логов пода
kubectl logs -n aither-inference deployment/vllm-32b-gptq --tail=1 > /dev/null
# Логи ротируются Kubernetes автоматически при достижении 10MB/файл, макс. 5 файлов
```

---

## 12. Capacity Monitoring — мониторинг ресурсов

> ⚠️ **Мониторинг ресурсов — ручной, через `kubectl top` и `kubectl describe node`.**

### Текущая ёмкость кластера (26.07.2026)

| Узел | CPU Cores | Память | GPU | Диск (OS) |
|------|-----------|--------|-----|-----------|
| bootsmam-k8s-clnt01-n7-gpu | ~112 ядер | ~755 GB | 2× GPU (Turing, CC 7.5) | ? |
| bootsman-k8s-clnt01-n8-gpu | ~112 ядер | ~755 GB | 2× GPU (Turing, CC 7.5) | ? |

### Что проверять

```bash
# Использование ресурсов узлов
kubectl top nodes

# Детальная информация по узлу
kubectl describe node <node-name> | grep -A10 "Allocated resources"

# Диск (внутри пода)
kubectl exec -n aither-inference <pod> -- df -h

# GPU-память
kubectl exec -n aither-inference deployment/vllm-32b-gptq -- \
    nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu \
    --format=csv
```

### Пороги для ручного реагирования

| Ресурс | Порог | Действие |
|--------|-------|----------|
| CPU узла | >85% allocated | Планировать масштабирование |
| Память узла | >85% allocated | Проверить утечки, запланировать расширение |
| VRAM | >90% used | Возможна OOM модели |
| Диск | >80% | Очистка или расширение |

---

## 13. Certificate Expiration Monitoring — мониторинг сертификатов

> ⚠️ **Cert-manager НЕ развёрнут. Проверка сертификатов — вручную.**

### Сертификаты для проверки

| Сертификат | Домен | Способ проверки |
|------------|-------|-----------------|
| Portal SSL | fb1.spb.ru | `openssl s_client -connect fb1.spb.ru:443` |
| Внутренние TLS | Внутренние сервисы | Проверить секреты K8s |

### Ручная проверка

```bash
# Проверка срока действия сертификата портала
echo | openssl s_client -connect fb1.spb.ru:443 -servername fb1.spb.ru 2>/dev/null \
    | openssl x509 -noout -dates

# Проверка K8s TLS-секретов
kubectl get secrets -n aither-inference --field-selector type=kubernetes.io/tls
```

### Рекомендуемый порог

| Условие | Действие |
|---------|----------|
| Сертификат истекает < 60 дней | Планировать обновление |
| Сертификат истекает < 30 дней | Срочно обновить |
| Сертификат истёк | Инцидент — немедленное обновление |

---

## 14. Test Alert Procedure — проверка алертинга

> ⚠️ **Процедура применима ПОСЛЕ внедрения Prometheus/Alertmanager. На данный момент проверить нечего.**

### После внедрения — процедура тестирования

1. **Проверка доставки алертов:**
   - Создать тестовый алерт через Alertmanager API
   - Проверить получение email / Telegram
   ```bash
   curl -X POST http://alertmanager:9093/api/v2/alerts \
     -H 'Content-Type: application/json' \
     -d '[{"labels":{"alertname":"TestAlert","severity":"critical"},"annotations":{"summary":"Тестовый алерт"}}]'
   ```

2. **Проверка срабатывания PrometheusRules:**
   - Временно снизить порог алерта до гарантированно срабатывающего
   - Дождаться срабатывания в Prometheus → проверка в Alertmanager
   - Вернуть исходный порог

3. **Проверка silence/mute:**
   - Создать silence в Alertmanager
   - Убедиться, что алерты не доставляются
   - Снять silence

4. **Проверка Grafana-дашбордов:**
   - Открыть каждый дашборд
   - Проверить наличие данных за последние 15 минут
   - Проверить отсутствие ошибок «No data»

### Периодичность тестирования

| Проверка | Частота | Ответственный |
|----------|---------|---------------|
| Доставка alert-каналов | 1 раз в месяц | DevOps |
| PrometheusRules | После каждого изменения | DevOps |
| Дашборды | 1 раз в квартал | DevOps / Platform Team |

---

## 15. Not Implemented — сводный список

Ниже перечислены **ВСЕ** компоненты мониторинга, которые **НЕ реализованы** по состоянию на 26.07.2026:

| # | Компонент | Приоритет внедрения | Трудозатраты (оценка) |
|---|-----------|---------------------|----------------------|
| 1 | **Prometheus** (сбор метрик) | 🔴 Критичный | 4–8 часов |
| 2 | **Grafana** (визуализация) | 🔴 Критичный | 2–4 часа (в составе стека) |
| 3 | **Alertmanager** (оповещения) | 🔴 Критичный | 1–2 часа (в составе стека) |
| 4 | **kube-state-metrics** (метрики объектов K8s) | 🔴 Критичный | В составе стека |
| 5 | **node-exporter** (метрики узлов) | 🟡 Высокий | В составе стека |
| 6 | **ServiceMonitors** (автообнаружение метрик) | 🟡 Высокий | 2–4 часа |
| 7 | **PrometheusRules** (алерты) | 🔴 Критичный | 4–8 часов |
| 8 | **Grafana Dashboards** | 🟡 Высокий | 8–16 часов |
| 9 | **Notification Routes** (email + Telegram) | 🔴 Критичный | 2–4 часа |
| 10 | **Loki** (централизованные логи) | 🟢 Средний | 4–8 часов |
| 11 | **Cert-manager** (автообновление сертификатов) | 🟢 Средний | 2–4 часа |
| 12 | **Метрики vLLM** (экспорт `/metrics`) | 🟡 Высокий | 1–2 часа |
| 13 | **Метрики BFF/Portal** (экспорт `/metrics`) | 🟡 Высокий | 2–4 часа |
| 14 | **Dashboard SLI/SLO** (автоматический) | 🟢 Средний | 2–4 часа |
| 15 | **Автоматический мониторинг сертификатов** | 🟢 Средний | 1–2 часа |

### Рекомендуемый порядок внедрения

1. **Неделя 1:** Развернуть kube-prometheus-stack (Prometheus + Grafana + Alertmanager + kube-state-metrics + node-exporter)
2. **Неделя 2:** Настроить ServiceMonitors для vLLM, BFF, nginx; создать базовые PrometheusRules
3. **Неделя 3:** Создать Grafana-дашборды; настроить Alertmanager (email + Telegram)
4. **Неделя 4:** Настроить Loki для логов; cert-manager; тонкая настройка алертов

---

## Приложение А. Быстрые команды (Cheat Sheet)

```bash
# === Здоровье кластера ===
kubectl get nodes
kubectl get pods -n aither-inference
kubectl get pods -n aiops

# === Ресурсы ===
kubectl top nodes
kubectl top pods -n aither-inference
kubectl top pods -n aiops

# === GPU ===
kubectl exec -n aither-inference deployment/vllm-32b-gptq -- nvidia-smi
kubectl exec -n aither-inference deployment/vllm-14b-instruct -- nvidia-smi

# === Логи ===
kubectl logs -n aither-inference deployment/aither-bff --tail=100
kubectl logs -n aither-inference deployment/nginx-gateway-32b --tail=100 | grep ' 5[0-9][0-9] '

# === Health endpoints ===
curl -sk https://fb1.spb.ru/health
curl -s http://10.129.13.78:30080/health

# === Сертификаты ===
echo | openssl s_client -connect fb1.spb.ru:443 -servername fb1.spb.ru 2>/dev/null | openssl x509 -noout -dates
```

---

*Документ отражает фактическое состояние на 26.07.2026. Подлежит обновлению после внедрения автоматизированного мониторинга.*
