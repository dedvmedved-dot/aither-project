#!/bin/bash
# create-admin.sh — создание первого администратора
set -e

echo "=== Создание администратора Aither ==="
echo "Выполните на VPS2 (портал):"
echo ""
echo "cd /root/aither-project/portal"
echo "node -e \""
echo "  const { createOrg, createApiKey } = require('./dist/admin');"
echo "  createOrg({ name: 'Аdministration', inviteCode: 'admin-2026' })"
echo "    .then(org => createApiKey(org.org_id, 'admin-key'))"
echo "    .then(key => console.log('Admin API Key:', key.api_key))"
echo "    .catch(err => console.error(err));"
echo "\""
echo ""
echo "После создания администратора:"
echo "  1. Войдите в портал через OAuth"
echo "  2. Используйте инвайт-код 'admin-2026' для входа в организацию"
echo "  3. Назначьте роль администратора через БД:"
echo "     UPDATE users SET role='admin' WHERE email='ваш@email';"
