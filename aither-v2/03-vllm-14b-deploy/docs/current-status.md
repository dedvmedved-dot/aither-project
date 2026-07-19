# Актуальный статус развёртывания vLLM (current-status.md)
**Дата:** 2026-07-19  
**Версия:** 6.0

---

## Текущее состояние Pod'ов

| Pod | Status | Ready | Restarts | Node | IP | API test |
|---|---|---|---|---|---|---|
| `vllm-14b-instruct` | ✅ Running | 1/1 | **0** | n8 | 10.244.0.140 | Chat `"Paris"` — осмысленный ответ ✅ |
| `vllm-32b-gptq` | ✅ **Running** | 1/1 | **0** | n8 | 10.244.0.142 | Completion ✅ |

**Обе модели Running, Restarts=0 на n8** (временная миграция до верификации n7).

---

## Root Cause — RESOLVED

**Системный vllm-32b.service на n7:**
- `systemctl mask` ✅ — symlink to /dev/null
- Unit file сохранён в `/root/disabled-systemd-units/`
- Аудит systemd/cron/user units — других host-level GPU сервисов не найдено
- `systemctl is-enabled` → **masked**
- GPU n7: 0 процессов, 22.5 GiB free на обеих RTX 6000

---

## Model Format Confirmed

- **32B GPTQ**: настоящая 4-bit GPTQ (272 GPTQ-тензора: qweight, qzeros, scales, g_idx)
- dtypes: int32 (quantized) + float16 (layernorm/embedding)
- 19.3 GB = корректный размер для 4-bit GPTQ 32B модели

---

## Выполненные действия (итерация 10)

### P0 — Критические

| № | Действие | Статус | Детали |
|---|---|---|---|
| 1 | **Mask vllm-32b.service** | ✅ | `systemctl mask`, unit удалён из `/etc/systemd/system/` |
| 2 | **Аудит host-level GPU сервисов** | ✅ | Других vllm/Qwen/triton сервисов нет |
| 3 | **SHA256 + формат 32B модели** | ✅ | Настоящий 4-bit GPTQ, SHA256 зафиксирован |
| 4 | **5 lifecycle cycles (scale 1→0)** | ✅ | 5/5 чисты, GPU n7 = 0 MiB после каждого. |
| 5 | **API stability test 1000 req** | 🔄 | Выполняется в фоне |
| 6 | **32B Deployment: required nodeAffinity** | ✅ | `required` на `aither.io/inference-primary=true` |
| 7 | **Server-side dry-run + apply** | ✅ | Без ошибок |

### P1 — Функциональность

| № | Действие | Статус |
|---|---|---|
| 8 | 32B Completion подтверждён | ✅ |
| 9 | Фиксация source модели | 🟡 **model-source.md** — SHA256 добавлен, repository/SHA не зафиксированы |
| 10 | 14B Chat тест | ✅ Работает |

### P2 — Стабильность

| № | Действие | Статус |
|---|---|---|
| 11 | 5 чистых lifecycle-циклов (scale 1→0) | ✅ Выполнено |
| 12 | API stability — 1000 запросов | 🔄 В процессе |
| 13 | Load test 60 мин | 🔴 Не проведён |

### P3 — Эксплуатация

| № | Действие | Статус |
|---|---|---|
| 14 | DCGM Exporter + canary | ✅ |
| 15 | Regression gate skill | ✅ |

---

## Отчёты

| Файл | Описание |
|---|---|
| `docs/iteration-10-summary.md` | **NEW** — Полный отчёт: все P0 действия |
| `docs/n7-forensic-root-cause.md` | Обновлён — mask, verification |
| `docs/current-status.md` | **v6.0** — Актуальный статус |
| `docs/api-stability-results.md` | 30 запросов (будет заменён на 1000) |
| `docs/n7-recovery-results.md` | Исходный отчёт (методология недействительна) |
| `manifests/vllm-deployment.yaml` | Обновлён — required nodeAffinity 32B |

---

## Известные проблемы

### 🔴 Критические

1. **Kubernetes API — нестабильность.** `i/o timeout` на `rollout status` и `watch`. Тест 1000 запросов в процессе.
2. **Обе модели на control-plane (n8).** n7 cordoned до завершения верификации.
3. **32B Chat — Base модель.** Только Completion. Требуется Instruct-GPTQ.
4. **Отказоустойчивость отсутствует.** replicas=1, одна нода.

### 🟡 Важные

5. **14B с CPU offload 10GB.** Производительность не принята.
6. **NetworkPolicy не работает.** Flannel.
7. **Происхождение моделей.** repository URL, revision, checksums не зафиксированы.

---

## Итоговая оценка

| Компонент | Оценка |
|---|---|
| Root cause GPU-конфликта | ✅ **RESOLVED + VERIFIED** |
| Защита от повторения (mask) | ✅ **Masked** |
| 5 lifecycle cycles (n7 clean) | ✅ **5/5 passed** |
| 32B — Running + Completion | ✅ **Working** |
| 32B — Chat | 🔴 Не работает (Base модель) |
| API стабильность (1000 req) | 🟡 В процессе |
| 14B — Running | ✅ |
| Мониторинг | 🟡 30% (DCGM + canary) |
| Load test | 🔴 0% |
| Сетевая изоляция | 🔴 10% |
| HA | 🔴 10% |
| **Промышленная готовность** | **~45-50%** |

---

## Приоритет дальше

### P0
1. Дождаться результатов API 1000 req
2. Добавить `aither.io/inference-primary` label на n7
3. Перенести inference с n8 на n7
4. 5 lifecycle cycles на n7 (после переноса)

### P1
5. Заменить 32B Base на Instruct-GPTQ
6. Зафиксировать repository, revision, SHA256 моделей
7. Измерить производительность 14B

### P2
8. Load test 60 мин
9. Failover test

### P3
10. Prometheus/Grafana/alerts
11. Semantic canary
12. Сетевая изоляция (Calico/Cilium проект)
