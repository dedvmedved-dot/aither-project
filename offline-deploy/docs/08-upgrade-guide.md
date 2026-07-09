# 08-upgrade-guide.md — Процедура обновления

## Обновление платформы

### 1. Бэкап

```bash
bash scripts/backup.sh
```

### 2. Обновление кода

```bash
cd /root/aither-project
git pull origin main
```

### 3. Обновление K8s-компонентов

```bash
# Обновить манифесты
kubectl apply -f offline-deploy/k8s/

# Перезапустить поды с новым кодом/конфигом
kubectl rollout restart deploy -n aither
```

### 4. Обновление портала

```bash
cd portal
npm install
npm run build
# Перезапустить BFF
systemctl restart aither-bff
```

### 5. Обновление Nginx

```bash
cp offline-deploy/configs/nginx/nginx.conf /etc/nginx/sites-enabled/aither
nginx -t && systemctl reload nginx
```

### 6. Проверка

```bash
make test
bash scripts/health-check.sh
```

## Откат

```bash
bash scripts/restore.sh /backup/aither/YYYY-MM-DD_HHMM
```

## Обновление моделей

1. Скачать новую модель на машине с интернетом
2. Перенести на носителе → `/mnt/models/NEW_MODEL/`
3. Создать `k8s/vllm-NEW/deployment.yaml`
4. `kubectl apply -f k8s/vllm-NEW/`
5. Добавить в `configs/gateway/config.yaml.template`
6. Обновить Gateway ConfigMap + restart

## Обновление GPU-драйвера

```bash
apt-get update && apt-get install -y nvidia-driver-580
reboot
nvidia-smi  # проверить новую версию
```

## Миграция БД

```bash
# Применить миграции (если schema.sql изменился)
kubectl exec -i -n aither deploy/postgres -- psql -U aither aither < scripts/seed-data.sql
```
