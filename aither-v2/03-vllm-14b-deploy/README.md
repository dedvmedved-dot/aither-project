# Этап 3: vLLM — запуск инференса Qwen

## Роль в дорожной карте

Этап 3 — первый real-workload: vLLM с Qwen моделями в Kubernetes на GPU-кластере из 2× RTX 6000 на каждой ноде.

```
┌──────────────────────────────────────────────────┐
│                    Этап 7                         │
│                 OAuth / Portal                    │
├──────────────────────────────────────────────────┤
│                    Этап 6                         │
│              Portal SPA + BFF + SSE               │
├──────────────────────────────────────────────────┤
│                    Этап 5                         │
│            Gateway + Redis / Rate Limit           │
├──────────────────────────────────────────────────┤
│                    Этап 4                         │
│        Tensor Parallelism (2× RTX 6000)           │
├──────────────────────────────────────────────────┤
│      ┌──────────────┴──────────────┐              │
│      │   ЭТАП 3 (vLLM)            │  ← ВЫ ЗДЕСЬ │
│      └──────────────┬──────────────┘              │
├──────────────────────────────────────────────────┤
│                    Этап 2                         │
│            containerd + NVIDIA Runtime            │
├──────────────────────────────────────────────────┤
│                    Этап 1                         │
│            K8s + GPU Operator                    │
└──────────────────────────────────────────────────┘
```

---

## Конфигурация кластера

| Узел | Роль | GPU | Модели на диске |
|------|------|-----|-----------------|
| **n8** (`10.129.13.78`) | Worker + control-plane | 2× RTX 6000 23GB | `Qwen2.5-Coder-14B-Instruct` (работает) `Qwen2.5-14B-Instruct` `Qwen2.5-32B-GPTQ` |
| **n7** (`10.129.13.77`) | Worker | 2× RTX 6000 23GB | `Qwen2.5-32B-GPTQ` (готов к запуску) `Qwen2.5-14B-Instruct` (частично) |

> **Важно:** RTX 6000 (Turing, CC 7.5) **не поддерживает bfloat16**. Все модели запускать с `--dtype half` (float16).

### Доступные модели

| Модель | Размер | Формат | RAM на диске | GPU RAM (загрузка) | Влезает в 1× RTX 6000? |
|--------|--------|--------|-------------|-------------------|------------------------|
| **Qwen2.5-Coder-14B-Instruct** | 14B | fp16 | 28GB | 21.6GB + KV Cache | ❌ Только TP=2 (2 GPU) |
| **Qwen2.5-14B-Instruct** | 14B | fp16 | 28GB | 21.6GB + KV Cache | ❌ Требует CPU offload |
| **Qwen2.5-32B-GPTQ** | 32B | GPTQ 4-bit | 19GB | ~10GB | ✅ С запасом |

---

## Архитектура развёртывания (текущая)

```
                    ┌──────────────────────┐
                    │   Пользователь        │
                    │   curl / v1/completions│
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  Service: vllm-api   │
                    │  ClusterIP :8000     │
                    └──────────┬───────────┘
                               │
          ┌────────────────────┴────────────────────┐
          │                                         │
┌─────────▼──────────┐                 ┌────────────▼─────────┐
│   n8 (GPU 0,1)     │                 │   n7 (GPU 0)         │
│ Coder-14B-Instruct │                 │ 32B-GPTQ             │
│ TP=2, port 8000    │                 │ TP=1, port 8001      │
│ ──────────────     │                 │ ──────────────       │
│ ✅ Работает        │                 │ ❌ Ждёт развёртывания │
└────────────────────┘                 └──────────────────────┘
```

---

## Текущее состояние

| Компонент | Статус | Примечание |
|-----------|--------|------------|
| **Namespace** aither-inference | ✅ Создан | — |
| **ServiceAccount** vllm-sa | ✅ Создан | С правами на pods/log |
| **Service** vllm-api | ✅ ClusterIP :8000 | Порт 8001 добавлен для 32B |
| **PV / PVC** | ❌ Не используется | Используется `hostPath: /data/models` на каждой ноде |
| **Deployment: Coder-14B** (n8) | ✅ **Running** | TP=2, оба GPU, default namespace |
| **Deployment: 14B-Instruct** (n7) | ❌ CrashLoopBackOff | OOM — 14B fp16 не влезает в 23GB |
| **Deployment: 32B-GPTQ** (n7) | ❌ Не развёрнут | Модель на диске ✅, ждёт запуска |
| GPU в Capacity | ✅ 2/2 на n8, 2/2 на n7 | — |
| NVIDIA RuntimeClass | ✅ nvidia | — |

