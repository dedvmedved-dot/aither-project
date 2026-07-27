# Отчёт: vLLM 14B загрузка и запуск — верификация задачи #3 ROADMAP

**Задача:** #3 — vLLM 14B загрузка и запуск
**Дата проверки:** 27.07.2026 17:15 МСК
**Метод:** Live-команды kubectl, nvidia-smi, curl, логи vLLM
**Результат:** ✅ РАБОТАЕТ

---

## 1. Deployment

| Параметр | Значение |
|---|---|
| **Имя** | `vllm-14b-instruct` |
| **Namespace** | `aither-inference` |
| **Образ** | `vllm/vllm-openai@sha256:6cf9808...` |
| **RuntimeClass** | `nvidia` |
| **NodeSelector** | `aither.io/vllm14b-primary: "true"` → N8 |
| **GPU request** | `nvidia.com/gpu: 2` |
| **Порт** | 8000 |
| **Модель** | Qwen2.5-14B-Instruct (FP16, 28 GB) с диска N8 |

---

## 2. Аргументы запуска

| Аргумент | Значение | Назначение |
|---|---|---|
| `--model` | `/model` | Путь к модели (hostPath с N8) |
| `--tensor-parallel-size` | **2** | Обе GPU RTX 6000 |
| `--host` | `0.0.0.0` | Слушать на всех интерфейсах |
| `--port` | `8000` | Стандартный порт vLLM |
| `--gpu-memory-utilization` | `0.90` | 90% VRAM под модель + KV-кеш |
| `--max-model-len` | `4096` | Максимальная длина контекста |
| `--dtype` | `half` | FP16 |
| `--max-num-seqs` | `1` | Одно concurrent sequence |
| `--enforce-eager` | ✓ | Без FlashAttention-2 (Turing SM 7.5) |
| `--generation-config` | `vllm` | Встроенная конфигурация генерации |
| `--served-model-name` | `qwen-14b` | Имя модели для API |
| `--disable-log-requests` | ✓ | Не логировать каждый запрос |
| `--disable-fastapi-docs` | ✓ | Без /docs эндпоинта |

---

## 3. Старт модели (из логов)

```
04:18:00  Automatically detected platform cuda.
04:18:03  vLLM API server version 0.8.5
04:18:12  tensor_parallel_size=2
04:18:12  Compute Capability < 8.0 → Falling back to V0 engine (Turing SM 7.5)
04:18:19  Using XFormers backend (FlashAttention-2 не поддерживается)
04:18:25  NCCL 2.21.5
04:18:40  rank 0 TP=0, rank 1 TP=1  (2 worker процесса)
04:18:40  Starting to load model /model...

  Загрузка 8 shard'ов safetensors:
  0% → 12% → 25% → 38% → 50% → 62% → 75% → 88% → 100%
  Время загрузки: 17.08 сек
  Model weights: 13.76 GiB

04:19:03  KV Cache: 5.52 GiB
          Total GPU: 21.97 GiB × 0.90 = 19.78 GiB
          CUDA blocks: 3768, Max concurrency: 14.72×

04:19:07  Starting vLLM API server on http://0.0.0.0:8000
```

**Старт занял: 67 секунд** (04:18:00 → 04:19:07)

---

## 4. Состояние пода

| Параметр | Значение |
|---|---|
| **Pod** | `vllm-14b-instruct-fd45456b-jjmnh` |
| **Статус** | Running |
| **Ready** | 1/1 |
| **Рестарты** | 0 |
| **Возраст** | 3 часа |
| **Узел** | bootsman-k8s-clnt01-n8-gpu |
| **Pod IP** | 10.244.0.142 |

---

## 5. GPU-использование (nvidia-smi на N8)

| GPU | Модель | VRAM | Температура | P-State | Процесс |
|---|---|---|---|---|---|
| GPU 0 | Quadro RTX 6000 | 20,185 / 23,040 MiB | 32°C | P0 | `/usr/bin/python3` (vLLM, 20,170 MiB) |
| GPU 1 | Quadro RTX 6000 | 20,185 / 23,040 MiB | 32°C | P0 | `/usr/bin/python3` (vLLM, 20,170 MiB) |

Обе GPU загружены. TP=2 работает. Температура в норме.

---

## 6. Health-проверки

| Проверка | Результат |
|---|---|
| K8s readiness probe | ✅ Все health-чеки → HTTP 200 |
| Service ClusterIP | ✅ `vllm-14b-instruct:8000` |
| `/health` (изнутри пода) | ✅ HTTP 200 |
| `/v1/models` (изнутри пода) | ⚠️ 401 Unauthorized (требуется API-ключ) |

---

## 7. Монтирование модели

| Тип | Путь на хосте | Путь в контейнере |
|---|---|---|
| **hostPath** | `/data/models/Qwen2.5-14B-Instruct` (28 GB) | `/model` |
| **emptyDir (Memory)** | — | `/dev/shm` |

Модель загружается с локального SSD, не из HuggingFace.

---

## 8. Ограничения

| Ограничение | Причина |
|---|---|
| `--enforce-eager` | Turing SM 7.5 < 8.0 (нет FlashAttention-2) |
| `--max-num-seqs 1` | Ограничение для стабильности |
| `--max-model-len 4096` | 14B с TP=2 на Turing |
| Без `--enable-lora` | LoRA не загружен (адаптер astra-14b не используется) |
| Без `--cpu-offload-gb` | Модель полностью на GPU (исправлено в EMG-01) |

---

## 9. Вывод

| Критерий | Статус |
|---|---|
| vLLM под запущен и Ready | ✅ 1/1 Running, 0 рестартов |
| Модель загружена (28 GB, 8 shard'ов) | ✅ 17.08 сек |
| TP=2 на обеих GPU | ✅ GPU#0 20.2 GB, GPU#1 20.2 GB |
| API server слушает | ✅ Порт 8000 |
| Health-пробы проходят | ✅ Стабильно HTTP 200 |
| KV-кеш аллоцирован | ✅ 5.52 GiB, 3768 блоков |
| Температура GPU | ✅ 32°C (норма) |
| Модель с локального диска | ✅ `/data/models/` → `/model` |
| NCCL (меж-GPU коммуникация) | ✅ nccl 2.21.5 |

**Задача #3 ROADMAP («vLLM 14B загрузка и запуск»): ВЫПОЛНЕНА. Работает стабильно на N8 с TP=2.**
