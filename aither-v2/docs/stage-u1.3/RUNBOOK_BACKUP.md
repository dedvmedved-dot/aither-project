# RUNBOOK: Backup

## Current Limitations
**WARNING:** There is no automated backup. SQLite databases are stored on pod ephemeral storage and WILL BE LOST on pod restart/recreate.

## Manual Backup Procedure

### 1. Backup ai-platform Database
```bash
ssh n8 "kubectl exec -n aither-inference deploy/aither-ai-platform -- \
  python3 -c \"import sqlite3; conn=sqlite3.connect('/data/ai-platform.db'); conn.backup(open('/tmp/backup.db','wb'))\" && \
  kubectl cp aither-inference/\$(kubectl get pods -n aither-inference -l app=aither-ai-platform -o jsonpath='{.items[0].metadata.name}'):/tmp/backup.db ./ai-platform-backup-\$(date +%Y%m%d).db"
```

### 2. Backup Identity Database
```bash
ssh n8 "kubectl exec -n aither-inference deploy/aither-identity -- \
  python3 -c \"import sqlite3; conn=sqlite3.connect('/data/identity.db'); conn.backup(open('/tmp/backup.db','wb'))\" && \
  kubectl cp aither-inference/\$(kubectl get pods -n aither-inference -l app=aither-identity -o jsonpath='{.items[0].metadata.name}'):/tmp/backup.db ./identity-backup-\$(date +%Y%m%d).db"
```

### 3. Backup VPS2 Configuration
```bash
cp /root/nginx-failover.conf ./nginx-failover-backup-$(date +%Y%m%d).conf
cp /root/ssl-cert/cert.pem ./cert-backup-$(date +%Y%m%d).pem
```

### 4. Repository (always backed up)
```bash
cd /root/aither-project/aither-v2
git status  # Ensure all changes committed
```

### 5. Store Backups
Copy backups to a safe location (separate machine or cloud storage).

## Backup Verification
```bash
sqlite3 ai-platform-backup-*.db "SELECT COUNT(*) FROM models"
sqlite3 ai-platform-backup-*.db "SELECT COUNT(*) FROM api_keys"
```
Should return non-zero counts.