### Почему 14B не работает на 1× RTX 6000

14B параметров в float16 = 28GB весов. PyTorch аллоцирует ~21.6GB на загрузку,
плюс KV Cache (~1-4GB). RTX 6000 имеет 23GB HBM2 — не хватает даже на минимальный контекст.

**Решение:** `--cpu-offload-gb 4` + `--max-model-len 1024` частично решает,
но для production используем **32B-GPTQ** (4-bit, ~10GB в GPU).

---

## Последовательность развёртывания

### Prerequisites

```bash
# Модели должны быть на каждой ноде локально в /data/models/
ssh n8 "ls /data/models/Qwen2.5-32B-GPTQ/model-00001-of-00005.safetensors"
ssh n7 "ls /data/models/Qwen2.5-32B-GPTQ/model-00005-of-00005.safetensors"

# Если модели нет на n7 — скопировать с n8:
# Через bastion:
ssh n7 "rsync -avP 10.129.13.78:/data/models/Qwen2.5-32B-GPTQ/ /data/models/Qwen2.5-32B-GPTQ/"
```

### 1. Создать namespace, SA, Service

```bash
kubectl apply -f manifests/vllm-namespace.yaml
kubectl apply -f manifests/vllm-sa.yaml
kubectl apply -f manifests/vllm-service.yaml
```

### 2. Развернуть vLLM с выбранной моделью

> **Рекомендуется:** `vllm-deployment.yaml` содержит два Deployment — 14B-Instruct (CPU offload) и 32B-GPTQ.
> Выберите один и примените.

**Вариант A: 32B-GPTQ (рекомендуется)**
```yaml
# manifests/vllm-deployment.yaml — секция vllm-32b-gptq
# --tensor-parallel-size 1
# --model /models/Qwen2.5-32B-GPTQ
kubectl delete deployment -n aither-inference vllm-14b-instruct 2>/dev/null; \
kubectl apply -f manifests/vllm-deployment.yaml
```

**Вариант B: 14B-Instruct с CPU offload**
```yaml
# manifests/vllm-deployment.yaml — секция vllm-14b-instruct
# --cpu-offload-gb 4, --max-model-len 4096
kubectl delete deployment -n aither-inference vllm-32b-gptq 2>/dev/null; \
kubectl apply -f manifests/vllm-deployment.yaml
```

### 3. Проверить состояние

```bash
kubectl get pods -n aither-inference -w
# NAME                                 READY   STATUS    RESTARTS   AGE
# vllm-32b-gptq-xxxxxxxxx-xxxxx        1/1     Running   0          2m

kubectl logs -n aither-inference -l app=vllm --tail=5
# INFO:     Application startup complete.
```

### 4. Проверить API

```bash
# Прямой тест через port-forward
kubectl port-forward -n aither-inference svc/vllm-api 8000:8000 &

# 32B-GPTQ
curl http://localhost:8001/health
# {"status": "ok"}

curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen2.5-32B-GPTQ",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 64
  }'
```

---

## Схемы

### Архитектура компонентов (текстовая)

```
                                        ┌──────────────────────┐
                                        │     Пользователь     │
                                        │  curl /v1/completions │
                                        └──────────┬───────────┘
                                                   │
                                        ┌──────────▼───────────┐
                                        │  Service: vllm-api   │
                                        │  ClusterIP :8000/8001│
                                        └──────────┬───────────┘
                                                   │
      ┌────────────────────────────────────────────┴────────────┐
      │                                                         │
┌─────▼──────────────────┐            ┌────────────────────────▼─────┐
│  n8 (2× RTX 6000)     │            │  n7 (2× RTX 6000)           │
│                        │            │                              │
│  ┌──────────────────┐  │            │  ┌──────────────────────┐   │
│  │ Coder-14B-Instruct│  │            │  │ 32B-GPTQ (не развёрнут)│   │
│  │ TP=2, порт 8000  │  │            │  │ TP=1, GPU 0, порт 8001│   │
│  │ ✅ Running       │  │            │  │ ~10GB VRAM            │   │
│  └──────────────────┘  │            │  └──────────────────────┘   │
│                        │            │                              │
│ /data/models/          │            │ /data/models/                │
│ ├ Coder-14B ✅         │            │ ├ 32B-GPTQ ✅ (19GB на диске) │
│ ├ 14B-Instruct ✅      │            │ └ 14B-Instruct ⚠️ (частично) │
│ └ 32B-GPTQ ✅          │            │                              │
└────────────────────────┘            └──────────────────────────────┘
```

