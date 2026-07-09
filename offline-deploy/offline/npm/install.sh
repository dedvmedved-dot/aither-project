#!/bin/bash
# npm-install.sh — установка NPM-пакета портала офлайн
set -e

echo "=== Установка NPM-пакета портала ==="
cd /root/aither-project/portal

if [ -f "../offline-deploy/offline/npm/portal-offline.tgz" ]; then
    npm install ../offline-deploy/offline/npm/portal-offline.tgz
    echo "✅ Портал установлен из офлайн-пакета"
else
    npm install
    echo "⚠️ Установка из интернета (офлайн-пакет не найден)"
fi
