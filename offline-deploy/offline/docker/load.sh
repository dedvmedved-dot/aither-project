#!/bin/bash
# load.sh — загрузить Docker-образы из tar-архива
set -e

ARCHIVE="images.tar.gz"

if [ ! -f "$ARCHIVE" ]; then
    echo "❌ $ARCHIVE не найден"
    echo "Скопируйте images.tar.gz с машины с интернетом:"
    echo "  scp images.tar.gz user@target:/path/to/offline-deploy/offline/docker/"
    exit 1
fi

echo "=== Загрузка Docker-образов ==="
gunzip -c "$ARCHIVE" | docker load
echo "✅ Образы загружены"

echo ""
echo "Проверка:"
docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}' | grep -E 'postgres|redis|vllm|chroma|prometheus|grafana|python|node|nginx'
