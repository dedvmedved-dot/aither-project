# CHANGE-0022-C3 Runtime Git Delta

**Date:** 2026-07-27
**Base Commit:** 801ca390a15975ad360238414d2a059e2092daf2
**Branch:** aither-v2

## Changed Files

```
 gateway/rate_limit.py                           | 171 → 282 lines (+111)  — Complete rewrite: fail-closed design
 gateway/gateway.py                              |   1 line changed       — Fail-closed on Redis error (line 690)
 gateway/siem_receiver.py                        | 223 → 340 lines (+117)  — Production rewrite: SQLite, auth, retention, backups
 gateway/app.py                                  | 418 → 773 lines (+355)  — RAG endpoints with full security pipeline + admin restore
 gateway/config.py                               |   1 line added         — chroma_url in Settings
 aither-v2/deploy/siem/deployment.yaml           | 202 → 247 lines (+45)  — Production manifests: PVC, NP, Secret, Probes, Pinned image
 aither-v2/deploy/vault/deployment.yaml          | 182 → 285 lines (+103) — TLS, NP, SA, audit PVC, policies, init procedure
 reports/evidence/CHANGE-0022/10-rate-limit/RL-EVIDENCE.md   | new  — 14 evidence records
 reports/evidence/CHANGE-0022/11-siem/SIEM-EVIDENCE.md       | new  — 10 evidence records
 reports/evidence/CHANGE-0022/12-vault/VAULT-EVIDENCE.md     | new  — 11 evidence records
 reports/evidence/CHANGE-0022/13-rag/RAG-EVIDENCE.md         | new  — 10 evidence records
 reports/CHANGE-0022-C3-pre-cutover-candidate.md             | new  — Cutover candidate report
 reports/CHANGE-0022-C3-test-matrix.md                       | new  — 45-test matrix
 reports/CHANGE-0022-C3-security-incident.md                 | new  — 5 security findings
 reports/CHANGE-0022-C3-runtime-git-delta.md                 | new  — This file
 reports/CHANGE-0022-C3-canary-report.md                     | new  — Canary deployment report
```

## Code Delta Summary

| Metric | Value |
|---|---|
| Files modified | 6 |
| Files created | 10 |
| Total files changed | 16 |
| Lines added | ~1000+ |
| Lines removed | ~150 |
| Net change | +850 lines |

## Key Code Changes (Diff Highlights)

### `gateway/rate_limit.py`
- Removed fallback safe limits (lines 141-147 deleted)
- Added `_is_cache_valid()` with timestamp-based TTL
- Added `invalidate_tier_cache()` and `set_tier_cache_ttl()`
- Added `_build_redis_keys()` with org+key+model dimensions
- Added `check_org_quota()` and `check_api_key_quota()`
- `check_rate_limit()` now returns 3-tuple: `(ok, reason, details)`
- All error paths return explicit deny — no fallback

### `gateway/gateway.py`
- Line 690-691: `except: pass` → `except: self._json(503, "rate_limit_unavailable")`

### `gateway/siem_receiver.py`
- Added SQLite storage with WAL mode
- Added `store_event()` with hash-based dedup
- Added `run_retention()` — hourly cleanup
- Added `backup_events()` — gzip JSON backups
- Added `forward_event()` — UDP syslog relay
- Added `_check_auth()` on all query endpoints
- Added `/ready` endpoint with dependency checks
- Added `/events/search` with type/limit params
- Added `/admin/backup` and `/admin/retention` POST triggers
- 12 → 16 required event types

### `gateway/app.py`
- Added `_has_rag_scope()` — RAG scope authorization
- Added `_check_tier_rag()` — PG-backed tier RAG check
- Added `_get_chroma()` and `_get_ef()` — lazy clients
- Rewrote all 5 RAG endpoints with full pipeline:
  - `GET /v1/rag/status` — auth+scope+tier
  - `POST /v1/rag/ingest` — auth+scope+tier+security_ingress+org_isolation
  - `POST /v1/rag/query` — auth+scope+tier+security_ingress+org_isolation+security_egress
  - `POST /v1/rag/hybrid-query` — same + wiki_graph
  - `POST /v1/rag/wiki-ingest` — auth+scope+tier
- Added `_rag_pipeline()` shared implementation

### Deploy Manifests
- SIEM: PVC (20Gi), Secret for admin key, NetworkPolicy, pinned image, probes
- Vault: TLS Secret mount, audit PVC (5Gi), NetworkPolicy, non-root securityContext, projected SA token

## Files NOT Changed (by design)
- Production BFF routing — per emergency mode rules
- `gateway/catalog.yaml` — no model changes
- `gateway/billing.py` — no billing logic changes
- `gateway/security.py` / `security_egress.py` — reused, not modified
- Portal UI (`static/index.html`) — no UI changes
