#!/bin/bash
# backup.sh — резервное копирование БД и конфигов
set -e

BACKUP_DIR="/backup/aither/$(date +%Y-%m-%d_%H%M)"
mkdir -p "$BACKUP_DIR"

echo "=== Резервное копирование Aither ==="
echo "Каталог: $BACKUP_DIR"

# PostgreSQL (K8s)
echo "Дамп PostgreSQL..."
kubectl exec -n aither deploy/postgres -- pg_dump -U aither aither > "$BACKUP_DIR/aither_db.sql"

# Конфиги K8s
echo "Конфиги K8s..."
kubectl get configmap -n aither -o yaml > "$BACKUP_DIR/k8s-configmaps.yaml"
kubectl get secret -n aither -o yaml > "$BACKUP_DIR/k8s-secrets.yaml"

# Конфиги портала
echo "Конфиги портала..."
cp /root/aither-project/portal/.env "$BACKUP_DIR/portal.env" 2>/dev/null || echo "  .env не найден"

# Nginx
echo "Nginx..."
cp /etc/nginx/sites-enabled/default "$BACKUP_DIR/nginx-default" 2>/dev/null || echo "  конфиг не найден"

echo ""
echo "✅ Резервная копия: $BACKUP_DIR"
du -sh "$BACKUP_DIR"
