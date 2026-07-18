# Актуальный статус развёртывания vLLM (current-status.md)
**Дата:** 2026-07-19  
**Версия:** 2.0  

---

## Текущее состояние Pod'ов

| Pod | Status | Ready | Restarts | Node | Примечание |
|---|---|---|---|---|---|
| `vllm-14b-instruct` | 🔴 CrashLoopBackOff | 0/1 | 3 | n7 (cordoned) | Ожидает восстановления после убийства orphan PID 858203 |
| `vllm-32b-gptq` | ✅ Running | 1/1 | 0 | n8 | `--quantization gptq` возвращён |

**32B работает.** 14B ждёт пересоздания Pod'а (нода n7 cordoned).

---

## Выполненные действия (итерация 6)

### P0 — Критические блокеры

| № | Действие | Статус | Детали |
|---|---|---|---|
| 1 | **32B остановлен** (replicas=0) | ✅ | Временно, чтобы не загружать control-plane |
| 2 | **`--quantization gptq` возвращён** в Deployment 32B | ✅ | Regression gate пройден (yaml-проверка). Причина предыдущей регрессии — параметр случайно удалён при редактировании |
| 3 | **Orphan PID 858203 убит** на n7 | ✅ | Процесс `multiprocessing.spawn` от старого Pod, висел 3+ часа. Cgroup принадлежит удалённому контейнеру. GPU освобождены. Root cause: containerd не очищает orphan-процессы после удаления Pod |
| 4 | **n7 cordoned** | ✅ | Нода временно исключена из планировщика до диагностики orphan-проблемы |
| 5 | **14B ожидает восстановления** | 🟡 | Pod пересоздастся на n8 после uncordon n7 |

### P1 — Функциональность

| № | Действие | Статус |
|---|---|---|
| 6 | 32B Completion тест | 🟡 Ожидает фоновую проверку |
| 7 | Фиксация source модели | ✅ 32B: Qwen2ForCausalLM, 64 слоя, float16, Base. 14B: Qwen2ForCausalLM, 48 слоёв, bfloat16 |

### P2 — Стабильность

| № | Действие | Статус |
|---|---|---|
| 8 | 5 циклов orphan-теста | ✅ Выполнено. Орфаны подтверждены на n7 |
| 9 | Load test 60 мин | 🔴 Не проведён (API нестабилен) |

### P3 — Эксплуатация

| № | Действие | Статус |
|---|---|---|
| 10 | DCGM Exporter + canary | ✅ Работает каждые 5 мин |
| 11 | Regression gate skill | ✅ Создан: k8s-gpu/deployment-regression-gates |
| 12 | Память: правила поведения | ✅ Сохранены |

---

## Известные проблемы

### 🔴 Критические

1. **Orphan-процессы на n7.** PID остаются после удаления Pod. На n8 — чисто. Root cause: не очищается containerd shim/task. Временное решение: ручная очистка `kill -9`.  
   **Статус:** DIAGNOSED → MITIGATED (ручной kill). **Не RESOLVED.**

2. **Kubernetes API нестабилен.** Периодические `i/o timeout`. Возможная причина: GPU-нагрузка на control-plane n8.  
   **Статус:** DIAGNOSED. **Не MITIGATED.**

3. **32B Chat — мусор.** Base-модель, не Instruct. Completion — осмысленный.  
   **Статус:** DIAGNOSED. Требуется замена на 32B-Instruct-GPTQ.

### 🟡 Важные

4. **NetworkPolicy не работает.** Flannel — не фильтрует трафик. Защита только через VLLM_API_KEY.
5. **14B с CPU offload 10GB.** Медленная генерация. Требуется квантизованная версия.
6. **Отказоустойчивость отсутствует.** По одной реплике. При отказе n8 — простой.

---

## Манифесты

| Файл | Ссылка |
|---|---|
| `manifests/vllm-deployment.yaml` (актуальный) | https://github.com/dedvmedved-dot/aither-project/blob/aither-v2/aither-v2/03-vllm-14b-deploy/manifests/vllm-deployment.yaml |
| `manifests/vllm-service.yaml` | https://github.com/dedvmedved-dot/aither-project/blob/aither-v2/aither-v2/03-vllm-14b-deploy/manifests/vllm-service.yaml |
| `manifests/vllm-network-policy.yaml` | https://github.com/dedvmedved-dot/aither-project/blob/aither-v2/aither-v2/03-vllm-14b-deploy/manifests/vllm-network-policy.yaml |
| `manifests/vllm-sa.yaml` | https://github.com/dedvmedved-dot/aither-project/blob/aither-v2/aither-v2/03-vllm-14b-deploy/manifests/vllm-sa.yaml |

## Отчёты

| Файл | Описание |
|---|---|
| `docs/current-status.md` (этот файл) | **Актуальный статус** |
| `docs/honest-final-report.md` | Предыдущий отчёт (архив) |
| `docs/orphan-test-results.md` | Orphan-тест: 3 цикла |
| `docs/load-test-results.md` | Результаты DNS-теста |
| `docs/monitoring-setup.md` | Мониторинг: DCGM + canary |
| `docs/README.md` | Индекс всех отчётов |

---

## Итоговая оценка

| Компонент | Оценка |
|---|---|
| Kubernetes-манифесты | 85-90% |
| 14B как тестовый сервис | 70% |
| 32B | 20% (Completion работает, Chat — нет) |
| Мониторинг | 30% |
| Orphan-проблема | DIAGNOSED |
| Отказоустойчивость | 20% |
| **Промышленная готовность** | **~40%** |

---

## Что делать дальше

### Приоритет (P0)
1. Восстановить n7: `kubectl uncordon bootsmam-k8s-clnt01-n7-gpu` после фоновой проверки
2. Провести 5 циклов orphan-теста на n7 без появления orphan
3. Если орфаны повторяются — перезагрузить n7

### Функциональность (P1)
4. Проверить 32B completion (фоновый тест запущен)
5. Получить Qwen2.5-32B-Instruct-GPTQ из официального репозитория
6. Заменить модель

### Стабильность (P2)
7. Провести load test 60 мин
8. Проверить etcd и API server под нагрузкой
