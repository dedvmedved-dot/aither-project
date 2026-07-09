# Aither HPA — Автомасштабирование

**Версия:** 1.0 | **Дата:** 09.07.2026

---

## Обзор

Aither использует Kubernetes HPA (Horizontal Pod Autoscaler) в трёх режимах:

| Компонент | Метрика | Min | Max | Тип |
|---|---|---|---|---|
| Gateway | CPU 70% / Memory 80% | 1 | 3 | Resource (metrics-server) |
| vLLM-14B | CPU 80% / Memory 85% | 1 | 1 | Resource (мониторинг) |
| vLLM-32B | CPU 80% / Memory 85% | 1 | 1 | Resource (мониторинг) |

## Архитектура мониторинга

```
metrics-server ────► kubectl top (CPU/Memory)
     │
     └──► HPA (Resource metrics)
     
Prometheus ──► DCGM Exporter (GPU: util, memory, temp)
     │
     ├──► Gateway /metrics (TTFT, requests, tokens, errors)
     ├──► vLLM /metrics (queue, latency, throughput)
     └──► Prometheus Adapter ──► External/Custom Metrics API
                                     │
                                     └──► HPA (GPU, queue-based)
```

## Текущие HPA

### Gateway (`gateway-hpa`)

```yaml
minReplicas: 1
maxReplicas: 3
metrics:
  - cpu: 70%
  - memory: 80%
```

Шкалирование по CPU/Memory. Gateway — stateless-прокси, может безопасно
масштабироваться горизонтально в пределах доступных CPU на узле.

### vLLM (`vllm-14b-hpa`, `vllm-32b-hpa`)

```yaml
minReplicas: 1
maxReplicas: 1  # ограничено GPU: 2 GPU на узел = 1 vLLM под
metrics:
  - cpu: 80%
  - memory: 85%
```

Оба vLLM HPA настроены как **мониторинг** (min=max=1). Шкалирование
vLLM ограничено доступными GPU — каждый под требует 2 GPU, а на каждом
узле только 2 GPU:

| Узел | GPU | vLLM под | Статус |
|---|---|---|---|
| n8 (control-plane) | 2× RTX6000 | vllm-qwen (14B) | 2/2 GPU |
| n7 (worker) | 2× RTX6000 | vllm-qwen32b (32B) | 2/2 GPU |

## GPU-based HPA (планируется)

Для GPU-метрик требуется:
1. **Prometheus Adapter** с кастомными правилами (установлен ✅)
2. **Pod-level DCGM labels** — нужна доработка scrape-конфигурации
   Prometheus для добавления `pod` и `namespace` лейблов к DCGM-метрикам

### Целевая конфигурация

```yaml
# Когда GPU-метрики будут доступны на уровне подов:
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: vllm-gpu-hpa
spec:
  metrics:
  - type: Pods
    pods:
      metric:
        name: gpu_utilization_percent
      target:
        type: AverageValue
        averageValue: "80"
  - type: Pods
    pods:
      metric:
        name: vllm_queue_depth
      target:
        type: AverageValue
        averageValue: "10"
```

### Ограничения

- Каждый vLLM под требует 2 GPU эксклюзивно
- HPA не может создать новый под на узле без свободных GPU
- Для реального масштабирования vLLM нужен третий GPU-узел
- Альтернатива: MIG (Multi-Instance GPU) для RTX 6000 (Turing) — не поддерживается

## Управление

```bash
# Статус всех HPA
kubectl get hpa -A

# Детали конкретного HPA
kubectl describe hpa gateway-hpa

# Изменить параметры
kubectl edit hpa gateway-hpa

# Принудительное масштабирование (ручное)
kubectl scale deployment gateway --replicas=2
```

## Компоненты инфраструктуры

| Компонент | Namespace | Статус |
|---|---|---|
| metrics-server | kube-system | ✅ Running |
| Prometheus | monitoring | ✅ Running, NodePort 30909 |
| Prometheus Adapter | custom-metrics | ✅ Running |
| DCGM Exporter | monitoring | ✅ Running (2 реплики) |
| Grafana | monitoring | ✅ Running, NodePort 30300 |
