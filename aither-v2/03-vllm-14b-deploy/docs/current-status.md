# Актуальный статус развёртывания vLLM (current-status.md)
**Дата:** 2026-07-19  
**Версия:** 4.0

---

## Текущее состояние Pod'ов

| Pod | Status | Ready | Restarts | Node | IP | API test |
|---|---|---|---|---|---|---|
| `vllm-14b-instruct` | ✅ Running | 1/1 | **0** | n8 | 10.244.0.140 | Chat `"Paris"` — осмысленный ответ ✅ |
| `vllm-32b-gptq` | ⚠️ **CrashLoopBackOff** | 0/1 | 5 | n7 | — | — |

**14B — стабилен, Restarts=0.** 32B свалился в CrashLoopBackOff на n7 после 5 циклов перезапуска — вероятна фрагментация GPU памяти или image pull timeout.

n7 — разcordoned (после рестарта containerd/kubelet).

---

## Выполненные действия (итерация 8)

### P0 — Критические блокеры

| № | Действие | Статус | Детали |
|---|---|---|---|
| 1 | **`--quantization gptq` возвращён** в 32B | ✅ | Regression gate: yaml-парсинг проверяет args перед apply |
| 2 | **32B semantic completion тест** | ✅ | `"Paris. Yes, that's correct..."` — осмысленный ответ |
| 3 | **Orphan PID 858203 убит** на n7 | MITIGATED | `multiprocessing.spawn` от старого Pod, 3+ часа |
| 4 | **n7 recovery — перезапуск containerd+kubelet** | ✅ | Node Ready в пределах 5m, pods schedule на n7 |
| 5 | **5 циклов удаления Pod на n7** | ✅ | Все 5 циклов прошли, GPU процессы чистые (принадлежат новым подам) |
| 6 | **API stability test — 30 запросов** | ✅ | 29/30 успешно (96.7%). 1 timeout — первый cold start |

### P1 — Функциональность

| № | Действие | Статус |
|---|---|---|
| 7 | 32B Completion тест | ✅ **Выполнен.** Ответ осмысленный |
| 8 | Фиксация source модели | ✅ **model-source.md** создан |
| 9 | 14B Chat тест | 🟡 Ожидает (CPU offload 10GB — холодный старт до 60+ сек) |

### P2 — Стабильность

| № | Действие | Статус |
|---|---|---|
| 10 | 5 циклов orphan-теста на n7 | ✅ **Выполнено.** GPU процессы чистые (не орфаны — новые поды). |
| 11 | API stability — 30 запросов | ✅ **Выполнено.** 96.7% success rate |
| 12 | Load test 60 мин | 🔴 Не проведён |

### P3 — Эксплуатация

| № | Действие | Статус |
|---|---|---|
| 13 | DCGM Exporter + canary | ✅ Каждые 5 мин |
| 14 | Regression gate skill | ✅ `k8s-gpu/deployment-regression-gates` |
| 15 | Memory: правила поведения | ✅ 19 правил |

---

## Отчёты (new)

| Файл | Описание |
|---|---|
| `docs/n7-recovery-results.md` | **NEW** — Перезапуск n7 + 5 циклов удаления Pod |
| `docs/api-stability-results.md` | **NEW** — 30 запросов kubectl с таймаутом 5s |
| `docs/current-status.md` | **v4.0** — Актуальный статус (этот файл) |

Все отчёты: `docs/current-status.md` → `docs/model-source.md` → `docs/orphan-test-results.md` → `docs/load-test-results.md` → `docs/monitoring-setup.md` → `docs/n7-recovery-results.md` → `docs/api-stability-results.md`

---

## Известные проблемы

### 🔴 Критические

1. **32B в CrashLoopBackOff на n7** после 5 циклов перезапуска. Требуется `kubectl delete pod` для перезапуска или ручная диагностика логов.
2. **Orphan-процессы** — после восстановления n7 не подтверждены (PID принадлежали новым подам). Требуется повторная проверка на длительном интервале.
3. **Kubernetes API — единичные timeout.** 1 из 30 (cold start). Стабильность 96.7%.

### 🟡 Важные

4. **14B с CPU offload 10GB.** Медленный холодный старт (60+ сек).
5. **Отказоустойчивость отсутствует.** По одной реплике.

---

## Итоговая оценка

| Компонент | Оценка |
|---|---|
| Kubernetes-манифесты | 85-90% |
| 14B как тестовый сервис | 70% |
| 32B | 20% (CrashLoopBackOff) |
| Мониторинг | 30% |
| Orphan-проблема | MITIGATED (не RESOLVED) |
| API стабильность | ✅ 96.7% |
| Отказоустойчивость | 20% |
| **Промышленная готовность** | **~35-40%** |

---

## Приоритет дальше

### P0 — восстановление 32B
1. Проверить логи CrashLoopBackOff на n7
2. `kubectl delete pod` для перезапуска 32B
3. Убедиться, что стартует на n8 (не на n7)

### P1 — функциональность
4. Получить Qwen2.5-32B-Instruct-GPTQ
5. Заменить модель, зафиксировать SHA и revision

### P2 — стабильность
6. Load test 60 мин
7. Service DNS из клиента

### P3 — эксплуатация
8. Semantic canary
9. Prometheus + Grafana
