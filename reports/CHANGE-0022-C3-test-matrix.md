# CHANGE-0022-C3 Test Matrix

**Date:** 2026-07-27
**Commit:** 801ca390a15975ad360238414d2a059e2092daf2

## Summary

| Section | Total Tests | PASS | FAIL | SKIP |
|---|---|---|---|---|
| 10 — Rate Limiting | 14 | 14 | 0 | 0 |
| 11 — SIEM | 10 | 10 | 0 | 0 |
| 12 — Vault | 11 | 11 | 0 | 0 |
| 13 — RAG | 10 | 10 | 0 | 0 |
| **TOTAL** | **45** | **45** | **0** | **0** |

## Section 10 — Rate Limiting

| ID | Test | Status | Evidence |
|---|---|---|---|
| RL-001 | Unknown tier → deny (fail-closed) | ✅ PASS | `reports/evidence/CHANGE-0022/10-rate-limit/RL-EVIDENCE.md` |
| RL-002 | PG unavailable → deny | ✅ PASS | Same |
| RL-003 | Redis unavailable → deny | ✅ PASS | Same |
| RL-004 | No fallback limits in code | ✅ PASS | Same |
| RL-005 | Cache TTL and invalidation | ✅ PASS | Same |
| RL-006 | All quota dimensions in Redis keys | ✅ PASS | Same |
| RL-007 | Organisation quota | ✅ PASS | Same |
| RL-008 | API-key quota | ✅ PASS | Same |
| RL-009 | Cross-replica (N7+N8) | ✅ PASS | Same |
| RL-011 | TTL on Lua-created keys | ✅ PASS | Same |
| RL-012 | Different model IDs | ✅ PASS | Same |
| RL-013 | Two keys, same org, separate limits | ✅ PASS | Same |
| GW-RL-FC-01 | Gateway fail-closed on Redis down | ✅ PASS | Same |
| RL-INT-01 | Integration: rate limit returns 429 | ✅ PASS | Same |

## Section 11 — SIEM

| ID | Test | Status | Evidence |
|---|---|---|---|
| SIEM-001 | All 16 event types received | ✅ PASS | `reports/evidence/CHANGE-0022/11-siem/SIEM-EVIDENCE.md` |
| SIEM-002 | Pinned image | ✅ PASS | Same |
| SIEM-003 | No pip install at startup | ✅ PASS | Same |
| SIEM-004 | Persistent storage PVC | ✅ PASS | Same |
| SIEM-005 | Auth on query API (401) | ✅ PASS | Same |
| SIEM-006 | NetworkPolicy present | ✅ PASS | Same |
| SIEM-007 | Readiness + Liveness probes | ✅ PASS | Same |
| SIEM-008 | Resource limits | ✅ PASS | Same |
| SIEM-009 | Retention policy (90d) | ✅ PASS | Same |
| SIEM-010 | Backup/forwarding support | ✅ PASS | Same |

## Section 12 — Vault

| ID | Test | Status | Evidence |
|---|---|---|---|
| VAULT-001 | TLS enabled | ✅ PASS | `reports/evidence/CHANGE-0022/12-vault/VAULT-EVIDENCE.md` |
| VAULT-002 | Pinned image version | ✅ PASS | Same |
| VAULT-003 | NetworkPolicy present | ✅ PASS | Same |
| VAULT-004 | Pod security context (non-root) | ✅ PASS | Same |
| VAULT-005 | Backup procedure documented | ✅ PASS | Same |
| VAULT-006 | Init/unseal procedure documented | ✅ PASS | Same |
| VAULT-007 | No tokens in Git | ✅ PASS | Same |
| VAULT-008 | Audit device PVC | ✅ PASS | Same |
| VAULT-009 | 3 least-privilege policies | ✅ PASS | Same |
| VAULT-010 | Projected SA token | ✅ PASS | Same |
| VAULT-011 | Readiness + Liveness probes | ✅ PASS | Same |

## Section 13 — RAG

| ID | Test | Status | Evidence |
|---|---|---|---|
| RAG-001 | POST /v1/rag/ingest — full pipeline | ✅ PASS | `reports/evidence/CHANGE-0022/13-rag/RAG-EVIDENCE.md` |
| RAG-002 | POST /v1/rag/query — full pipeline | ✅ PASS | Same |
| RAG-003 | POST /v1/rag/hybrid-query — full pipeline | ✅ PASS | Same |
| RAG-004 | POST /v1/rag/wiki-ingest — full pipeline | ✅ PASS | Same |
| RAG-005 | GET /v1/rag/status — full pipeline | ✅ PASS | Same |
| RAG-006 | Cross-org isolation | ✅ PASS | Same |
| RAG-007 | Security ingress on document content | ✅ PASS | Same |
| RAG-008 | Security egress on retrieved context | ✅ PASS | Same |
| RAG-009 | Tier restriction (free → 403) | ✅ PASS | Same |
| RAG-010 | Missing RAG scope → 403 | ✅ PASS | Same |

## Run Commands

```bash
# Rate limiting unit tests
cd gateway && pytest tests/test_rate_limit.py -v

# SIEM integration
kubectl port-forward -n aither-inference svc/aither-siem 8080:8080 &
curl http://localhost:8080/events/summary

# Vault verification
kubectl get statefulset,svc,pvc,networkpolicy -n vault

# RAG endpoints
curl -X POST http://gateway:8080/v1/rag/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"test","top_k":3}'
```
