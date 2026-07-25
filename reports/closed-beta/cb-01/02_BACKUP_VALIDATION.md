# CB-01 Backup Validation

**Timestamp:** 2026-07-25 00:57 UTC

## Backup Contents

### ai-platform.db
- Location: /root/backups/cb-01-pre-launch/ai-platform.db
- Tables: models (2), api_keys (21), assistants (98), conversations (99), messages (1013)
- Dumped via Python sqlite3.backup() from running pod
- SQLite integrity: PASS

### identity.db
- Location: /root/backups/cb-01-pre-launch/identity.db
- Tables: users (1), sessions (3+)
- Dumped via Python sqlite3.backup() from running pod
- SQLite integrity: PASS

## Verification Commands

```bash
# Verify backup integrity
sqlite3 /root/backups/cb-01-pre-launch/ai-platform.db "SELECT COUNT(*) FROM api_keys"
sqlite3 /root/backups/cb-01-pre-launch/identity.db "SELECT COUNT(*) FROM users"
```

## Restore Procedure
See: `docs/stage-u1.3/RUNBOOK_RESTORE.md`

## Security
- Backups stored on host filesystem, not in Git
- No API key values in backup documentation (only table counts)
- chmod 600 on backup directory
