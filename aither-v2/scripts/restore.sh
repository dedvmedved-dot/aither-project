#!/bin/bash
# Aither Restore Script
# Stage: RC1
# Description: Restore Aither platform data from backup (SQL format)
# Usage: ./scripts/restore.sh <backup_directory>

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <backup_directory>"
    exit 1
fi

BACKUP_PATH="$1"
NAMESPACE="${NAMESPACE:-aither-inference}"

if [ ! -d "${BACKUP_PATH}" ]; then
    echo "Error: Backup directory not found: ${BACKUP_PATH}"
    exit 1
fi

echo "=== Aither Restore ==="
echo "Restoring from: ${BACKUP_PATH}"

# 1. Restore AI Platform Database
if [ -f "${BACKUP_PATH}/ai-platform.sql" ]; then
    echo "[1/2] Restoring AI Platform database..."
    AI_POD=$(kubectl get pod -n ${NAMESPACE} -l app=aither-ai-platform -o jsonpath='{.items[0].metadata.name}')
    kubectl cp "${BACKUP_PATH}/ai-platform.sql" ${NAMESPACE}/${AI_POD}:/tmp/ai-platform-restore.sql
    kubectl exec -n ${NAMESPACE} ${AI_POD} -- sh -c '
        python3 -c "
import sqlite3
conn = sqlite3.connect(\"/data/ai-platform.db\")
conn.executescript(open(\"/tmp/ai-platform-restore.sql\").read())
conn.commit()
conn.close()
"
        rm -f /tmp/ai-platform-restore.sql
    '
    echo "  ✅ AI Platform database restored"
fi

# 2. Restore Identity Database
if [ -f "${BACKUP_PATH}/identity.sql" ]; then
    echo "[2/2] Restoring Identity database..."
    ID_POD=$(kubectl get pod -n ${NAMESPACE} -l app=aither-identity -o jsonpath='{.items[0].metadata.name}')
    kubectl cp "${BACKUP_PATH}/identity.sql" ${NAMESPACE}/${ID_POD}:/tmp/identity-restore.sql
    kubectl exec -n ${NAMESPACE} ${ID_POD} -- sh -c '
        python3 -c "
import sqlite3
conn = sqlite3.connect(\"/data/identity.db\")
conn.executescript(open(\"/tmp/identity-restore.sql\").read())
conn.commit()
conn.close()
"
        rm -f /tmp/identity-restore.sql
    '
    echo "  ✅ Identity database restored"
fi

echo ""
echo "=== Restore Complete ==="
echo "Restart pods to apply restored data:"
echo "  kubectl rollout restart deployment/aither-ai-platform -n ${NAMESPACE}"
echo "  kubectl rollout restart deployment/aither-identity -n ${NAMESPACE}"
