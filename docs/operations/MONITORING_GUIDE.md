# Aither AI Platform — Руководство по мониторингу

**Версия:** OPS-01-R1 | **Дата:** 26 июля 2026

---

## 1. Эндпоинты здоровья

| Сервис | URL | Ожидаемый ответ |
|--------|-----|-----------------|
| Portal (Internet) | https://fb1.spb.ru:443/health | 200 OK |
| Portal (Test Zone) | http://10.129.13.78:30080/health | 200 OK |
| BFF (внутренний) | http://aither-bff:3000/health | 200 OK |
| AI Platform | http://aither-ai-platform:8000/health | 200 OK |
| Identity | http://aither-identity:8000/health | 200 OK |
| vLLM 14B | http://vllm-14b-instruct:8000/health | 200 OK |
| vLLM 32B | http://vllm-32b-gptq:8000/health | 200 OK |
| Redis | redis-cli ping (через exec) | PONG |

---

## 2. Ключевые метрики

### Производительность API

| Метрика | Описание | Порог тревоги |
|---------|----------|---------------|
| request_rate | Запросов/сек | >100 (нагрузка) |
| error_rate_5xx | Доля 5xx ошибок | >1% |
| error_rate_4xx | Доля 4xx ошибок | >5% |
| latency_p95 | 95-й перцентиль задержки | >30s для 32B |
| latency_p50 | Медианная задержка | >5s |

### Ресурсы

| Метрика | Описание | Порог |
|---------|----------|-------|
| gpu_utilization | Загрузка GPU | >90% |
| gpu_memory_used | Использование VRAM | >90% |
| pod_cpu | CPU подов | >80% |
| pod_memory | Память подов | >80% |

### Доступность

| Метрика | Порог |
|---------|-------|
| Pod restarts | >0 за 5 минут |
| Crash loops | Любой |
| Health check failures | >2 подряд |

---

## 3. Проверка вручную

```bash
# Комплексная проверка здоровья
for dep in aither-portal aither-portal-frontend aither-bff aither-identity \
           aither-ai-platform vllm-14b-instruct vllm-32b-gptq \
           aither-redis-rate-limit nginx-gateway-32b; do
    ready=$(kubectl get deployment $dep -n aither-inference -o jsonpath='{.status.readyReplicas}')
    echo "$dep: $ready/1"
done

# Проверка GPU
kubectl exec -n aither-inference deployment/vllm-14b-instruct -- nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader 2>/dev/null

# Проверка Redis
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
```

---

## 5. Prometheus/Grafana

Метрики доступны через стандартные K8s метрики (kube-state-metrics, cadvisor).

### PromQL примеры

```promql
# Доступность подов
kube_deployment_status_replicas_available{namespace="aither-inference"}

# Перезапуски
rate(kube_pod_container_status_restarts_total{namespace="aither-inference"}[5m])

# Использование CPU
rate(container_cpu_usage_seconds_total{namespace="aither-inference"}[1m])
```
