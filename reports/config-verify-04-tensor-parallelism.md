# Отчёт: Tensor Parallelism (TP=2) — верификация задачи #4 ROADMAP

**Задача:** #4 — Tensor Parallelism (TP=2)
**Дата проверки:** 27.07.2026 17:45 МСК
**Метод:** kubectl (deployment args, resources, logs), nvidia-smi (node + inside pod)
**Результат:** ⚠️ 14B TP=2 ✅, 32B TP=1 ❌

---

## 1. vLLM 14B-Instruct (N8) — TP=2 ✅

### Deployment

| Параметр | Значение |
|---|---|
| `--tensor-parallel-size` | **2** |
| `nvidia.com/gpu` (limits) | **2** |
| NodeSelector | `aither.io/vllm14b-primary: "true"` → N8 |

### vLLM Logs (старт)

```
tensor_parallel_size=2
rank 0 in world size 2: DP rank 0, PP rank 0, TP rank 0
rank 1 in world size 2: DP rank 0, PP rank 0, TP rank 1
```

### nvidia-smi на узле (N8)

| GPU | VRAM Used | VRAM Total | P-State | Процесс |
|---|---|---|---|---|
| GPU 0 | 20,185 MiB | 23,040 MiB | P0 | vLLM (rank 0) |
| GPU 1 | 20,185 MiB | 23,040 MiB | P0 | vLLM (rank 1) |

### nvidia-smi внутри пода

| GPU | VRAM Used |
|---|---|
| GPU 0 | 20,185 MiB |
| GPU 1 | 20,185 MiB |

**14B: TP=2 работает корректно. Обе GPU загружены равномерно. ✅**

---

## 2. vLLM 32B-GPTQ (N7) — TP=1 ❌

### Deployment

| Параметр | Значение | Ожидалось |
|---|---|---|
| `--tensor-parallel-size` | **1** ❌ | 2 |
| `nvidia.com/gpu` (limits) | **1** ❌ | 2 |
| NodeSelector | `aither.io/qwen32b-gptq: "true"` → N7 | — |

### vLLM Logs (старт)

Отсутствуют записи `tensor_parallel_size=2` или `world size`. Под запущен с TP=1 по умолчанию.

### nvidia-smi на узле (N7)

| GPU | VRAM Used | VRAM Total | P-State | Процесс |
|---|---|---|---|---|
| GPU 0 | 21,865 MiB | 23,040 MiB | P0 | vLLM (один процесс) |
| GPU 1 | **0 MiB** | 23,040 MiB | **P8** | — (простаивает) |

### nvidia-smi внутри пода

| GPU | VRAM Used |
|---|---|
| GPU 0 | 21,865 MiB |
| GPU 1 | — (не виден) |

**32B: TP=1. Модель на одном GPU. GPU#1 простаивает. ❌**

---

## 3. Сравнение

| Параметр | 14B (N8) | 32B (N7) |
|---|---|---|
| `--tensor-parallel-size` | **2** ✅ | **1** ❌ |
| `nvidia.com/gpu` limits | **2** ✅ | **1** ❌ |
| vLLM world size | **2** ✅ | **1** ❌ |
| GPU#0 | 20,185 MiB P0 | 21,865 MiB P0 |
| GPU#1 | 20,185 MiB P0 | **0 MiB P8** ❌ |
| Статус | ✅ TP=2 | ❌ TP=1 |

---

## 4. Влияние TP=1 на 32B

| Последствие | Описание |
|---|---|
| Производительность | Модель на 1 GPU вместо 2. ~50% потеря теоретической производительности |
| VRAM | 21,865 / 23,040 MiB = 95%. Критический запас. KV-кеш ограничен |
| GPU#1 простаивает | 23 GB не используются. Ресурс wasted |
| KV-кеш | В 2 раза меньше, чем при TP=2 |
| Максимальный batch | Ограничен одним GPU |

---

## 5. Причина

32B деплоймент не был обновлён при миграции 14B на N8 (EMG-01). Его манифест остался в исходном состоянии с `tensor-parallel-size=1` и `nvidia.com/gpu: 1`.

---

## 6. Исправление

```bash
kubectl patch deployment vllm-32b-gptq -n aither-inference --type='json' -p='[
  {"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/nvidia.com~1gpu", "value": "2"},
  {"op": "replace", "path": "/spec/template/spec/containers/0/resources/requests/nvidia.com~1gpu", "value": "2"}
]'

kubectl set args deployment/vllm-32b-gptq -n aither-inference -- \
  --tensor-parallel-size=2 \
  --model=/model --quantization=gptq --dtype=half \
  --host=0.0.0.0 --port=8000 \
  --gpu-memory-utilization=0.90 --max-model-len=4096 \
  --max-num-seqs=1 --enforce-eager --generation-config=vllm \
  --served-model-name=qwen-32b-base \
  --disable-log-requests --disable-fastapi-docs
```

Требуется: `kubectl rollout restart deployment/vllm-32b-gptq -n aither-inference`
Даунтайм: ~2 минуты (пока модель перезагрузится на 2 GPU).

---

## 7. Вывод

| Критерий | 14B | 32B |
|---|---|---|
| TP аргумент | `--tensor-parallel-size 2` ✅ | `--tensor-parallel-size 1` ❌ |
| GPU resources | `nvidia.com/gpu: 2` ✅ | `nvidia.com/gpu: 1` ❌ |
| vLLM world size | 2 ✅ | 1 ❌ |
| GPU#0 загружен | ✅ 20.2 GB | ✅ 21.9 GB |
| GPU#1 загружен | ✅ 20.2 GB | ❌ 0 GB (P8 idle) |

**Задача #4 ROADMAP («Tensor Parallelism TP=2»): 14B — ВЫПОЛНЕНА. 32B — БАГ (TP=1). Требуется исправление деплоймента 32B.**
