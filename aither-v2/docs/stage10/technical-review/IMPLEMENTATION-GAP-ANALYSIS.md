# IMPLEMENTATION-GAP-ANALYSIS.md

**Project:** Aither / AI Hermes MVP  
**Stage:** Stage 10 — RC1 Gate  
**Document:** Implementation Gap Analysis  
**Date:** 2026-07-20

---

## 1. Purpose

Identify gaps between the current implementation and the requirements implied by the Stage 10 document set (00-10).

## 2. Scope

Comparison of documented Stage 10 requirements against actual repository state.

## 3. Gaps

### Gap 1: DNS-N7-01 — MissingClusterDNS on node n7

| Aspect | Detail |
|---|---|
| Status | **PARTIAL — NOT RESOLVED** |
| Documented in | `03-STAGE10-RC1-STANDARD.md` (RC1 criteria), `FINDINGS.md` |
| Current state | `nginx-gateway-32b-hardened.yaml:21` uses hostname `vllm-32b-gptq.aither-inference.svc` — which fails on n7 |
| Runtime workaround | ClusterIP `10.99.3.103` was patched at runtime but NOT committed |
| Gap | The manifest in the repository WILL break on next redeployment |
| Resolution required | Before final PASSED |

### Gap 2: GW-RUNTIME-CM-01 — ConfigMap drift

| Aspect | Detail |
|---|---|
| Status | **PARTIAL — NOT RESOLVED** |
| Documented in | `FINDINGS.md`, `AUDIT_LOG.md` |
| Current state | GitHub manifest uses hostname; runtime uses ClusterIP |
| Gap | Source of truth (Git) ≠ running state (K8s) |
| Resolution required | Align manifest OR fix ClusterDNS |

### Gap 3: PROD-READY-01 — Production readiness

| Aspect | Detail |
|---|---|
| Status | **OPEN** |
| Documented in | `PROJECT_MASTER.md`, `current-mvp-status.md` |
| Current state | No HTTPS, no HA for BFF, no monitoring, no automated rollback |
| Gap | All identified as OPEN — accepted for MVP |
| Resolution required | Documented as technical debt, not RC1 blocker |

### Gap 4: AUTH-REDIS-FAIL-01 — Auth unavailable when Redis is down

| Aspect | Detail |
|---|---|
| Status | **PARTIAL** |
| Current state | BFF auth fails with 503 when Redis unavailable (`app.py:400,465,504`) |
| Gap | Admin login, token management, session validation all fail |
| Resolution required | Accept for MVP (fail-open for RL but fail-closed for auth is by design) |

### Gap 5: AUTH-TOKEN-PERSIST-01 — Token durability

| Aspect | Detail |
|---|---|
| Status | **PARTIAL** |
| Current state | Token metadata stored only in Redis (no persistent backup) |
| Gap | All tokens lost on Redis restart |
| Resolution required | Accept for MVP — document in DR plan |

### Gap 6: GW-IMG-01 — Image digest not pinned

| Aspect | Detail |
|---|---|
| Status | **RISK ACCEPTED / PARTIAL** |
| Current state | `nginx:alpine` version tag used |
| Gap | Non-reproducible deployments, potential supply chain risk |
| Resolution required | Post-MVP hardening |

### Gap 7: GW-SC-01 — Gateway securityContext partial

| Aspect | Detail |
|---|---|
| Status | **PARTIAL** |
| Current state | nginx containers require elevated capabilities |
| Gap | `runAsNonRoot: false`, `CHOWN`/`SETGID`/`SETUID` added |
| Resolution required | Post-MVP with distroless nginx image |

### Gap 8: BFF-RL-REDIS-FAIL-01 — RL fail-open tested? No

| Aspect | Detail |
|---|---|
| Status | **PARTIAL** |
| Current state | Code implements fail-open logic, but no evidence of it being tested |
| Gap | Fail-open behavior untested |
| Resolution required | Test evidence needed for RC1 closeout |

### Gap 9: BFF-RL-RESET-TTL-01 — TTL not observed

| Aspect | Detail |
|---|---|
| Status | **MINOR FINDING** |
| Current state | TTL reset confirmed only by manual Redis key flush |
| Gap | No automated verification |
| Resolution required | Post-MVP observability improvement |

## 4. Summary

| Category | Count | Critical | Major | Minor |
|---|---|---|---|---|
| Gaps affecting RC1 | 2 | DNS-N7-01, GW-RUNTIME-CM-01 | — | — |
| Gaps accepted for MVP | 7 | — | PROD-READY-01, GW-IMG-01, GW-SC-01 | AUTH-REDIS-FAIL-01, AUTH-TOKEN-PERSIST-01, BFF-RL-REDIS-FAIL-01, BFF-RL-RESET-TTL-01 |

## 5. Conclusion

Two gaps (**DNS-N7-01** and **GW-RUNTIME-CM-01**) directly affect reproducibility and must be resolved before final RC1 PASSED. All other gaps are documented as open findings and can be accepted for MVP.
