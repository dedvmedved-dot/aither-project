#!/bin/bash
# install.sh — установить pip-пакеты из офлайн-пакета
set -e

DEST="packages"

if [ ! -d "$DEST" ] || [ -z "$(ls -A $DEST 2>/dev/null)" ]; then
    echo "❌ Каталог $DEST пуст или не существует"
    echo "Скопируйте packages/ с машины с интернетом"
    exit 1
fi

echo "=== Установка pip-пакетов (офлайн) ==="
pip3 install --no-index --find-links="$DEST" -r requirements.txt
echo "✅ Пакеты установлены"
