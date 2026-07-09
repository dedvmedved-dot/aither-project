# Aither Platform — Production Runbook

**Версия:** 1.0
**Дата:** 09.07.2026
**Владелец:** Сергей Кравчук

---

## 1. Архитектура

```
Пользователи → VPS1 (nginx:10443) → VPS2:80 (Портал + BFF :3000)
                                        │
                                   VPS3:80 (Failover, stateless)
                                        │
                                   Gateway (K8s n7 :30900)
                                        │
                              ┌─────────┴─────────┐
                         vLLM-14B (n8)      vLLM-32B (n7)
                         Qwen2.5-Coder      Qwen2.5-32B-Instruct
                         2× RTX6000          2× RTX6000

База данных: PostgreSQL (K8s n8, NodePort 31113)
Кэш:          Redis (K8s n8)
Векторная БД: ChromaDB (K8s n7)
Embeddings:   multilingual-e5-large (K8s n7, CPU)
Мониторинг:   Prometheus + Grafana + DCGM-Exporter
```

## 2. Доступ к кластеру

```bash
# VPS1 → VPS2 (WireGuard)
ssh root@130.17.1.90

# На VPS2 — kubectl
kubectl get nodes
kubectl get pods -A
kubectl top nodes
kubectl top pods
```

## 3. Health Check — быстрая проверка

```bash
#!/bin/bash
# health-check.sh — статус всех компонентов одной командой

echo "=== NODES ==="
kubectl get nodes

echo -e "\n=== PROBLEM PODS ==="
kubectl get pods -A --field-selector=status.phase!=Running | grep -v Completed

echo -e "\n=== RESOURCE USAGE ==="
kubectl top nodes

echo -e "\n=== GPU STATUS ==="
kubectl describe nodes | grep -A1 'nvidia.com/gpu$'

echo -e "\n=== ENDPOINTS ==="
curl -s http://localhost:30900/health | jq .
curl -s http://localhost:3000/api/v1/health | jq .

echo -e "\n=== RECENT EVENTS ==="
kubectl get events --sort-by='.lastTimestamp' | tail -10
```

## 4. Инциденты и восстановление

### 4.1 Gateway не отвечает (503)

```bash
# Проверить под
kubectl get pod -l app=gateway
kubectl logs -l app=gateway --tail=50

# Проверить Redis
kubectl get pod -l app=redis
kubectl exec -it deploy/redis -- redis-cli ping

# Перезапустить Gateway
kubectl rollout restart deployment/gateway
```

### 4.2 vLLM не отвечает / OOM

```bash
# Проверить поды моделей
kubectl get pod -l app=vllm-qwen
kubectl logs -l app=vllm-qwen32b --tail=20

# GPU-память
kubectl exec -it $(kubectl get pod -l app=vllm-qwen32b -o name | head -1) -- nvidia-smi

# Перезапустить модель (drain сначала через Gateway API!)
curl -X POST http://localhost:30900/admin/models/qwen2.5-32b-instruct/drain
kubectl rollout restart deployment/vllm-qwen32b
# После загрузки модели:
curl -X POST http://localhost:30900/admin/models/qwen2.5-32b-instruct/undrain
```

### 4.3 PostgreSQL не отвечает

```bash
kubectl get pod -l app=postgres
kubectl logs -l app=postgres --tail=20
kubectl exec -it deploy/postgres -- psql -U aither -d aither_billing -c "SELECT 1;"

# Перезапуск (graceful)
kubectl rollout restart deployment/postgres
```

### 4.4 Redis не отвечает

```bash
kubectl exec -it deploy/redis -- redis-cli ping
# Если нет ответа — перезапустить
kubectl rollout restart deployment/redis
```

### 4.5 Портал не открывается (VPS2/VPS3)

```bash
# VPS2
ssh root@130.17.1.90 "docker ps | grep portal && docker logs portal --tail=20"

# Проверить BFF
ssh root@130.17.1.90 "curl -s localhost:3000/api/v1/health"

# Перезапустить портал
ssh root@130.17.1.90 "cd /opt/aither && docker-compose restart portal"
```

### 4.6 Embeddings недоступны

```bash
kubectl get pod -l app=embeddings
kubectl logs -l app=embeddings --tail=20
curl -s http://embeddings.default.svc.cluster.local:8001/health

# Перезапустить
kubectl rollout restart deployment/embeddings
# Примечание: первый запуск ~5 мин (скачивание модели multilingual-e5-large, ~560MB)
```

## 5. Резервное копирование

### 5.1 База данных PostgreSQL