### Последовательность развёртывания (текстовая)

```
    ┌──────────────────────┐
    │    1. ПОДГОТОВКА      │
    │ namespace + SA + RBAC │
    │ проверить модели      │
    │ hostPath: /data/models│
    └──────────┬───────────┘
               │
    ┌──────────▼───────────┐
    │    2. ВЫБОР МОДЕЛИ    │
    │ ┌─── 32B-GPTQ ◄──────┼─── РЕКОМЕНДУЕТСЯ
    │ │  (1 GPU, ~10GB)     │
    │ └─── 14B-Instruct     │
    │      (CPU offload 4GB)│
    └──────────┬───────────┘
               │
    ┌──────────▼───────────┐
    │    3. РАЗВЁРТЫВАНИЕ   │
    │ kubectl apply -f      │
    │ Deployment + Service  │
    └──────────┬───────────┘
               │
    ┌──────────▼───────────┐
    │    4. ПРОВЕРКА        │
    │ Pod Running 1/1       │
    │ Log: startup complete │
    │ curl /health → ok     │
    └──────────┬───────────┘
               │
    ┌──────────┴───────────┐
    ▼                      ▼
 Успех → Gateway      Ошибка → диагностика:
 (Этап 5)                    nvidia-smi, логи,
                              cleanup GPU, offload
```

### Визуализация DOT → PNG

Исходные диаграммы в формате DOT (Graphviz) лежат в `docs/diagrams/`.
Чтобы сгенерировать PNG, выполните:

```bash
apt-get install -y graphviz
dot -Tpng docs/diagrams/03-vllm-14b-deploy.dot \
  -o docs/diagrams/03-vllm-14b-deploy.png
dot -Tpng docs/diagrams/03-deploy-sequence.dot \
  -o docs/diagrams/03-deploy-sequence.png
```

Готовые PNG (если сгенерированы):

![Архитектура компонентов](docs/diagrams/03-vllm-14b-deploy.png)

![Последовательность развёртывания](docs/diagrams/03-deploy-sequence.png)

Файлы DOT для редактирования:

| Файл | Описание |
|------|----------|
| [`docs/diagrams/03-vllm-14b-deploy.dot`](docs/diagrams/03-vllm-14b-deploy.dot) | Компонентная архитектура: ноды, модели, сервисы |
| [`docs/diagrams/03-deploy-sequence.dot`](docs/diagrams/03-deploy-sequence.dot) | Последовательность развёртывания: подготовка → выбор → деплой → проверка |

---

## Особенности RTX 6000 (Turing TU102)

| Параметр | Значение |
|----------|----------|
| GPU Architecture | Turing (CC 7.5) |
| VRAM | 23GB HBM2 |
| Memory bandwidth | ~460 GB/s |
| bfloat16 support | ❌ Не поддерживается |
| FlashAttention-2 | ❌ Не поддерживается |
| vLLM engine | V0 (V1 несовместим с CC < 8.0) |
| Attention backend | XFormers |
| Рекомендуемый dtype | `half` (float16) |
| Рекомендуемая квантизация | GPTQ 4-bit |

---

## Метрики производительности (ожидаемые)

| Модель | Параметры | GPU | Memory | t/s (BS=1) | t/s (BS=8) |
|--------|-----------|-----|--------|-----------|-----------|
| Coder-14B (работает) | TP=2, 2 GPU | 2× RTX 6000 | ~21GB×2 | ~45 | ~140 |
| 14B-Instruct | TP=1, CPU offload | 1× RTX 6000 | ~20GB | ~15 | ~40 |
| **32B-GPTQ** | **TP=1** | **1× RTX 6000** | **~10GB** | **~30** | **~80** |

---

## Файлы

```
03-vllm-14b-deploy/
├── README.md                                    ← этот файл
├── manifests/
│   ├── vllm-namespace.yaml                      ← namespace aither-inference
│   ├── vllm-sa.yaml                             ← ServiceAccount + RBAC
│   ├── vllm-deployment.yaml                     ← 2 Deployment: 14B + 32B
│   └── vllm-service.yaml                        ← ClusterIP :8000, :8001
└── docs/diagrams/
    ├── 03-vllm-14b-deploy.dot                   ← архитектура компонентов
    └── 03-deploy-sequence.dot                   ← последовательность развёртывания
```
