#!/bin/bash
# Aither Backup Script
# Stage: RC1
# Description: Automated backup of Aither platform data
# Usage: ./scripts/backup.sh

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/root/backups/aither}"
NAMESPACE="${NAMESPACE:-aither-inference}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="${BACKUP_DIR}/${TIMESTAMP}"
KUBECTL="kubectl"

echo "=== Aither Backup: ${TIMESTAMP} ==="
echo "Backup directory: ${BACKUP_PATH}"
mkdir -p "${BACKUP_PATH}"

# 1. AI Platform SQLite Database
echo "[1/4] Backing up AI Platform database..."
AI_POD=$(${KUBECTL} get pod -n ${NAMESPACE} -l app=aither-ai-platform -o jsonpath='{.items[0].metadata.name}')
${KUBECTL} exec -n ${NAMESPACE} ${AI_POD} -- sh -c 'python3 -c "import sqlite3; conn=sqlite3.connect(\"/data/ai-platform.db\"); f=open(\"/tmp/ai-platform-backup.sql\",\"w\"); [f.write(l+\"\n\") for l in conn.iterdump()]; f.close(); conn.close()"'
${KUBECTL} cp ${NAMESPACE}/${AI_POD}:/tmp/ai-platform-backup.sql "${BACKUP_PATH}/ai-platform.sql"
${KUBECTL} exec -n ${NAMESPACE} ${AI_POD} -- rm -f /tmp/ai-platform-backup.sql
echo "  ✅ AI Platform database backed up (${BACKUP_PATH}/ai-platform.sql)"

# 2. Identity SQLite Database  
echo "[2/4] Backing up Identity database..."
ID_POD=$(${KUBECTL} get pod -n ${NAMESPACE} -l app=aither-identity -o jsonpath='{.items[0].metadata.name}')
${KUBECTL} exec -n ${NAMESPACE} ${ID_POD} -- sh -c 'python3 -c "import sqlite3; conn=sqlite3.connect(\"/data/identity.db\"); f=open(\"/tmp/identity-backup.sql\",\"w\"); [f.write(l+\"\n\") for l in conn.iterdump()]; f.close(); conn.close()"'
${KUBECTL} cp ${NAMESPACE}/${ID_POD}:/tmp/identity-backup.sql "${BACKUP_PATH}/identity.sql"
${KUBECTL} exec -n ${NAMESPACE} ${ID_POD} -- rm -f /tmp/identity-backup.sql
echo "  ✅ Identity database backed up (${BACKUP_PATH}/identity.sql)"

# 3. Kubernetes Configuration (all manifests in aither-v2)
echo "[3/4] Backing up Kubernetes configuration..."
${KUBECTL} get configmap -n ${NAMESPACE} -o yaml > "${BACKUP_PATH}/configmaps.yaml"
${KUBECTL} get secret -n ${NAMESPACE} -o yaml > "${BACKUP_PATH}/secrets.yaml"
${KUBECTL} get deployment -n ${NAMESPACE} -o yaml > "${BACKUP_PATH}/deployments.yaml"
${KUBECTL} get service -n ${NAMESPACE} -o yaml > "${BACKUP_PATH}/services.yaml"
${KUBECTL} get pvc -n ${NAMESPACE} -o yaml > "${BACKUP_PATH}/pvc.yaml"
echo "  ✅ K8s configuration backed up"

# 4. Git repository state
echo "[4/4] Saving git commit reference..."
cd /root/aither-v2/aither-v2
git rev-parse HEAD > "${BACKUP_PATH}/git-head.txt"
git log --oneline -5 > "${BACKUP_PATH}/git-log.txt"
echo "  ✅ Git state saved: $(cat ${BACKUP_PATH}/git-head.txt)"

echo ""
echo "=== Backup Complete ==="
echo "Location: ${BACKUP_PATH}"
ls -la "${BACKUP_PATH}"