```bash
# Дамп БД
kubectl exec deploy/postgres -- pg_dump -U aither aither_billing > /tmp/aither-db-$(date +%Y%m%d-%H%M).sql

# Копировать на VPS1
scp /tmp/aither-db-*.sql root@170.168.91.95:/root/backups/

# Восстановление
kubectl exec -i deploy/postgres -- psql -U aither aither_billing < backup.sql
```

### 5.2 Конфигурации

```bash
# С репозитория
cd /root/aither-project && git pull
tar czf /tmp/aither-configs-$(date +%Y%m%d).tar.gz \
  gateway/gateway.py configs/ k8s/ portal/ docker-compose.yml
```

### 5.3 Расписание (cron)

```bash
# Ежедневно в 3:00 МСК
# Добавить в crontab на VPS2:
# 0 3 * * * /root/scripts/backup-aither.sh
```

## 6. Мониторинг

### 6.1 Prometheus (+ Grafana)

```
URL:     http://n7:30900/metrics (Gateway)
Grafana: http://n7:32300 (login: admin / admin)
```

### 6.2 Ключевые метрики

| Метрика | Что | Тревога при |
|---|---|---|
| `gateway_ttft_seconds` | Time-to-first-token | P95 > 10s |
| `gateway_requests_total` | Всего запросов | — |
| `gateway_billing_errors_total` | Ошибки биллинга | > 0 за 5 мин |
| `gateway_active_requests` | Активные запросы | > max_concurrent |
| `node_memory_MemAvailable_bytes` | Свободная RAM | < 4GB |
| `DCGM_FI_DEV_GPU_UTIL` | GPU utilization | > 95% sustained |

### 6.3 Алерты (AlertManager)

```yaml
# TODO: настроить AlertManager rules при Stage 6 #28
# - Pod CrashLoopBackOff > 5 мин
# - GPU utilisation < 5% при активных запросах
# - PostgreSQL connections > 80%
# - Disk usage > 85%
```

## 7. Процедуры обслуживания

### 7.1 Обновление моделей

```bash
# 1. Drain модель
curl -X POST localhost:30900/admin/models/<model>/drain

# 2. Дождаться завершения активных запросов
curl localhost:30900/admin/queues

# 3. Обновить модель в /mnt/models
# 4. Перезапустить vLLM
kubectl rollout restart deployment/vllm-<модель>

# 5. Дождаться загрузки (следить за логами)
kubectl logs -f deployment/vllm-<модель>

# 6. Undrain
curl -X POST localhost:30900/admin/models/<model>/undrain
```

### 7.2 Обновление Gateway

```bash
kubectl set image deployment/gateway gateway=aither-gateway:latest
kubectl rollout status deployment/gateway
```

### 7.3 Обновление Портала

```bash
# На VPS2 и VPS3
ssh root@130.17.1.90 "cd /opt/aither && git pull && docker-compose up -d --build portal"
ssh root@89.127.217.88 "cd /opt/aither && git pull && docker-compose up -d --build portal"
```

## 8. Контакты

| Роль | Контакт |
|---|---|
| DevOps / SRE | Сергей Кравчук (tg: @sergey_kravchuk) |
| GPU-инфраструктура | VPS1 (170.168.91.95) → VPS2 (130.17.1.90) |
| Резервный портал | VPS3 (89.127.217.88) |
| БД администратор | K8s PostgreSQL (n8:31113) |

## 9. План эвакуации (Disaster Recovery)

1. **VPS2 недоступен** → VPS1 nginx автоматически переключает на VPS3 (backup upstream)
2. **VPS3 тоже недоступен** → ручной перевод DNS на VPS1:10443 с прямым доступом к Gateway
3. **n8 (control-plane) недоступен** → невозможно управлять кластером; восстановить n8 приоритетно
4. **n7 (vLLM 32B) недоступен** → Gateway автоматически маршрутизирует все запросы на 14B (n8)
5. **Полная потеря БД** → восстановление из ежедневного бэкапа

### Восстановление с нуля

```bash
# 1. Развернуть K8s
# 2. Применить манифесты
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/postgres/
kubectl apply -f k8s/redis/

# 3. Восстановить БД
kubectl exec -i deploy/postgres -- psql -U aither aither_billing < latest-backup.sql

# 4. Загрузить модели на /mnt/models
# 5. Запустить vLLM
kubectl apply -f k8s/vllm-14b/
kubectl apply -f k8s/vllm-32b/

# 6. Gateway + ChromaDB + Embeddings
kubectl apply -f k8s/gateway/
kubectl apply -f k8s/chromadb/
kubectl apply -f k8s/embeddings/

# 7. Портал на VPS2
ssh vps2 "cd /opt/aither && docker-compose up -d"
```
