#!/bin/bash
# rotate-keys.sh — ротация API-ключей организации
set -e

if [ -z "$1" ]; then
    echo "Использование: $0 <org_id>"
    echo "  Создаёт новый API-ключ и отзывает все старые"
    exit 1
fi

ORG_ID="$1"
echo "=== Ротация ключей для org=$ORG_ID ==="

# Отозвать все ключи
kubectl exec -n aither deploy/postgres -- psql -U aither aither -c \
    "UPDATE api_keys SET revoked=TRUE WHERE org_id='$ORG_ID';"

echo "✅ Старые ключи отозваны"
echo ""
echo "Создайте новый ключ через портал или API:"
echo "  POST /api/v1/orgs/$ORG_ID/keys"
