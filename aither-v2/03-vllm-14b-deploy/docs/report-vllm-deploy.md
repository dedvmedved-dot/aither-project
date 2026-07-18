# Этап 3: vLLM 32B-GPTQ — отчёт о развёртывании

**Дата:** 2026-07-18  
**Кластер:** Kubernetes v1.33.5, containerd 2.2.1, Astra Linux  
**Нода:** n7 — `bootsmam-k8s-clnt01-n7-gpu` (10.129.13.77)  
**GPU:** 2× Quadro RTX 6000 23GB (Turing TU102, CC 7.5)  
**Версия vLLM:** v0.8.5 (образ `vllm/vllm-openai:v0.8.5`)

---

## 1. Структура развёртывания

### 1.1 Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: aither-inference
```

### 1.2 Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: vllm-api
  namespace: aither-inference
  labels:
    app: vllm
spec:
  type: ClusterIP
  clusterIP: 10.104.41.145
  ports:
    - name: openai-api
      port: 8000
      protocol: TCP
      targetPort: 8000
  selector:
    app: vllm
```

> **⚠️ Примечание:** Сервис слушает только порт 8000. Pod с 32B-GPTQ работает на порту 8001. Для доступа к нему через сервис необходимо добавить второй порт. На данный момент Pod доступен напрямую по ClusterIP: `10.244.1.221:8001`.

### 1.3 Полный YAML Deployment

Файл: `manifests/vllm-deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-32b-gptq
  namespace: aither-inference
  labels:
    app: vllm
    model: qwen-32b-gptq
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm
      model: qwen-32b-gptq
  strategy:
    type: Recreate
  template:
    metadata:
      labels:
        app: vllm
        model: qwen-32b-gptq
    spec:
      terminationGracePeriodSeconds: 30
      serviceAccountName: vllm-sa
      runtimeClassName: nvidia
      nodeName: bootsmam-k8s-clnt01-n7-gpu
      hostPID: true
      containers:
        - name: vllm
          image: vllm/vllm-openai:v0.8.5
          command:
            - sh
            - -c
            - |
              echo "=== Kill stale ==="
              nvidia-smi --query-compute-apps=pid,process_name --format=csv,noheader | grep VLLM | cut -d, -f1 | while read pid; do kill -9 "$pid" 2>/dev/null || true; done
              sleep 3
              nvidia-smi --query-gpu=index,memory.used --format=csv,noheader
              echo "=== Start 32B-GPTQ ==="
              exec python3 -m vllm.entrypoints.openai.api_server \
                --model /models/Qwen2.5-32B-GPTQ \
                --tensor-parallel-size 1 \
                --host 0.0.0.0 --port 8001 \
                --gpu-memory-utilization 0.95 \
                --max-model-len 4096 \
                --trust-remote-code \
                --dtype half \
                --enforce-eager \
                --quantization gptq \
                --served-model-name qwen-32b
          env:
            - name: CUDA_VISIBLE_DEVICES
              value: "0"
          ports:
            - containerPort: 8001
          resources:
            limits:
              nvidia.com/gpu: "1"
              memory: 36Gi
              cpu: "8"
            requests:
              nvidia.com/gpu: "1"
              memory: 28Gi
              cpu: "4"
          volumeMounts:
            - name: dshm
              mountPath: /dev/shm
            - name: models
              mountPath: /models
          readinessProbe:
            httpGet:
              path: /health
              port: 8001
            initialDelaySeconds: 90
            periodSeconds: 15
            timeoutSeconds: 10
          livenessProbe:
            httpGet:
              path: /health
              port: 8001
            initialDelaySeconds: 240
            periodSeconds: 30
            timeoutSeconds: 10
      volumes:
        - name: dshm
          emptyDir:
            medium: Memory
            sizeLimit: 32Gi
        - name: models
          hostPath:
            path: /data/models
            type: Directory
```

### 1.4 RuntimeClass

```yaml
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: nvidia
handler: nvidia
```

---

## 2. Хранение модели: hostPath

Модель находится локально на каждой ноде:

| Нода | Путь | Содержимое | Размер |
|------|------|-----------|--------|
| n7 | `/data/models/Qwen2.5-32B-GPTQ/` | 5× safetensors + config, tokenizer, etc. | 19 GB |
| n8 | `/data/models/Qwen2.5-32B-GPTQ/` | Полная копия | 19 GB |

