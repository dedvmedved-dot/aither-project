#!/bin/bash
# restore.sh — восстановление из резервной копии
set -e

if [ -z "$1" ]; then
    echo "Использование: $0 <каталог_бэкапа>"
    ls -d /backup/aither/*/ 2>/dev/null | sort -r
    exit 1
fi

BACKUP_DIR="$1"
echo "=== Восстановление из $BACKUP_DIR ==="

if [ -f "$BACKUP_DIR/aither_db.sql" ]; then
    echo "Восстановление PostgreSQL..."
    kubectl exec -i -n aither deploy/postgres -- psql -U aither aither < "$BACKUP_DIR/aither_db.sql"
    echo "✅ БД восстановлена"
fi

if [ -f "$BACKUP_DIR/k8s-configmaps.yaml" ]; then
    echo "Восстановление ConfigMaps..."
    kubectl apply -f "$BACKUP_DIR/k8s-configmaps.yaml"
    echo "✅ ConfigMaps восстановлены"
fi

echo ""
echo "Перезапуск подов..."
kubectl rollout restart deploy -n aither

echo "✅ Восстановление завершено"
