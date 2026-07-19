# Iteration 17 — Final Blockers Closed

**Date:** 2026-07-19

---

## P0.1: Benchmark Job Fixed

| Fix | Status |
|---|---|
| `nodeSelector: aither.io/benchmark-node=true` | ✅ |
| Toleration for control-plane taint | ✅ |
| Image pinned `curlimages/curl:8.10.1` | ✅ |
| `bc` removed (direct `$(()))` arithmetic) | ✅ |
| TTFB vs TTFT separated in report | ✅ |
| Auth tests (no token, wrong token, valid) | ✅ |
| Gateway path tests (chat 422, completion 200) | ✅ |

---

## P0.2: Auth Tests Results

| Test | Result | Expected |
|---|---|---|
| No token | **401** ✅ | 401/403 |
| Wrong token | **401** ✅ | 401/403 |
| Valid token (POST) | **200** ✅ | 200 |
| 32B chat via gateway | **422** ✅ | 422 |
| 32B completion via gateway | **200** ✅ | 200 |

**Gateway auth: PROVEN.**

---

## P0.3: 14B Benchmark

| Metric | Value |
|---|---|
| Health check | 4ms ✅ |
| Single Chat TTFB | 7.78s |
| Concurrency 1 | 7.77s |
| Concurrency 2 | 7.78s / 15.53s |
| Concurrency 4 | in progress |
| Response | "The capital of France is Paris." ✅ |

---

## P0.4: SHA256

| Model | Files | Status |
|---|---|---|
| Qwen2.5-32B-GPTQ | 9 | ✅ All ЦЕЛ |
| Qwen2.5-14B-Instruct | 42 (incl cache) | ✅ All ЦЕЛ |

---

## Manifests

| File | Link |
|---|---|
| `docs/iteration-17-summary.md` | **NEW** |
| `docs/current-status.md` | **v13.0** |
| `manifests/nginx-gateway-32b.yaml` | Updated — auth via vLLM |
| `manifests/benchmark-job.yaml` | Fixed — nodeSelector, image, auth tests |
