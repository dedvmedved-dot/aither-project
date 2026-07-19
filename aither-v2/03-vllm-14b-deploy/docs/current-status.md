# Актуальный статус развёртывания vLLM (current-status.md)
**Дата:** 2026-07-19  
**Версия:** 12.0

---

## Текущее состояние

| Pod | Status | Ready | Restarts | Node |
|---|---|---|---|---|
| `vllm-14b-instruct` | ✅ Running | 1/1 | 0 | **n7** |
| `vllm-32b-gptq` | ✅ Running | 1/1 | 0 | **n7** |
| `nginx-gateway-32b` | ✅ Running | 1/1 | 0 | n8 |
| `benchmark-inference` | ✅ Running | — | — | n8 |

---

## Выполнено (Iteration 16)

| № | Действие | Статус |
|---|---|---|
| 1 | **Benchmark Job deployed** | ✅ Runs inside cluster on n8 — no VPN needed |
| 2 | **nginx gateway production-grade** | ✅ ConfigMap + Deployment + Service via DNS |
| 3 | **SHA256 all files verified** | ✅ Both models ЦЕЛ (OK) |
| 4 | **14B Chat working** | ✅ "The capital of France is Paris." TTFT=8.18s |
| 5 | **Gateway blocks 32B Chat** | ✅ HTTP 422 on `/v1/chat/completions` |

---

## Отчёты

| Файл | Ссылка |
|---|---|
| `docs/iteration-16-summary.md` | **NEW** |
| `docs/current-status.md` | **v12.0** |
| `manifests/nginx-gateway-32b.yaml` | **NEW** |
| `manifests/benchmark-job.yaml` | **NEW** |

---

## Remaining for Production

| Item | Status |
|---|---|
| Full 60min load test | 🔄 In progress (benchmark job) |
| VPN stability | 🟡 DIAGNOSED (MTU 1362) |
| HA | 🔴 |
| Monitoring | 🟡 Basic (DCGM) |
| Provenance | 🔴 |
| **Production readiness** | **~60%** |
