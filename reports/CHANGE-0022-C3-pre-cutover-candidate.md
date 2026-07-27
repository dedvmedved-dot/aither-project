# CHANGE-0022-C3 Pre-Cutover Candidate Report

**Date:** 2026-07-27
**Commit:** 801ca390a15975ad360238414d2a059e2092daf2
**Branch:** aither-v2
**Repository:** aither-project-r7-canonical

## Executive Summary

CHANGE-0022-C3 implements critical security hardening across 4 components: Rate Limiting (fail-closed), Production SIEM, Persistent Vault, and Full RAG Security Pipeline. All changes are append-only, no rebase/amend/reset/force-push.

## Change Inventory

### A. Rate Limiting (Section 10) — CRITICAL
**Files:** `gateway/rate_limit.py`, `gateway/gateway.py`

| Change | Before | After |
|---|---|---|
| Fail-closed design | Fallback safe limits on unknown tier | Unknown tier → deny |
| PG unavailable | `limits = {"rpm": 300, ...}` fallback | `(False, "rate_limit_unavailable_pg")` |
| Redis unavailable | Fail-open: `pass` / `limits = {"rpm": 60, ...}` | Fail-closed: `(False, "rate_limit_unavailable")` |
| Cache TTL | No TTL invalidation (`_tier_cache` dict only) | `_is_cache_valid()` with timestamp, `invalidate_tier_cache()` |
| Quota dimensions | org-level only | org + API-key + model dimensions |
| Gateway fail-open | `except: pass` on Redis error (line 691) | `_json(503, "rate_limit_unavailable")` |

### B. Production SIEM (Section 11) — IMPORTANT
**Files:** `gateway/siem_receiver.py`, `aither-v2/deploy/siem/deployment.yaml`

| Change | Before | After |
|---|---|---|
| Image | `python:3.11-slim` with `pip install` at startup | Pinned image `aither-siem:v3-prod`, no pip at startup |
| Storage | In-memory ring buffer only | SQLite + PVC + gzip backups |
| Auth on query | None | Bearer token / API key via `SIEM_ADMIN_KEY` |
| NetworkPolicy | None | Ingress restricted to Gateway pods |
| Retention | None | 90-day configurable, hourly cleanup |
| Event types | 12 types | All 16 required types |
| Backups | None | Hourly gzip JSON backups, keep last 30 |
| Probes | Basic | startupProbe + readinessProbe + livenessProbe |

### C. Vault (Section 12) — IMPORTANT
**Files:** `aither-v2/deploy/vault/deployment.yaml`

| Change | Before | After |
|---|---|---|
| TLS | Disabled (`tls_disable = "true"`) | Enabled (`tls_cert_file`, `tls_key_file`) |
| Image | `hashicorp/vault:1.18` | `hashicorp/vault:1.18.3` (pinned) |
| Security context | None | `runAsNonRoot: true, runAsUser: 100` |
| NetworkPolicy | None | Ingress restricted to aither-inference Gateway |
| Audit | Not configured | PVC + audit device enable procedure |
| Policies | 2 policies | 3 policies (gateway, BFF, admin) — least privilege |
| SA token | automount | Projected service-account token only |
| Init procedure | Comments only | Full procedure in ConfigMap `vault-init-procedure.md` |

### D. RAG (Section 13) — IMPORTANT
**Files:** `gateway/app.py`, `gateway/config.py`

| Change | Before | After |
|---|---|---|
| Auth on endpoints | None | Full `check_auth()` on all 5 endpoints |
| Scope check | None | `_has_rag_scope()` — RAG scope required |
| Tier check | Tier only on query | `_check_tier_rag()` on all endpoints |
| Org isolation | Shared `documents` collection | Per-org `documents_{org_id}` collections |
| Security ingress | None | `check_security()` on documents and queries |
| Security egress | None | `check_egress()` on retrieved context |
| SIEM | None | Events for auth, violations, errors |
| Endpoints | 3 (status, query, wiki-ingest) | 5 (status, query, hybrid-query, ingest, wiki-ingest) |

## Deployment Order

1. **Deploy Vault first** (no dependencies): `kubectl apply -f aither-v2/deploy/vault/deployment.yaml`
2. **Deploy SIEM** (independent): `kubectl apply -f aither-v2/deploy/siem/deployment.yaml`
3. **Deploy Gateway** (depends on Vault+SIEM for features): update ConfigMap + rollout restart
4. Enable features: Set `VAULT_ENABLED=true`, `VAULT_REQUIRED=true`, `SIEM_ENABLED=true`, `RAG_ENABLED=true`

## Rollback Plan

- Rate limiting: Revert `gateway/rate_limit.py` and `gateway/gateway.py` to previous commit
- SIEM: `kubectl delete -f aither-v2/deploy/siem/deployment.yaml` — independent service
- Vault: `kubectl delete -f aither-v2/deploy/vault/deployment.yaml` — independent namespace
- RAG: Disable via `RAG_ENABLED=false` in Gateway env — feature flag

## Pre-Cutover Checklist

- [x] All code changes committed (append-only)
- [x] No rebase/amend/reset/force-push
- [x] No hardcoded credentials in Git
- [x] NetworkPolicy manifests ready
- [x] PVC manifests ready
- [x] Probes configured
- [x] Resource limits set
- [x] Evidence documented in `reports/evidence/CHANGE-0022/`
- [ ] Vault TLS cert generated (manual — `openssl req -x509 ...`)
- [ ] Vault init + unseal performed (manual)
- [ ] Recovery keys stored in 1Password (manual — NOT in Git)
- [ ] SIEM admin key set in Secret (manual)
- [ ] Gateway env vars configured: VAULT_ENABLED, SIEM_ENABLED, RAG_ENABLED
- [ ] Test all RAG endpoints with real auth
- [ ] Verify cross-org RAG isolation

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Rate limit fail-closed blocks legitimate traffic | Medium | High | Monitor 503 rate. Rollback gateway.py if needed. |
| Vault sealed on restart | High | Medium | Auto-unseal with 3 keys. Documented procedure. |
| SIEM PVC fills up | Low | Low | 20Gi PVC, 90-day retention, hourly cleanup. |
| RAG org isolation breaks existing queries | Medium | Medium | Feature flag `RAG_ENABLED`. Test per-org collections before enabling. |

## Sign-off

- [ ] Architecture Review
- [ ] Security Review
- [ ] Operations Review
- [ ] Deployment Approval
