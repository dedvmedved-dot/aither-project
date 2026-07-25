# Aither AI Platform — Руководство по резервному копированию и восстановлению

**Версия:** OPS-01-R1 | **Дата:** 26 июля 2026

---

## 1. Что требуется резервировать

| Компонент | Тип | Приоритет | Метод |
|-----------|-----|-----------|-------|
| Portal DB (PostgreSQL, VPS2) | Данные | Критический | pg_dump |
| Aither DB (PostgreSQL, K8s) | Данные | Критический | pg_dump |
| ConfigMaps (5 шт.) | Конфигурация | Высокий | kubectl get -o yaml |
| Secrets (4 шт.) | Креды | Критический | kubectl get -o yaml (внешнее хранение) |
| Redis (rate-limit) | Кеш | Низкий | Не требует (пересоздаётся) |

---

## 2. Резервное копирование

### PostgreSQL (VPS2 Portal DB)

```bash
ssh vps2 "pg_dump -U portal -h 127.0.0.1 portal > /backup/portal_db_$(date +%Y%m%d).sql"
```

### PostgreSQL (K8s Aither DB)

```bash
kubectl exec -n aither-inference deployment/postgres -- pg_dump -U aither aither > /backup/aither_db_$(date +%Y%m%d).sql
```

### ConfigMaps

```bash
for cm in aither-bff-config aither-portal-config aither-portal-frontend-config nginx-gateway-32b; do
    kubectl get configmap $cm -n aither-inference -o yaml > /backup/cm-${cm}-$(date +%Y%m%d).yaml
done
```

### Secrets

```bash
for secret in aither-bff-auth aither-identity-secret aither-ai-platform-secret vllm-api-key; do
    kubectl get secret $secret -n aither-inference -o yaml > /backup/secret-${secret}-$(date +%Y%m%d).yaml
done
```

---

## 3. Расписание

| Частота | Что |
|---------|-----|
| Ежедневно | PostgreSQL дампы, ConfigMaps |
| При изменении | Secrets, ConfigMaps |
| Еженедельно | Полный снапшот |

---

## 4. Восстановление

### PostgreSQL

```bash
# VPS2 Portal DB
ssh vps2 "psql -U portal -h 127.0.0.1 portal < /backup/portal_db_YYYYMMDD.sql"

# K8s Aither DB
kubectl exec -n aither-inference deployment/postgres -i -- psql -U aither aither < /backup/aither_db_YYYYMMDD.sql
```

### ConfigMaps

```bash
kubectl apply -f /backup/cm-aither-portal-config-YYYYMMDD.yaml
kubectl rollout restart deployment/aither-portal -n aither-inference
```

### Secrets

```bash
kubectl apply -f /backup/secret-aither-bff-auth-YYYYMMDD.yaml
kubectl rollout restart deployment/aither-bff -n aither-inference
```

---

## 5. Disaster Recovery

При полной потере кластера:

1. Развернуть K8s кластер заново
2. Применить все Secrets
3. Применить все ConfigMaps
4. Развернуть компоненты в порядке: vLLM → Redis → AI Platform → Identity → BFF → Portal
5. Восстановить PostgreSQL из дампа
6. Проверить доступность портала и моделей