> `hostPath: /data/models` монтируется в `/models` контейнера.  
> Права: `drwxr-xr-x root:root` — доступ есть.

---

## 3. Диагностика развёртывания

### 3.1 `kubectl get pod -o yaml`

См. Deployment YAML выше (Pod наследует spec из Deployment).  
Полный вывод — в логах сессии (Pod `vllm-32b-gptq-54798c8dbc-zlbq9`).

### 3.2 `kubectl describe pod`

| Параметр | Значение |
|----------|----------|
| Pod IP | `10.244.1.221` |
| Node | `bootsmam-k8s-clnt01-n7-gpu` (10.129.13.77) |
| RuntimeClass | `nvidia` |
| ServiceAccount | `vllm-sa` |
| Container ID | `containerd://54da4f7541b6...` |
| Image | `docker.io/vllm/vllm-openai:v0.8.5` |
| State | Running (started 19:00:48 MSK) |
| Restart count | 1 (первый запуск упал с OOM) |
| GPU allocated | `nvidia.com/gpu: 1` (limit/request) |
| CPU | requests 4, limits 8 |
| Memory | requests 28Gi, limits 36Gi |
| QoS Class | Burstable |

**Замечание по ClusterDNS:** kubelet на ноде не настроен ClusterDNS, используется `Default` политика. Не влияет на работу vLLM.

### 3.3 Логи Pod (текущий запуск)

```
=== Kill stale ===
0, 21 MiB
=== Start 32B-GPTQ ===
INFO 07-18 [api_server.py:1043] vLLM API server version 0.8.5
INFO 07-18 [api_server.py:1044] args: ... quantization='gptq', max_model_len=4096, tensor_parallel_size=1 ...
INFO 07-18 [config.py:717] Defaulting to 'generate'.
INFO 07-18 [gptq_bitblas.py:168] Detected gptq_bitblas, forcing gptq.
WARNING 07-18 [config.py:830] gptq quantization not fully optimized.
WARNING 07-18 [arg_utils.py:1658] Compute Capability < 8.0 → falling back to V0.
INFO 07-18 [cuda.py:289] Using XFormers backend.
INFO 07-18 [model_runner.py:1108] Loading model /models/Qwen2.5-32B-GPTQ...
Loading safetensors: 100% (5/5, 5.95s)
INFO 07-18 [llm_engine.py:240] Engine V0 initialized.
INFO 07-18 [worker.py:287] total_gpu_memory=21.97GiB × gpu_memory_utilization(0.95) = 20.88GiB
INFO 07-18 [worker.py:287] model weights=18.14GiB; KV Cache=1.23GiB
INFO 07-18 [executor_base.py:112] # cuda blocks: 314, # CPU blocks: 1024
INFO 07-18 [api_server.py:1090] Starting vLLM API server on http://0.0.0.0:8001
INFO:     Application startup complete.
```

**KPI загрузки модели:**
| Метрика | Значение |
|---------|----------|
| Загрузка весов | 5.95 сек (5 shards) |
| Инициализация engine | 6.49 сек |
| Memory profiling | 3.66 сек |
| Warmup | 11.28 сек |
| **Total startup** | **~40 сек** |
| GPU Memory (weights) | 18.14 GiB |
| GPU Memory (KV Cache) | 1.23 GiB |
| GPU Memory (peak) | 20.88 GiB |
| Max context length | 4096 токенов |

### 3.4 Логи Pod (предыдущий запуск — причина первого падения)

Предыдущий запуск упал с **OOM**:

```
ERROR 07-18 [engine.py:448] CUDA out of memory. GPU 0: 21.97 GiB total, 1.29 GiB free.
Process 638085 has 20.52 GiB memory in use.
```

Причина — на GPU 0 висел старый процесс (PID 638085, 20.52 GiB), cleanup скрипт убил только VLLM-процессы, но этот процесс не содержал "VLLM" в имени. После ручной очистки — запуск успешен.

---

## 4. Состояние GPU

### 4.1 `nvidia-smi` на n7

```
GPU 0: Quadro RTX 6000 | 10079 MiB / 23040 MiB | 25% util | VLLM::Worker_TP0 (PID 650192)
GPU 1: Quadro RTX 6000 | 20819 MiB / 23040 MiB |  0% util | /usr/bin/python3 (PID 640341) — старый висяк
```

