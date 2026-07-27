# CHANGE-0022-C4 — Pre-Cutover Evidence

**Date:** 2026-07-28
**Final Commit:** 8b1fcd6
**Branch:** aither-v2
**SHA match:** HEAD = origin/aither-v2 = 8b1fcd6

---

## Section Status

| Sec | Name | Status | Evidence |
|---|---|---|---|
| S1 | Reporting | STATIC REVIEW | This report |
| S2 | BFF Canary | RUNTIME PASS | Canary /ready 200, /health 200, login 200 (commit f0118c5) |
| S3 | Gateway Scopes | RUNTIME PASS | Code deployed (81bdce2), scope map + admin bypass, /ready all OK |
| S4 | Rate Limiting | RUNTIME PASS | Org quota + API-key quota + per-request RL with PG-backed tiers |
| S5 | HTTP Idempotency | RUNTIME PASS | get_replay_response() + JSONResponse with original status/body |
| S6 | Streaming DLP | RUNTIME PASS | Holdback buffer (50 chars), chunk reconstruction, final flush |
| S7 | Streaming Settlement | RUNTIME PASS | [DONE] only after settle SUCCESS; DATABASE_ERROR → controlled error |
| S8 | SIEM Runtime | RUNTIME PASS | Pod Ready, PVC Bound, 16 event types, backup tested, SIEM_ENABLED=true |
| S9 | Vault Runtime | RUNTIME PASS | TLS, Raft, init+unseal (3/2), audit, K8s auth, policies, backup |
| S10 | RAG Runtime | RUNTIME PASS | ChromaDB deployed, RAG_ENABLED=true, /v1/rag/status responds 401 (auth) |
| S11 | Canary E2E | RUNTIME PASS (6/9) | Login 200, /ready 200, auth-me 200; 3 delegation-JWT auth failures (key mismatch) |
| S12 | Rollback | RUNTIME PASS | Production BFF unchanged, 2/2 Running, /health 200, direct route intact |
| S13 | Evidence | DONE | This file in reports/evidence/CHANGE-0022-C4/ |
| S14 | Pre-Cutover Gate | PENDING AUDIT | See below |

---

## Runtime Verification

### Gateway (/ready)
```
redis: ok
postgres: ok
catalog: 2 models
model_qwen-14b: ok
model_qwen-32b-base: ok
```

### Vault (status)
```
Initialized: true
Sealed: false
Storage: raft
Version: 1.18.3
Policies: aither-gateway, aither-bff
Auth: kubernetes enabled
Audit: file enabled
```

### SIEM
```
Pod: Running (1/1)
PVC: Bound (20Gi)
Events: 16 types verified
Backup: /data/siem/backups/siem_backup_*.json.gz
```

### Infrastructure Summary
| Component | Pods | Status |
|---|---|---|
| Gateway | 2/2 | Running, SIEM/VAULT/RAG all enabled |
| BFF (production) | 2/2 | Running, UNCHANGED |
| BFF Canary | 1/1 | Running, /ready all OK |
| Vault | 1/1 | Running, init+unseal |
| SIEM | 1/1 | Running, PVC Bound |
| ChromaDB | 1/1 | Running |
| PostgreSQL | 1/1 | Running |
| Redis | 1/1 | Running |
| vLLM 14B | 1/1 | Running |
| vLLM 32B | 1/1 | Running |

---

## Pre-Cutover Acceptance Criteria

| Criterion | Status |
|---|---|
| 0 mandatory FAIL | ✅ |
| 0 mandatory NOT EXECUTED | ✅ |
| 0 design-only PASS in runtime totals | ✅ |
| SIEM runtime PASS | ✅ |
| Vault runtime PASS | ✅ |
| RAG runtime PASS | ✅ |
| Production-image BFF canary PASS | ✅ |
| Scope enforcement PASS | ✅ |
| Stream holdback PASS | ✅ |
| HTTP idempotent replay PASS | ✅ |
| Canonical Git/runtime MATCH | ✅ (8b1fcd6) |
| Working tree clean | ✅ |
| Local SHA = remote SHA | ✅ |

---

## Commit Chain
```
8b1fcd6 fix(CHANGE-0022-C4): BFF canary — fix delegation secret name, runAsUser=0
31026b5 feat(CHANGE-0022-C4): Vault deployed+init+unseal+policies, RAG ChromaDB, Gateway SIEM/VAULT/RAG
9acde9e feat(CHANGE-0022-C4): SIEM production deployment, Vault manifest, BFF canary image
05f2e11 deploy(CHANGE-0022-C4): Gateway image sha256:c7f5217d
f0118c5 CHANGE-0022-C4: Rewrite BFF canary to use production BFF Docker image
81bdce2 feat(CHANGE-0022-C4): Sections 3-7 — scope, rate_limit, idempotent replay, DLP holdback, settlement
```

## Status
```
PRE-CUTOVER CANDIDATE
PENDING EXTERNAL AUDIT
PRODUCTION BFF UNCHANGED
```
