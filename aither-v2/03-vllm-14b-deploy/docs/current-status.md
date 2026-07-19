# Актуальный статус развёртывания vLLM (current-status.md)
**Дата:** 2026-07-19  
**Версия:** 10.0

---

## Текущее состояние Pod'ов

| Pod | Status | Ready | Restarts | Node |
|---|---|---|---|---|
| `vllm-14b-instruct` | ✅ Running | 1/1 | 0 | **n7** |
| `vllm-32b-gptq` | ✅ Running | 1/1 | 0 | **n7** |

---

## API Stability — ✅ RESOLVED

**Final root cause:** VPN instability, NOT the API server.

| Test | Result |
|---|---|
| Loopback on n8 (curl to 127.0.0.1 via SAN hostname, 50 req) | **100% (50/50)** |
| Same test via SSH through VPN | 49% (VPN drops connections) |

**The Kubernetes API server is healthy.** Remote access is limited by VPN quality.

---

## Completed This Iteration

| № | Action | Status |
|---|---|---|
| 1 | **API root cause proven** | ✅ **100% loopback** → API server healthy |
| 2 | **Image digest applied** | ✅ `@sha256:6cf9808c...` |
| 3 | **32B Completion-only** | ✅ Formalized |
| 4 | **SHA256SUMS** | 🔄 In progress |
| 5 | **Security context** | ✅ Already applied (iter 13) |

---

## Отчёты

| Файл | Ссылка |
|---|---|
| `docs/iteration-14-summary.md` | **NEW** — API root cause proven, digest applied |
| `docs/current-status.md` | **v10.0** |
| `manifests/vllm-deployment.yaml` | Image digest |

---

## Production Readiness

| Component | Status |
|---|---|
| API server | ✅ **100% stable (loopback)** |
| SSH/VPN access | 🟡 Unstable (VPN drops) |
| SHA256 | 🔄 In progress |
| 32B Chat | 🔴 Completion-only (Base model) |
| Load test | 🔴 |
| HA | 🔴 |
| **Production readiness** | **~50%** |
