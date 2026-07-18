# Актуальный статус развёртывания vLLM (current-status.md)
**Дата:** 2026-07-19  
**Версия:** 5.0

---

## Текущее состояние Pod'ов

| Pod | Status | Ready | Restarts | Node | IP | API test |
|---|---|---|---|---|---|---|
| `vllm-14b-instruct` | ✅ Running | 1/1 | **0** | n8 | 10.244.0.140 | Chat `"Paris"` — осмысленный ответ ✅ |
| `vllm-32b-gptq` | ✅ **Running** | 1/1 | **0** | n8 | 10.244.0.141 | Completion ✅ |

**Обе модели Running, Restarts=0 на n8.** n7 — cordoned после обнаружения root cause.

---

## Root Cause — найден!

**Проблема «orphan GPU процессов» на n7 была вызвана systemd unit `/etc/systemd/system/vllm-32b.service`**, который запускал vLLM с `tensor-parallel-size=2` напрямую на хосте (вне Kubernetes).

| Симптом | Объяснение |
|---|---|
| PID 1137814/1137815 (VLLM::Worker_TP0/TP1) сохранялись через все 5 циклов | Процессы принадлежали systemd, а не удаляемым Pod'ам |
| TP0+TP1 при `tensor-parallel-size: "1"` в Deployment | Systemd unit использовал `--tensor-parallel-size 2` |
| GPU память не освобождалась | systemd перезапускал процессы при kill |
| Cycle 5 CrashLoopBackOff | Обе GPU заняты (21.65 GiB × 2), новому Pod'у не хватило VRAM |
| cgroup = `/system.slice/vllm-32b.service` (не `kubepods.slice/...`) | Прямое доказательство — не Kubernetes |

**Статус: RESOLVED.** Сервис остановлен и отключён (`systemctl disable`). GPU полностью свободны.

---

## Выполненные действия (итерация 9)

### P0 — Root cause устранён

| № | Действие | Статус | Детали |
|---|---|---|---|
| 1 | **Forensic diagnosis PID 1137814/1137815** | ✅ | cgroup, PPID, cmdline, namespace — все указывают на systemd unit |
| 2 | **Kill stale processes** | ✅ | SIGKILL через `systemctl kill -s KILL` |
| 3 | **Stop+disable vllm-32b.service** | ✅ | `systemctl disable` — сервис больше не запустится |
| 4 | **Cordon n7** | ✅ | До 5 чистых циклов |
| 5 | **32B перезапущен на n8** | ✅ | Running 1/1, Restarts=0 |
| 6 | **32B Completion test** | ✅ | `"Paris. Yes, that's correct..."` |
| 7 | **API stability test — 30 запросов** | ✅ | 29/30 успешно (96.7%) |

### P1 — Функциональность

| № | Действие | Статус |
|---|---|---|
| 8 | 32B Completion подтверждён | ✅ |
| 9 | Фиксация source модели | 🟡 **model-source.md** создан, но repository/SHA не зафиксированы |
| 10 | 14B Chat тест | 🟡 Ожидает (CPU offload 10GB) |

### P2 — Стабильность

| № | Действие | Статус |
|---|---|---|
| 11 | 5 чистых orphan-циклов на n7 | 🔴 Не проведены (будет после восстановления n7) |
| 12 | API stability — 1000 запросов | 🔴 Не проведён |
| 13 | Load test 60 мин | 🔴 Не проведён |

### P3 — Эксплуатация

| № | Действие | Статус |
|---|---|---|
| 14 | DCGM Exporter + canary | ✅ Каждые 5 мин |
| 15 | Regression gate skill | ✅ `k8s-gpu/deployment-regression-gates` |

---

## Отчёты

| Файл | Описание |
|---|---|
| `docs/n7-forensic-root-cause.md` | **NEW** — Полный forensic: root cause найден (systemd unit) |
| `docs/n7-recovery-results.md` | Исходный отчёт (методология признана недействительной) |
| `docs/api-stability-results.md` | 30 запросов, 96.7% |
| `docs/current-status.md` | **v5.0** — Актуальный статус (этот файл) |

---

## Известные проблемы

### 🔴 Критические

1. **Kubernetes API — единичные timeout.** 1 из 30 (холодный старт). Требуется тест 1000 запросов.
2. **n7 требует 5 чистых циклов** перед возвратом в эксплуатацию.
3. **Отказоустойчивость отсутствует.** Обе модели на одной ноде (n8).

### 🟡 Важные

4. **14B с CPU offload 10GB.** Медленный холодный старт (60+ сек).
5. **32B — Base модель.** Completion только. Chat требует Instruct-GPTQ.
6. **NetworkPolicy не работает.** Flannel.

---

## Итоговая оценка

| Компонент | Оценка | Изменение |
|---|---|---|
| Root cause orphan | ✅ **RESOLVED** | ⬆️ Было MITIGATED |
| 32B | 60% | ⬆️ После переезда на n8 |
| 14B | 70% | Без изменений |
| Kubernetes-манифесты | 85-90% | Без изменений |
| Мониторинг | 30% | Без изменений |
| API стабильность | 96.7% (30 запросов) | 🟡 Предварительно |
| Отказоустойчивость | 20% | Без изменений |
| **Промышленная готовность** | **~40-45%** | ⬆️ После RESOLVED root cause |

---

## Приоритет дальше

### P0 — восстановление n7
1. 5 чистых циклов `scale 1 → scale 0 → verify GPU clean` на n7
2. Если успешно — uncordon n7 + вернуть label

### P1 — функциональность
3. API stability: 1000 запросов (локально с n8 и удалённо)
4. Заменить 32B Base на Instruct-GPTQ

### P2 — стабильность
5. Load test 60 мин
6. Failover test (n7 → n8)

### P3 — эксплуатация
7. Semantic canary
8. Prometheus + Grafana
9. Сетевая изоляция (Calico/Cilium проект)
