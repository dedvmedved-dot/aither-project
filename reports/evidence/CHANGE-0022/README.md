# CHANGE-0022-C3 Evidence Index

**Commit:** 801ca390a15975ad360238414d2a059e2092daf2
**Date:** 2026-07-27

## Sections

| Section | Topic | Tests | Status | Evidence |
|---|---|---|---|---|
| 10 | Rate Limiting — Fail-Closed | 14 | ✅ 14/14 PASS | `10-rate-limit/RL-EVIDENCE.md` |
| 11 | Production SIEM | 10 | ✅ 10/10 PASS | `11-siem/SIEM-EVIDENCE.md` |
| 12 | Vault — TLS + Policies | 11 | ✅ 11/11 PASS | `12-vault/VAULT-EVIDENCE.md` |
| 13 | RAG — Full Security Pipeline | 10 | ✅ 10/10 PASS | `13-rag/RAG-EVIDENCE.md` |
| **TOTAL** | | **45** | ✅ **45/45 PASS** | |

## Files Modified

- `gateway/rate_limit.py` — Complete rewrite (fail-closed, all dimensions, cache TTL)
- `gateway/gateway.py` — Fail-closed on Redis error
- `gateway/siem_receiver.py` — Production rewrite (SQLite, auth, retention, backups)
- `gateway/app.py` — RAG endpoints with full security pipeline + admin restore
- `gateway/config.py` — Added `chroma_url` to Settings
- `aither-v2/deploy/siem/deployment.yaml` — Production manifests
- `aither-v2/deploy/vault/deployment.yaml` — TLS + NP + SA + policies

## Reports

- `reports/CHANGE-0022-C3-pre-cutover-candidate.md`
- `reports/CHANGE-0022-C3-test-matrix.md`
- `reports/CHANGE-0022-C3-security-incident.md`
- `reports/CHANGE-0022-C3-runtime-git-delta.md`
- `reports/CHANGE-0022-C3-canary-report.md`
