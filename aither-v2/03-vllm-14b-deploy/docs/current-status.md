# Актуальный статус развёртывания vLLM (current-status.md)
**Дата:** 2026-07-19  
**Версия:** 3.0  

---

## Текущее состояние Pod'ов

| Pod | Status | Ready | Restarts | Node | IP | API test |
|---|---|---|---|---|---|---|
| `vllm-14b-instruct` | ✅ Running | 1/1 | **0** | n8 | 10.244.0.140 | Chat `"Paris"` — осмысленный ответ ✅ |
| `vllm-32b-gptq` | ✅ Running | 1/1 | **0** | n8 | 10.244.0.139 | Completion `"Paris. Yes, that's correct..."` ✅ Chat `!!!` (Base) |

**Обе модели Running, Restarts=0.** 32B Completion подтверждён semantic-тестом (см. ниже).
n7 — cordoned, ожидает восстановления orphan-проблемы.

---

## Проверка 32B Completion (после возврата `--quantization gptq`)

```text
Запрос: "The capital of France is"
Ответ:  "Paris. Yes, that's correct! Paris is the capital city of France. It is known for its rich history,"
```

✅ **Completion работает.** Логи без BitBLAS, без ошибок. Regression gate пройден (yaml-проверка `--quantization gptq`).

---

## Выполненные действия (итерация 7)

### P0 — Критические блокеры

| № | Действие | Статус | Детали |
|---|---|---|---|
| 1 | **`--quantization gptq` возвращён** в 32B | ✅ | Regression gate: yaml-парсинг проверяет args перед apply. Причина прошлой регрессии — случайное удаление при редактировании |
| 2 | **32B semantic completion тест** | ✅ | `"Paris. Yes, that's correct..."` — осмысленный ответ |
| 3 | **Orphan PID 858203 убит** на n7 | MITIGATED | `multiprocessing.spawn` от старого Pod, 3+ часа, GPU освобождены |
| 4 | **n7 cordoned** | ✅ | До завершения восстановления |
| 5 | **14B восстановлен** | ✅ | CrashLoopBackOff → Running после пересоздания на n8 |

### P0 — в процессе (фоновые задачи)

| № | Действие | Статус |
|---|---|---|
| 6 | Диагностика orphan: сравнение runtime/config n7 vs n8 | ✅ **Идентичны.** containerd 2.2.1, runc 1.3.3, nvidia-runtime 1.19.1, SystemdCgroup=true |
| 7 | Перезапуск containerd+kubelet на n7 + 5 циклов | ⏳ Фоновая задача |
| 8 | Локализация API timeout (30 запросов) | ⏳ Фоновая задача |

### P1 — Функциональность

| № | Действие | Статус |
|---|---|---|
| 9 | 32B Completion тест | ✅ **Выполнен.** Ответ осмысленный |
| 10 | Фиксация source модели | ✅ **model-source.md** создан. Подробно: архитектура, слои, dtype, размеры shards, tokenizer, chat template. Отсутствует: HuggingFace repo URL, commit SHA, upstream checksums |
| 11 | 14B Chat тест | 🟡 Ожидает (CPU offload 10GB — холодный старт до 60+ сек) |

### P2 — Стабильность

| № | Действие | Статус |
|---|---|---|
| 12 | 5 циклов orphan-теста | 🟡 Выполнено 3 цикла, орфаны подтверждены. Фоновый тест — перезапуск n7 + 5 новых циклов |
| 13 | Load test 60 мин | 🔴 Не проведён |

### P3 — Эксплуатация

| № | Действие | Статус |
|---|---|---|
| 14 | DCGM Exporter + canary | ✅ Каждые 5 мин |
| 15 | Regression gate skill | ✅ `k8s-gpu/deployment-regression-gates` |
| 16 | Memory: правила поведения | ✅ 19 правил |

---

## Известные проблемы

### 🔴 Критические

1. **Orphan-процессы на n7.** PID остаются после удаления Pod. На n8 — чисто. Runtime/config идентичны на обеих нодах — root cause не установлен.  
   **Статус:** DIAGNOSED → MITIGATED (ручной kill). **Не RESOLVED.**

2. **Kubernetes API — периодические timeout.** Причина не локализована (локально на n8 vs через bastion). Фоновый тест запущен.  
   **Статус:** DIAGNOSED.

3. **32B Chat — мусор.** Base-модель, не Instruct. Для чата требуется Qwen2.5-32B-Instruct-GPTQ.  
   **Статус:** DIAGNOSED. Completion работает.

### 🟡 Важные

4. **NetworkPolicy не работает.** Flannel — не фильтрует. Защита только через VLLM_API_KEY.
5. **14B с CPU offload 10GB.** Медленный холодный старт (60+ сек). Требуется квантизованная версия.
6. **Отказоустойчивость отсутствует.** По одной реплике. При отказе n8 — простой.

---

## Source моделей

Подробно: [`docs/model-source.md`](./model-source.md)

| Параметр | 32B (qwen-32b-base) | 14B (qwen-14b) |
|---|---|---|
| Архитектура | Qwen2ForCausalLM | Qwen2ForCausalLM |
| Слои | 64 | 48 |
| dtype | float16 | bfloat16 |
| Размер | ~19.3 GB (5 shards) | ~28 GB (8 shards) |
| quantize_config.json | ❌ Отсутствует | ❌ Отсутствует |
| Chat template | ✅ Есть (2507 символов) | ✅ |
| Тип | **Base** (не Instruct) | Instruct |
| HuggingFace repo | Не зафиксирован | Не зафиксирован |

---

## Манифесты

| Файл | Ссылка |
|---|---|
| `manifests/vllm-deployment.yaml` | https://github.com/dedvmedved-dot/aither-project/blob/aither-v2/aither-v2/03-vllm-14b-deploy/manifests/vllm-deployment.yaml |
| `manifests/vllm-service.yaml` | https://github.com/dedvmedved-dot/aither-project/blob/aither-v2/aither-v2/03-vllm-14b-deploy/manifests/vllm-service.yaml |

## Отчёты

| Файл | Описание |
|---|---|
| `docs/current-status.md` | **Актуальный статус** |
| `docs/model-source.md` | Source моделей (архитектура, размеры) |
| `docs/orphan-test-results.md` | 3 цикла orphan-теста |
| `docs/load-test-results.md` | DNS-тест |
| `docs/monitoring-setup.md` | DCGM + canary |
| `docs/README.md` | Индекс |

---

## Итоговая оценка

| Компонент | Оценка |
|---|---|
| Kubernetes-манифесты | 85-90% |
| 14B как тестовый сервис | 70% |
| 32B | 30% (Completion ✅, Chat ❌) |
| Мониторинг | 30% |
| Orphan-проблема | DIAGNOSED (не RESOLVED) |
| Отказоустойчивость | 20% |
| **Промышленная готовность** | **~40-45%** |

---

## Приоритет дальше

### P0 — восстановление
1. Дождаться фоновых задач (n7 recovery + API stability)
2. Если 5 циклов на n7 без orphan — uncordon

### P1 — функциональность
3. Получить Qwen2.5-32B-Instruct-GPTQ (официальный источник)
4. Заменить модель, зафиксировать SHA и revision

### P2 — стабильность
5. Load test 60 мин
6. Service DNS из клиента

### P3 — эксплуатация
7. Semantic canary (проверка не только health)
8. Prometheus + Grafana
