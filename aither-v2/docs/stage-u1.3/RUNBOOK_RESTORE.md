# RUNBOOK: Restore

## Current Limitations
No automated restore procedure. Manual database copy required.

## ai-platform Database Restore

### 1. Copy Backup to Pod
```bash
BACKUP_FILE="./ai-platform-backup-20260724.db"
POD=$(ssh n8 "kubectl get pods -n aither-inference -l app=aither-ai-platform -o jsonpath='{.items[0].metadata.name}'")
ssh n8 "kubectl cp $BACKUP_FILE aither-inference/$POD:/tmp/restore.db"
```

### 2. Restore Database in Pod
```bash
ssh n8 "kubectl exec -n aither-inference $POD -- python3 -c \"
import sqlite3
# Stop writes, replace DB
conn = sqlite3.connect('/data/ai-platform.db')
conn.close()
import shutil
shutil.copy('/tmp/restore.db', '/data/ai-platform.db')
print('Restored')
\""
```

### 3. Restart Pod to Ensure Clean State
```bash
ssh n8 "kubectl rollout restart deploy/aither-ai-platform -n aither-inference"
```

## Identity Database Restore
Same procedure, replacing `aither-ai-platform` with `aither-identity`.

## VPS2 Configuration Restore

### nginx Config
```bash
cp ./nginx-failover-backup-*.conf /root/nginx-failover.conf
docker exec aither-failover-nginx nginx -t
docker exec aither-failover-nginx nginx -s reload
```

### SSL Certificates
```bash
cp ./cert-backup-*.pem /root/ssl-cert/cert.pem
cp ./key-backup-*.pem /root/ssl-cert/key.pem
docker restart aither-failover-nginx
```

## Verification After Restore
Run `03_HEALTH_CHECKLIST.md`.
