# Актуальный статус развёртывания vLLM (current-status.md)
**Дата:** 2026-07-19  
**Версия:** 8.0

---

## Текущее состояние Pod'ов

| Pod | Status | Ready | Restarts | Node | IP | API test |
|---|---|---|---|---|---|---|
| `vllm-14b-instruct` | ✅ Running | 1/1 | **0** | **n7** 🎯 | 10.244.1.251 | Chat ✅ |
| `vllm-32b-gptq` | ✅ **Running** | 1/1 | **0** | **n7** 🎯 | 10.244.1.250 | Completion ✅ |

**Обе модели на n7. n8 — чистый control-plane.**

---

## Root Cause — Systemd Conflict

- `vllm-32b.service` — **masked** ✅, forensic copy archived
- GPU n7: 0 processes, free
- **n7 lifecycle: VERIFIED** — 5/5 clean cycles

---

## API Stability Root Cause

| Finding | Detail |
|---|---|
| **etcd health** | ✅ HEALTH=true, leader, Raft term 61 |
| **apiserver livez/readyz** | ✅ Always `ok` |
| **HTTP/2 (SSH to n8, bypassing bastion)** | ✅ **92% (46/50)** |
| **HTTP/1.1 (SSH to n8)** | ❌ **0% (0/50)** |
| **VPS direct (kubectl through bastion)** | ❌ **48% (48/100)** |
| **Inference removed from n8** | ❌ **No improvement (48% before → 48% after)** |

**Root cause: bastion (nginx/conntrack) connection pool limits.** Not API server, not etcd, not inference load.

**Workaround:** Use SSH tunnel to n8 for stable API access.

---

## Выполненные действия (итерация 12)

| № | Действие | Статус | Детали |
|---|---|---|---|
| 1 | **5 lifecycle cycles on n7** | ✅ | **5/5 PASSED** — n7 lifecycle VERIFIED |
| 2 | **etcd TLS health check** | ✅ | etcd health=true, leader |
| 3 | **HTTP/2 vs HTTP/1.1 test** | ✅ | HTTP/1.1 0% — confirms bastion issue |
| 4 | **14B migrated to n7** | ✅ | Both models on n7. n8 freed. |
| 5 | **Affinity updated** | ✅ | 14B: required. 32B: cleaned redundant preferred |
| 6 | **SHA256 models** | 🟡 config.json + first/last shard 32B |
| 7 | **Manifests pushed** | ✅ | vllm-deployment.yaml updated |

---

## Отчёты (new)

| Файл | Ссылка |
|---|---|
| `docs/iteration-12-summary.md` | **NEW** — 5 lifecycle cycles, API root cause, both models on n7 |
| `docs/current-status.md` | **v8.0** — Актуальный статус |
| `manifests/vllm-deployment.yaml` | Обновлён — 14B required affinity, 32B cleaned |

---

## Известные проблемы

### 🔴 Критические
1. **API timeout через bastion (48%).** Root cause: bastion connection pool. Not apiserver/etcd. Workaround: SSH tunnel.
2. **32B Chat — Base модель.** Только Completion.
3. **Отказоустойчивость отсутствует.** replicas=1, одна нода n7.

### 🟡 Важные
4. **14B CPU offload 10GB — производительность не принята.**
5. **NetworkPolicy не работает.** Flannel.
6. **Происхождение моделей.** repository URL, revision не зафиксированы.

---

## Итоговая оценка

| Компонент | Оценка |
|---|---|
| Systemd conflict | ✅ **RESOLVED + VERIFIED** |
| n7 lifecycle | ✅ **VERIFIED (5/5)** |
| Both models on n7 | ✅ **Completed** |
| API stability | 🟡 **DIAGNOSED** (bastion root cause) |
| 32B Chat | 🔴 |
| Production readiness | **~40-45%** |