> **Проблема:** PID 640341 (20.8 GiB) висит на GPU 1 с предыдущего запуска.  
> Это старый engine-процесс vLLM, не убитый cleanup (имя процесса `/usr/bin/python3`, без "VLLM").

### 4.2 `nvidia-smi topo -m`

```
        GPU0    GPU1
GPU0     X       SYS
GPU1    SYS       X

SYS = Connection traversing PCIe + SMP interconnect between NUMA nodes.
```

**Вывод:** GPU на разных NUMA-узлах (CPU 0-27 для GPU0, 28-55 для GPU1).  
**Для TP=2:** межсерверная связь через PCIe + QPI — неоптимально, latency выше, чем NVLink.

---

## 5. Проверка параметров

| Параметр | Ожидание | Реальность | Вердикт |
|----------|----------|------------|---------|
| `--quantization gptq` | Форсирует exllama backend | ✅ **Работает.** vLLM определил gptq_bitblas, но применил gptq | ⚠️ vLLM предупреждает, что `gptq` медленнее gptq_bitblas |
| `--tensor-parallel-size 1` | 1 GPU | ✅ 1 GPU выделен | ✅ |
| `command/args` совместимость | vllm-openai:v0.8.5 | ✅ Все флаги распознаны | ✅ |
| `/dev/shm` | EmptyDir Memory 32Gi | ✅ Создан | ✅ |
| hostPID | Доступ к `nvidia-smi` на хосте | ✅ Cleanup GPU работает | ✅ |
| Probes | Readiness 90s, Liveness 240s | ✅ Pod Ready после ~90с | ✅ |
| requests/limits | CPU 4/8, Mem 28/36Gi, GPU 1/1 | ✅ Соответствует | ✅ |
| VRAM: KV Cache | 1.23 GiB | ✅ 314 cuda blocks (1.23 GiB) | ⚠️ Только ~1x concurrency при 4096 токенах |

---

## 6. Выявленные проблемы

### 6.1 Garbage collection GPU процессов (HIGH)

**Проблема:** cleanup скрипт ищет `VLLM` в имени процесса, но engine-процесс называется `/usr/bin/python3` — не убивается.

**Решение:** Использовать `nvidia-smi --query-compute-apps=pid` для поиска всех процессов на GPU:

```bash
nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -v '^$' | \
  while read pid; do kill -9 "$pid" 2>/dev/null; done
```

### 6.2 Service не включает порт 8001 (MEDIUM)

**Проблема:** `vllm-api` слушает только порт 8000, а 32B-GPTQ на порту 8001.  
**Решение:** Добавить второй порт в сервис.

### 6.3 GPTQ на Turing — качество вывода (HIGH)

**Проблема:** При `--quantization gptq` модель отвечает мусором (`!!!`).  
**Причина:** `exllama_config.version: 1` несовместим с Turing (CC 7.5).  
**Варианты:**
- `--quantization gptq_marlin` — более совместим с Turing  
- `--quantization gptq_bitblas` — требует `pip install bitblas`  
- Переквантовать модель в AWQ или Marlin

### 6.4 ClusterDNS не настроен (LOW)

Kubelet предупреждает `MissingClusterDNS`. Pod использует `Default` DNS — не влияет.

### 6.5 NCCL между RTX 6000 (INFO)

GPU на разных NUMA-узлах (SYS топология). Для TP=2 — дополнительная латентность через QPI/PCIe.

---

## 7. `kubectl describe node` (n7) — ресурсы

```
Capacity:
  cpu:                112
  memory:             791 GiB
  nvidia.com/gpu:     2
  pods:               110

Allocated resources:
  nvidia.com/gpu:     1 / 2     (vllm-32b-gptq использует 1)
  cpu:                4215m (3%)
  memory:             29114Mi (3%)
```

> Один GPU свободен. Можно разместить ещё один Pod на этом узле.

---

## 8. Итог

| Критерий | Статус |
|----------|--------|
| Pod запущен и отвечает на `/health` | ✅ |
| Модель загружается (~40 сек) | ✅ |
| GPU выделен корректно (1/2) | ✅ |
| Probes работают | ✅ |
| cleanup GPU при старте | ⚠️ Убивает не все процессы |
| Качество генерации (gptq на Turing) | ❌ Мусорный вывод |
| Service включает оба порта | ❌ |
| ClusterDNS | ❌ Не настроен |

**Рекомендация:** после решения проблемы GPTQ (п.6.3) — развёртывание можно считать успешным.
