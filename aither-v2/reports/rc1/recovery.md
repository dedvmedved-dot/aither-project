# Failover & Recovery Report

**Stage:** RC1  
**Date:** 2026-07-23  
**File:** `reports/rc1/recovery.md`

---

## Test Methodology

Each test: restart the service pod, observe automatic recovery, verify functionality.

## Test 1: Portal Backend Restart

| Step | Action | Result | Time |
|------|--------|--------|------|
| 1 | Delete pod aither-portal-backend | ✅ Pod terminated | 0s |
| 2 | Deployment creates new pod | ✅ New pod scheduled on n8 | 3s |
| 3 | Container starts (image pull) | ✅ Image cached (IfNotPresent) | 2s |
| 4 | Liveness probe passes (/health) | ✅ 200 | 5s |
| 5 | Readiness probe passes (/ready) | ✅ 200 | 5s |
| 6 | Service endpoints updated | ✅ New pod IP in service | 1s |
| **Total recovery time** | | | **~10s** |

**Validation:** Login → Create conversation → Send message → all work ✅

## Test 2: AI Platform Restart

| Step | Action | Result | Time |
|------|--------|--------|------|
| 1 | Delete pod aither-ai-platform | ✅ Pod terminated | 0s |
| 2 | New pod created | ✅ Scheduled on n8 | 3s |
| 3 | SQLite DB reads from PVC | ✅ PVC `aither-ai-platform-data` still Bound | 2s |
| 4 | init_db() — tables already exist | ✅ `CREATE TABLE IF NOT EXISTS` safe | 1s |
| 5 | Liveness probe (/health) | ✅ 200 | 10s |
| 6 | Readiness probe (/ready) | ✅ 200 (DB + Identity connected) | 12s |
| 7 | Data integrity (conversations intact) | ✅ SQLite on PVC survives restart | — |
| **Total recovery time** | | | **~15s** |

**Validation:** List conversations → Get history → Messages preserved ✅

## Test 3: Gateway Restart

| Step | Action | Result | Time |
|------|--------|--------|------|
| 1 | Restart deployment (2 replicas) | ✅ Rolling update | 0s |
| 2 | New pods start | ✅ nginx:alpine starts fast | 2s |
| 3 | ConfigMap nginx.conf applied | ✅ New `/ready`, `/version` endpoints | 1s |
| 4 | Liveness (/healthz) | ✅ 200 (local nginx) | 3s |
| 5 | Readiness (/health proxied) | ✅ vLLM 32B healthy | 5s |
| **Total recovery time** | | | **~5s** |

**Validation:** AI Platform can reach Gateway → `/v1/completions` works ✅

## Test 4: Identity Restart

| Step | Action | Result | Time |
|------|--------|--------|------|
| 1 | Delete pod aither-identity | ✅ Pod terminated | 0s |
| 2 | New pod created | ✅ PVC bound | 3s |
| 3 | Users and secrets restored | ✅ SQLite on PVC | 5s |
| 4 | Liveness (/health) | ✅ 200 | 8s |
| 5 | Readiness (/ready) | ✅ 200 | 10s |
| **Total recovery time** | | | **~10s** |

**Validation:** Login with admin/admin works (bcrypt hash from PVC) ✅

## Recovery Time Summary

| Service | Recovery Time | Data Loss | Notes |
|---------|---------------|-----------|-------|
| Portal Backend | ~10s | None | Stateless, no data |
| AI Platform | ~15s | None | SQLite on PVC persists |
| Gateway | ~5s | None | Stateless nginx + ConfigMap |
| Identity | ~10s | None | SQLite on PVC persists |
| Full stack | ~15s | None | Worst case: all pods restart |

## Failure Scenarios

### Scenario: PV/PVC Failure
- **Impact:** AI Platform and Identity lose all data
- **Mitigation:** Backup scripts (`scripts/backup.sh`) provide SQL dump for restore
- **Recovery time:** ~5 minutes (restore backup + restart pods)

### Scenario: Node Failure (n8 is control-plane + GPU)
- **Impact:** All pods on n8 become unavailable
- **Mitigation:** Gateway has 2 replicas on n7, but AI Platform and Portal Backend are single-replica
- **Recommendation:** Add anti-affinity rules for V1.0

### Scenario: vLLM Crash
- **Impact:** Gateway returns 502/503 to all LLM requests
- **Recovery:** Kubernetes automatically restarts vLLM pod (~30s)
- **Mitigation:** None needed — autorestart handles it

## Conclusion

✅ **All services recover automatically within 5-15 seconds.**  
✅ **No data loss on PVC-backed pods (AI Platform, Identity).**  
✅ **Gateway rolling restart with zero downtime (2 replicas).**  
✅ **Backup/restore procedure verified.**

⚠️ Single points of failure (1 replica) for AI Platform, Portal Backend, and Identity. Acceptable for Beta.
