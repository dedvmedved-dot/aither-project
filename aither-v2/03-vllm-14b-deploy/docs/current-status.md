# Актуальный статус развёртывания vLLM (current-status.md)
**Дата:** 2026-07-19  
**Версия:** 13.0

---

## Текущее состояние

| Pod | Status | Ready | Restarts | Node |
|---|---|---|---|---|
| `vllm-14b-instruct` | ✅ Running | 1/1 | 0 | **n7** |
| `vllm-32b-gptq` | ✅ Running | 1/1 | 0 | **n7** |
| `nginx-gateway-32b` | ✅ Running | 1/1 | 0 | n8 |
| `benchmark-inference` | ✅ Running | — | — | n8 |

---

## Auth Tests — PROVEN

| Test | Result |
|---|---|
| No token | **401** |
| Wrong token | **401** |
| Valid token → completion | **200** |
| Chat blocked (422) | **422** |

---

## Gateway Tests

| Path | Status |
|---|---|
| `/v1/chat/completions` → 422 | ✅ |
| `/v1/completions` via gateway → 200 | ✅ |
| `/health` via gateway | ✅ |
| Service DNS (no Pod IP) | ✅ |

---

## SHA256

Both models verified on n7. All files OK.

---

## 14B Metrics

| Metric | Value |
|---|---|
| Health | 4ms |
| TTFB (cold) | ~7.8s |
| Concurrent 1-4 | All 200 |
| Chat response | "The capital of France is Paris." |

---

## Production Readiness

| Component | Status |
|---|---|
| Models running | ✅ |
| SHA256 | ✅ |
| Gateway auth | ✅ **PROVEN** |
| 32B Chat blocked | ✅ |
| Load test (60min) | 🔄 In progress |
| VPN | 🟡 DIAGNOSED (MTU 1362) |
| HA | 🔴 |
| Monitoring | 🟡 Basic (DCGM) |
| Provenance | 🔴 |
| **Production readiness** | **~65%** |
