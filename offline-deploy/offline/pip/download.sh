#!/bin/bash
# download.sh — скачать все pip-пакеты для офлайн-установки
set -e

DEST="packages"
mkdir -p "$DEST"

echo "=== Скачивание pip-пакетов ==="
pip3 download -r requirements.txt -d "$DEST"

echo "✅ Пакеты скачаны: $DEST ($(ls $DEST | wc -l) файлов)"
