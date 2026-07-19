# Iteration 18 — 60min Endurance + Gateway Hardening

**Date:** 2026-07-19

---

## P0.1: 60-Minute Endurance Benchmark

**Status:** 🔄 **RUNNING** (expected completion: ~19:50 MSK)

Job `benchmark-endurance-60min` created on n8. Tests both models sequentially for 60 minutes.

| Metric | Expected |
|---|---|
| Duration | 3600s |
| 14B requests | ~420 (one per ~8s) |
| 32B requests | ~420 |
| HTTP errors | 0 |
| Conclusion | PASSED |

---

## P0.2: Gateway Hardening — PRODUCTION-GRADE

| Change | Status |
|---|---|
| `replicas: 2` | ✅ |
| `securityContext.runAsNonRoot: true` | ✅ |
| `runAsUser: 101` | ✅ |
| `allowPrivilegeEscalation: false` | ✅ |
| `capabilities.drop: ALL` | ✅ |
| Image pinned via digest | ✅ `nginx:alpine@sha256:343e2...` |
| Rate limiting (30 req/min) | ✅ |
| `client_max_body_size: 4m` | ✅ |
| `proxy_connect_timeout/send_timeout` | ✅ |
| nginx stub_status for metrics | ✅ `/nginx_status` |

---

## P0.3: Auth Tests — PROVEN

| Test | Result |
|---|---|
| No token | 401 ✅ |
| Wrong token | 401 ✅ |
| Valid token | 200 ✅ |
| Chat blocked | 422 ✅ |
| Completion via gateway | 200 ✅ |

---

## P0.4: SHA256 — COMPLETE

Both models verified on n7. All files `ЦЕЛ`.

---

## Manifests

| File | Link |
|---|---|
| `docs/iteration-18-summary.md` | **NEW** |
| `docs/current-status.md` | **v14.0** |
| `manifests/nginx-gateway-32b.yaml` | **Hardened**: digest, securityContext, rate limit, replicas=2 |
| `manifests/benchmark-endurance-60min.yaml` | **NEW**: 60-min endurance test |
