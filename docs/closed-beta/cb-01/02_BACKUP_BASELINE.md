# CB-01 Backup Baseline

**Date:** 2026-07-25 00:57 UTC
**Pre-access backup created before user provisioning.**

---

## Backup Artifacts

| Component | Location | Size | Status |
|---|---|---|---|
| ai-platform.db | /root/backups/cb-01-pre-launch/ai-platform.db | Verified | ✅ Created |
| identity.db | /root/backups/cb-01-pre-launch/identity.db | Verified | ✅ Created |
| Gateway config (nginx) | Docker container: aither-failover-nginx | Active | ✅ Running |
| K8s manifests | /root/aither-project/k8s/ | In repo | ✅ Committed |
| VPS2 config | docker-compose.vps2.yml | In repo | ✅ Committed |
| TLS config | /root/ssl-cert/ | On host | ✅ Present |
| Release manifest | docs/stage-u1.4/01_RELEASE_MANIFEST.md | In repo | ✅ Committed |
| Commit SHA | d07011d65b648713fb97979765d0d0d1106c4911 | In repo | ✅ Committed |

---

## Database Contents (Pre-Launch)

### ai-platform.db
- models: 2 (qwen-14b, qwen-32b-base)
- api_keys: 21 (16 existing + 5 new beta keys)
- assistants: 98
- conversations: 99
- messages: 1013

### identity.db
- users: 1 (admin)

---

## Backup Verification

| Check | Status |
|---|---|
| File exists | ✅ |
| Size non-zero | ✅ |
| SQLite readable | ✅ |
| Stored outside pod filesystem | ✅ |
| Restore procedure documented (U1.3 RUNBOOK_RESTORE.md) | ✅ |
| Secrets NOT in Git | ✅ |

---

## Restore Procedure Reference
See: `docs/stage-u1.3/RUNBOOK_RESTORE.md`

---

**Status: PASS**
---
*Evidence: reports/closed-beta/cb-01/02_BACKUP_VALIDATION.md*
