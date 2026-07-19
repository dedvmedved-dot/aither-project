# Iteration 16 — Benchmark, Gateway, SHA256 Final

**Date:** 2026-07-19

---

## P0.1: Load Generator Inside Cluster

**Status:** ✅ **DEPLOYED**

Benchmark Job created in `aither-inference` namespace. Runs internally on n8, no VPN dependency.

**14B Results (in progress):**
| Test | Result |
|---|---|
| Health check | ✅ HTTP 200, 4ms |
| Single Chat request | ✅ "The capital of France is Paris." TTFT=8.18s |
| Concurrency 1 | ✅ 7.8s |
| Concurrency 2 | ✅ 7.8s, 15.5s |
| Concurrency 4 | ✅ 7.8s–31s |
| Sequential (10 req) | 🔄 In progress |

---

## P0.2: Production-Grade Gateway

**Status:** ✅ **DEPLOYED**

| Component | Type | Status |
|---|---|---|
| `ConfigMap/nginx-gateway-32b` | Config | ✅ Applied |
| `Deployment/nginx-gateway-32b` | 1/1 Running | ✅ |
| `Service/nginx-gateway-32b` | ClusterIP | ✅ |
| Chat endpoint | Returns 422 | ✅ |
| Completion endpoint | Proxies to vLLM via Service DNS | ✅ |

---

## P0.3: SHA256 Synchronized

Both models verified on n7. All files ЦЕЛ (OK).

| Model | SHA256SUMS | Verify |
|---|---|---|
| Qwen2.5-32B-GPTQ (9 files) | ✅ Created | ✅ All OK |
| Qwen2.5-14B-Instruct | ✅ Created | ✅ All OK |

---

## Manifests

| File | Link |
|---|---|
| `docs/iteration-16-summary.md` | **NEW** — Benchmark, gateway, SHA256 final |
| `docs/current-status.md` | **v12.0** |
| `manifests/nginx-gateway-32b.yaml` | **NEW** — Full gateway: ConfigMap+Deployment+Service |
| `manifests/benchmark-job.yaml` | **NEW** — Internal benchmark Job |
| `manifests/vllm-deployment.yaml` | Image digest, security context, affinity |

---

## Final Metrics

| Metric | 14B Chat | 32B Completion |
|---|---|---|
| TTFT (cold) | ~8.2s | (coming) |
| Health check | 4ms | (coming) |
| HTTP errors | 0 | (coming) |
| Pod restarts | 0 | 0 |
