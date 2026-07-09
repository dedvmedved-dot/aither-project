#!/bin/bash
# save.sh — сохранить Docker-образы в tar-архив
set -e

IMAGES=(
    "postgres:16"
    "redis:7-alpine"
    "vllm/vllm-openai:latest"
    "chromadb/chroma:latest"
    "prom/prometheus:latest"
    "grafana/grafana:latest"
    "python:3.11-slim"
    "node:20-alpine"
    "nginx:alpine"
)

OUTPUT="images.tar.gz"

echo "=== Сохранение Docker-образов ==="
for img in "${IMAGES[@]}"; do
    echo "  docker pull $img..."
    docker pull "$img" 2>/dev/null || echo "    ⚠️ не удалось (нет интернета?)"
done

echo ""
echo "Упаковка в $OUTPUT..."
docker save "${IMAGES[@]}" | gzip > "$OUTPUT" 2>/dev/null || {
    echo "⚠️ docker save не удался. Сохраняем только то что есть локально..."
    docker save $(docker images --format '{{.Repository}}:{{.Tag}}' | grep -E 'postgres|redis|vllm|chroma|prometheus|grafana|python:3.11|node:20|nginx') | gzip > "$OUTPUT"
}

echo "✅ Образы сохранены: $OUTPUT ($(du -sh $OUTPUT | cut -f1))"
