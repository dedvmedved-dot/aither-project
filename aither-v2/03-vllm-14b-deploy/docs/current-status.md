# Актуальный статус развёртывания vLLM (current-status.md)
**Дата:** 2026-07-19  
**Версия:** 14.0

---

## Текущее состояние

| Pod | Status | Ready | Restarts | Node |
|---|---|---|---|---|
| `vllm-14b-instruct` | ✅ Running | 1/1 | 0 | **n7** |
| `vllm-32b-gptq` | ✅ Running | 1/1 | 0 | **n7** |
| `nginx-gateway-32b` | ✅ Running (×2) | 2/2 | 0 | n8 |
| `benchmark-endurance-60min` | 🔄 Running | — | 0 | n8 |

---

## Auth & Gateway — PROVEN + HARDENED

| Feature | Status |
|---|---|
| No token → 401 | ✅ |
| Wrong token → 401 | ✅ |
| Valid token → 200 | ✅ |
| Chat blocked → 422 | ✅ |
| replicas: 2 | ✅ |
| runAsNonRoot + drop ALL caps | ✅ |
| Image digest | ✅ |
| Rate limiting | ✅ 30 req/min |

---

## Benchmark Progress

| Metric | 14B Chat | 32B Completion |
|---|---|---|
| Health | 4ms | ✅ |
| TTFB (cold) | ~7.8s | (in endurance) |
| Concurrency | All 200 | (in endurance) |
| Chat response | "Paris" ✅ | N/A (completion-only) |
| **60-min endurance** | 🔄 **RUNNING** | 🔄 **RUNNING** |

---

## Production Readiness

| Component | Status |
|---|---|
| Models running | ✅ |
| SHA256 | ✅ |
| Gateway auth | ✅ PROVEN |
| Gateway hardened | ✅ production-grade |
| 60-min endurance | 🔄 In progress |
| VPN | 🟡 DIAGNOSED (MTU 1362) |
| HA | 🔴 (single GPU node) |
| Monitoring | 🟡 Basic (DCGM) |
| Provenance | 🔴 |
| **Production readiness** | **~70%** |
