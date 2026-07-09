# 03-admin-guide.md — Руководство администратора

## Управление платформой

### Проверка состояния
```bash
bash scripts/health-check.sh
```

### Просмотр логов
```bash
kubectl logs -n aither deploy/gateway --tail=100 -f
kubectl logs -n aither deploy/vllm-qwen --tail=100 -f
```

### Перезапуск сервиса
```bash
kubectl rollout restart deploy/gateway -n aither
kubectl rollout restart deploy/vllm-qwen -n aither
```

### Резервное копирование
```bash
bash scripts/backup.sh
# → /backup/aither/YYYY-MM-DD_HHMM/
```

### Восстановление
```bash
bash scripts/restore.sh /backup/aither/2026-07-11_1200
```

### Ротация ключей
```bash
bash scripts/rotate-keys.sh <org_id>
```

### Сбор логов для диагностики
```bash
bash scripts/collect-logs.sh
# → /tmp/aither-logs-YYYYMMDD-HHMM/
```

## Управление пользователями

### Просмотр организаций
```sql
SELECT id, name, invite_code FROM organizations;
```

### Назначение администратора
```sql
UPDATE users SET role='admin' WHERE email='user@example.com';
```

### Просмотр использования
```sql
SELECT org_id, SUM(amount) as total_spent, COUNT(*) as requests
FROM billing_ledger
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY org_id ORDER BY total_spent DESC;
```

## Мониторинг

- **Grafana:** http://GRAFANA_HOST:30300 (admin/admin)
- **Prometheus:** http://PROMETHEUS_HOST:30909
- **Gateway метрики:** http://GATEWAY_HOST:30900/metrics

## Обновление моделей

1. Добавить модель в `configs/gateway/config.yaml.template`
2. Создать vLLM deployment в `k8s/`
3. `kubectl apply -f k8s/vllm-new/`
4. Обновить Gateway ConfigMap: `kubectl create configmap gateway-config --from-file=catalog.yaml -n aither --dry-run=client -o yaml | kubectl apply -f -`
5. `kubectl rollout restart deploy/gateway -n aither`
