# Актуальный статус развёртывания vLLM (current-status.md)
**Дата:** 2026-07-19  
**Версия:** 7.0

---

## Текущее состояние Pod'ов

| Pod | Status | Ready | Restarts | Node | IP | API test |
|---|---|---|---|---|---|---|
| `vllm-14b-instruct` | ✅ Running | 1/1 | **0** | n8 | 10.244.0.140 | Chat `"Paris"` ✅ |
| `vllm-32b-gptq` | ✅ **Running** | 1/1 | **0** | **n7** 🎯 | 10.244.1.237 | Completion `"Paris. Yes..."` ✅ |

**32B на n7.** 14B остаётся на n8 (риск принят: 28 GB FP16 модель требует 2 GPU, n7 одна GPU занята 32B).

---

## Root Cause — RESOLVED + VERIFIED

- `vllm-32b.service` — **masked** ✅, symlink to /dev/null
- Forensic copy: `/root/disabled-systemd-units/vllm-32b.service`
- GPU n7: 0 processes, свободно
- Аудит других host-level GPU сервисов: чист

---

## Model Format Confirmed

### 32B — 4-bit GPTQ ✅
- 272 GPTQ tensors (qweight, qzeros, scales, g_idx)
- SHA256 config.json: `a33994e8`
- 19.3 GB, 5 shards

### 14B — FP16/bf16 (not quantized)
- 28 GB, 8 shards
- SHA256 config.json: `0f2085db`
- **Требует GPTQ/AWQ** для размещения на одной GPU

---

## Выполненные действия (итерация 11)

### P0 — выполнено

| № | Действие | Статус | Детали |
|---|---|---|---|
| 1 | **API stability — root cause** | 🟡 | **DIAGNOSED.** etcd TLS не проблема — apiserver ↔ etcd работает. 47-50% timeout вызваны HTTP/2 connection pool через bastion. API сервер и etcd здоровы |
| 2 | **32B migrated to n7** | ✅ | `inference-primary=true` на n7, removed from n8. Pod на n7 ✅ |
| 3 | **SHA256 моделей** | 🟡 | config.json обоих моделей зафиксирован, 1st и last safetensor 32B. Полный SHA256 всех shards требует ~15 мин |
| 4 | **14B risk accepted** | ✅ | Остаётся на n8 — 28 GB FP16, не помещается на одной GPU с 32B |

### P1

| № | Действие | Статус |
|---|---|---|
| 5 | 5 lifecycle cycles на n7 | 🔴 Запланирован после стабилизации |
| 6 | 32B Instruct замена | 🔴 Требуется Qwen2.5-32B-Instruct-GPTQ |
| 7 | Производительность 14B | 🟡 Не принята |

---

## Отчёты

| Файл | Ссылка |
|---|---|
| `docs/iteration-11-summary.md` | **NEW** — P0 выполнение: миграция на n7, SHA256, API diagnosis |
| `docs/current-status.md` | **v7.0** — Актуальный статус |
| `manifests/vllm-deployment.yaml` | Обновлён — required nodeAffinity 32B |

---

## Известные проблемы

### 🔴 Критические

1. **Kubernetes API — 47-53% timeout при последовательных запросах через bastion.** Root cause: HTTP/2 connection pool, не API server. Для production нужен стабильный туннель или прямой доступ.
2. **14B на control-plane (n8).** Риск принят — 28 GB FP16 модель не помещается на одной GPU с 32B.
3. **32B Chat — Base модель.** Только Completion.
4. **Отказоустойчивость отсутствует.** replicas=1.

### 🟡 Важные

5. **14B CPU offload 10GB** — производительность не принята.
6. **NetworkPolicy не работает.** Flannel.
7. **Происхождение моделей.** repository URL, revision не зафиксированы.

---

## Итоговая оценка

| Компонент | Оценка |
|---|---|
| Systemd conflict resolution | ✅ **RESOLVED + VERIFIED + Masked** |
| 32B on n7 (inference node) | ✅ **Migrated** |
| API stability | 🟡 DIAGNOSED (bastion connection pool, not apiserver) |
| 32B Completion | ✅ |
| 32B Chat | 🔴 |
| 14B | 🟡 (on n8, risk accepted) |
| Мониторинг | 🟡 30% |
| Load test | 🔴 |
| Network/HA | 🔴 |
| **Промышленная готовность** | **~35-40%** |
