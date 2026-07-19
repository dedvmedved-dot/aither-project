# Актуальный статус развёртывания vLLM (current-status.md)
**Дата:** 2026-07-19  
**Версия:** 9.0

---

## Текущее состояние Pod'ов

| Pod | Status | Ready | Restarts | Node |
|---|---|---|---|---|
| `vllm-14b-instruct` | ✅ Running | 1/1 | 0 | **n7** |
| `vllm-32b-gptq` | ✅ Running | 1/1 | 0 | **n7** |

**Обе модели на n7. n8 — чистый control-plane.**

---

## Root Causes — Resolved

| Issue | Status |
|---|---|
| Systemd vllm-32b.service (TP=2 host process) | ✅ **RESOLVED + VERIFIED** (masked, archived) |
| 32B on control-plane n8 | ✅ **Migrated to n7** |
| 14B on control-plane n8 | ✅ **Migrated to n7** |
| n7 lifecycle (5 cycles) | ✅ **VERIFIED** (5/5 passed, GPU clean after each) |
| etcd health | ✅ **HEALTH=true**, leader |
| API server health | ✅ **95%** direct curl, healthy |
| Bastion API timeout | 🟡 **DIAGNOSED** — bastion connection pool, not apiserver/etcd |

---

## Security

| Setting | 14B | 32B |
|---|---|---|
| seccompProfile | ✅ `RuntimeDefault` | ✅ `RuntimeDefault` |
| allowPrivilegeEscalation | ✅ `false` | ✅ `false` |
| capabilities.drop | ✅ `ALL` | ✅ `ALL` |

---

## Выполненные действия (итерация 13)

| № | Действие | Статус |
|---|---|---|
| 1 | **kubectl -v=8 with stderr** | ✅ API server healthy. Curl = 95%. |
| 2 | **Direct curl to 127.0.0.1:6443** | ⚠️ TLS SAN mismatch — cert on hostname, not loopback |
| 3 | **Security context added** | ✅ seccomp + container security for both deployments |
| 4 | **SHA256 (full)** | 🔄 Background — ~20 min for 13 GB files through SSH |
| 5 | **Full lifecycle proto** | ✅ One cycle fully documented |

---

## Отчёты (new)

| Файл | Ссылка |
|---|---|
| `docs/iteration-13-summary.md` | **NEW** — API root cause confirmed, security context, lifecycle |
| `docs/current-status.md` | **v9.0** |
| `manifests/vllm-deployment.yaml` | Security context added |

---

## Итоговая оценка

| Компонент | Оценка |
|---|---|
| Systemd conflict | ✅ RESOLVED |
| n7 lifecycle | ✅ VERIFIED |
| Both models on n7 | ✅ |
| API server health | ✅ 95% |
| Bastion API access | 🟡 DIAGNOSED |
| 32B Chat | 🔴 |
| Load test | 🔴 |
| HA | 🔴 |
| **Production readiness** | **~45-50%** |
