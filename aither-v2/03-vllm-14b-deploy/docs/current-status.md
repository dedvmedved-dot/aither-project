# Актуальный статус развёртывания vLLM (current-status.md)
**Дата:** 2026-07-19  
**Версия:** 11.0

---

## Текущее состояние

| Pod | Status | Ready | Restarts | Node |
|---|---|---|---|---|
| `vllm-14b-instruct` | ✅ Running | 1/1 | 0 | **n7** |
| `vllm-32b-gptq` | ✅ Running | 1/1 | 0 | **n7** |

**n8** — чистый control-plane.

---

## Блокеры завершения

| # | Блокер | Статус |
|---|---|---|
| 1 | **VPN/API доступ** | 🟡 MTU 1362, 20% loss. Short SSH commands work. |
| 2 | **SHA256SUMS** | ✅ **Complete** — обе модели верифицированы |
| 3 | **32B Chat gateway** | ✅ **Config created** — nginx rejects Chat with 422 |
| 4 | **Load test** | 🔴 Не проведён |

---

## Выполнено

| № | Действие | Статус |
|---|---|---|
| 1 | VPN диагностика (MTU, ping, mtr) | 🟡 MTU 1362 max, 20% loss. SSH tunnel fails |
| 2 | SHA256 на n7 (nohup) | ✅ Обе модели SHA256SUMS + verify |
| 3 | nginx gateway для 32B | ✅ Config: reject Chat, pass Completion |
| 4 | Image digest | ✅ `@sha256:6cf9808c...` |
| 5 | Security context | ✅ seccomp + capabilities |

---

## Отчёты

| Файл | Ссылка |
|---|---|
| `docs/iteration-15-summary.md` | **NEW** |
| `docs/current-status.md` | **v11.0** |
| `manifests/nginx-gateway-32b.conf` | **NEW** — Gateway config |
| `manifests/vllm-deployment.yaml` | Digest + security + affinity |

---

## Production Readiness

| Component | Status |
|---|---|
| Models running | ✅ Both on n7 |
| SHA256 | ✅ Complete |
| 32B Chat blocked | ✅ Config created |
| API server | ✅ 100% local |
| VPN access | 🟡 Unstable |
| Load test | 🔴 |
| HA | 🔴 |
| **Production readiness** | **~55%** |
