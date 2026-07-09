# 06-troubleshooting.md — Типовые проблемы

## Под не стартует (ContainerCreating)

```bash
kubectl describe pod -n aither <pod-name> | grep -A5 Events
```

Частые причины:
- Docker-образ не загружен → `make offline-load`
- PVC не создан → `kubectl apply -f k8s/postgres/`
- GPU не доступен → `nvidia-smi`, проверить `runtimeClassName: nvidia`

## Gateway: connection refused

```bash
kubectl logs -n aither deploy/gateway --tail=50
```

Частые причины:
- PostgreSQL не готов → `kubectl exec -n aither deploy/postgres -- pg_isready`
- Redis не готов → `kubectl exec -n aither deploy/redis -- redis-cli ping`
- ConfigMap не смонтирован → `kubectl describe pod -n aither <gateway-pod>`

## vLLM: OOM (out of memory)

```bash
kubectl logs -n aither deploy/vllm-qwen --tail=50
```

Решение: уменьшить `--gpu-memory-utilization` до 0.85 или `--max-model-len`.

## Портал: 502 Bad Gateway

```bash
# Проверить что Gateway доступен
curl http://K8S_NODE_IP:30900/health

# Проверить BFF
ssh VPS2 "journalctl -u aither-bff --since '5 min ago'"
```

## Grafana: дашборды пустые

```bash
# Проверить что Prometheus скрейпит метрики
curl http://localhost:30909/api/v1/targets | python3 -m json.tool
```

## БД: недостаточно места

```bash
df -h /data/postgres
# При < 10% — очистить старые логи или расширить PVC
```

## Модель не загружается

```bash
# Проверить наличие файлов
ssh K8S_NODE "ls -la /mnt/models/Qwen2.5-14B-Instruct/"

# Проверить vLLM логи
kubectl logs -n aither deploy/vllm-qwen | grep -i error
```
