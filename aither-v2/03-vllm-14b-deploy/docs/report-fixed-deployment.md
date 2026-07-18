# Отчёт: Исправление конфигурации vLLM Deployment

**Дата:** 2026-07-18  
**Основание:** Анализ рекомендаций ChatGPT (документ `Общий вывод ChatGPT-1.md`)

---

## Выполненные изменения

### 1. Удалён `hostPID: true` и startup-cleanup (kill -9) ⚠️ HIGH

**Проблема:** Контейнер имел доступ к PID namespace узла и убивал все GPU-процессы с "VLLM" в имени при старте. Это могло уничтожить соседние Pod'ы или административные задачи.

**Решение:** 
- Удалён `hostPID: true` из обоих Deployment
- Удалён shell-скрипт с `nvidia-smi ... kill -9`
- Использован прямой `command: [python3, -m, vllm.entrypoints.openai.api_server]` — Python становится PID 1, kubelet отправляет SIGTERM корректно
- `terminationGracePeriodSeconds: 30` → **120** для штатного завершения

**Файл:** `manifests/vllm-deployment.yaml`

---

### 2. Service разделён на два отдельных ⚠️ HIGH

**Проблема:** Один Service `vllm-api` с селектором `app: vllm` матчил оба Pod'а (14B и 32B). Порт 8000 направлялся в том числе к 32B Pod, где слушался порт 8001.

**Решение:** Созданы два отдельных Service с точным селектором:

| Service | Selector | Порт |
|---|---|---|
| `vllm-14b-instruct` | `app: vllm, model: qwen-14b-instruct` | 8000 → http |
| `vllm-32b-gptq` | `app: vllm, model: qwen-32b-gptq` | 8000 → http |

Удалён фиксированный `clusterIP: 10.104.41.145`.

**Файл:** `manifests/vllm-service.yaml`

---

### 3. Оставлен `--quantization gptq` (Marlin/BitBLAS исключены) ⚠️ HIGH

**Проблема:** В предыдущем отчёте рекомендовался `gptq_marlin`, НО он требует Compute Capability ≥ 8.0. RTX 6000 имеет CC 7.5 (Turing).

**Решение:**
- `--quantization gptq` — оставлен (корректен для vLLM 0.8.5 + Turing)
- `gptq_marlin` — НЕ используется (требует SM80+)
- `gptq_bitblas` — НЕ используется (официально отключён для <SM80 в vLLM)
- Добавлен `--generation-config vllm` — отключает загрузку `generation_config.json` из модели
- Добавлен `--served-model-name qwen-32b` — явное имя модели для API
- `--dtype half` — оставлен (корректен для GPTQ)
- Удалён `--trust-remote-code`

---

### 4. Probes переделаны на startupProbe ⚠️ MEDIUM

**Проблема:** `readinessProbe.initialDelaySeconds: 300` (14B) / `120` (32B) искусственно задерживал готовность на 50+ секунд после загрузки модели.

**Решение:**

```yaml
startupProbe:
  httpGet:
    path: /health
    port: http
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 60    # до 5 минут на загрузку
readinessProbe:
  httpGet:
    path: /health
    port: http
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3
livenessProbe:
  httpGet:
    path: /health
    port: http
  periodSeconds: 30
  timeoutSeconds: 5
  failureThreshold: 3
```

Kubernetes ждёт успеха startupProbe, прежде чем запускать readiness/liveness.

---

### 5. Ресурсы переведены в Guaranteed QoS ⚠️ MEDIUM

**Проблема:** CPU и memory requests отличались от limits → QoS `Burstable`.

**Решение:** Requests = Limits для обоих Deployment:

```yaml
resources:
  requests:
    cpu: "8"
    memory: 36Gi
    nvidia.com/gpu: "1"
  limits:
    cpu: "8"
    memory: 36Gi
    nvidia.com/gpu: "1"
```

---

### 6. `nodeName` заменён на `nodeSelector` ⚠️ MEDIUM

**Проблема:** `nodeName` обходит scheduler, Pod не может быть перезапущен на другой ноде.

**Решение:**

```yaml
nodeSelector:
  aither.io/qwen14b-instruct: "true"   # для 14B
  aither.io/qwen32b-gptq: "true"       # для 32B
```

**Необходимо применить на нодах кластера:**

```bash
kubectl label node bootsmam-k8s-clnt01-n7-gpu aither.io/qwen14b-instruct=true
kubectl label node bootsmam-k8s-clnt01-n7-gpu aither.io/qwen32b-gptq=true
kubectl label node bootsmam-k8s-srv01-n8-gpu aither.io/qwen14b-instruct=true
kubectl label node bootsmam-k8s-srv01-n8-gpu aither.io/qwen32b-gptq=true
```

---

### 7. Безопасность ⚠️ LOW

- `automountServiceAccountToken: false` — vLLM не обращается к Kubernetes API
- ServiceAccount `vllm-sa` — оставлен без избыточных RBAC-ролей
- Модели монтируются `readOnly: true`
- Удалён `--trust-remote-code`

---

### 8. Порт 32B изменён с 8001 → 8000 ⚠️ MEDIUM

**Проблема:** 32B Pod слушал порт 8001, что требовало отдельного Service-порта.

**Решение:** Оба Deployment теперь слушают порт 8000 (`--port 8000`). Это упрощает Service и прокси.

---

## Осталось сделать на кластере (требуется SSH на master-ноду)

### Шаг 1: Применить метки нод
```bash
kubectl label node bootsmam-k8s-clnt01-n7-gpu aither.io/qwen14b-instruct=true
kubectl label node bootsmam-k8s-clnt01-n7-gpu aither.io/qwen32b-gptq=true
kubectl label node bootsmam-k8s-srv01-n8-gpu aither.io/qwen14b-instruct=true
kubectl label node bootsmam-k8s-srv01-n8-gpu aither.io/qwen32b-gptq=true
```

### Шаг 2: Применить обновлённые манифесты
```bash
kubectl apply -f manifests/vllm-deployment.yaml
kubectl apply -f manifests/vllm-service.yaml
kubectl apply -f manifests/vllm-sa.yaml
```

### Шаг 3: Очистить старый PID (если ещё висит)
```bash
ssh bootsmam-k8s-clnt01-n7-gpu
PID=640341
ps -fp "$PID" 2>/dev/null && \
  sudo kill -TERM "$PID" 2>/dev/null; \
  sleep 10; \
  sudo kill -KILL "$PID" 2>/dev/null || true
nvidia-smi
```

### Шаг 4: Проверить модель — сравнить хэши
```bash
ssh bootsmam-k8s-clnt01-n7-gpu
find /data/models/Qwen2.5-32B-GPTQ -type f -print0 | sort -z | xargs -0 sha256sum > /tmp/qwen32b.sha256

ssh bootsmam-k8s-srv01-n8-gpu
find /data/models/Qwen2.5-32B-GPTQ -type f -print0 | sort -z | xargs -0 sha256sum > /tmp/qwen32b.sha256

# Сравнить
diff <(ssh n7 'cat /tmp/qwen32b.sha256') <(ssh n8 'cat /tmp/qwen32b.sha256')
```

### Шаг 5: Проверить конфиг модели
```bash
cd /data/models/Qwen2.5-32B-GPTQ
jq '{model_type, architectures, torch_dtype, vocab_size, eos_token_id, bos_token_id}' config.json
jq '.bits, .group_size, .desc_act, .sym, .quant_method' quantize_config.json
jq '{tokenizer_class, chat_template: (.chat_template | length > 0)}' tokenizer_config.json
```

### Шаг 6: Проверить ClusterDNS
```bash
kubectl -n kube-system get svc kube-dns -o wide
# Ожидается ClusterIP, например 10.96.0.10
sudo grep -R -nE 'clusterDNS|clusterDomain' /var/lib/kubelet/config.yaml /etc/kubernetes 2>/dev/null
```

### Шаг 7: Детерминированный тест генерации
```bash
# Через Service:
curl -s http://vllm-32b-gptq.aither-inference.svc.cluster.local:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen-32b",
    "messages": [{"role": "user", "content": "Ответь одним словом: столица Франции?"}],
    "temperature": 0,
    "max_tokens": 32
  }' | python3 -m json.tool
```

**Ожидаемый ответ:** `{"choices":[{"message":{"content":"Париж"}}]}`

Если ответ всё ещё мусорный — вероятные причины:
1. Повреждённые веса модели — проверить хэши
2. Несовместимые файлы tokenizer/config — проверить шаг 5
3. Base-модель вместо Instruct — проверить `chat_template` в `tokenizer_config.json`

---

## Сводка изменений манифестов

| Файл | Статус | Изменения |
|---|---|---|
| `vllm-deployment.yaml` | ✅ Обновлён | `hostPID` удалён, startup‑cleanup удалён, probes → startupProbe, resources → Guaranteed, `nodeName` → `nodeSelector`, порт 32B → 8000, `automountServiceAccountToken: false`, `readOnly: true`, `--trust-remote-code` удалён, `--generation-config vllm`, `--served-model-name`, `terminationGracePeriodSeconds: 120` |
| `vllm-service.yaml` | ✅ Обновлён | Разделён на два отдельных Service с точным selector по модели |
| `vllm-sa.yaml` | ✅ Обновлён | RBAC-роли удалены (не нужны при `automountServiceAccountToken: false`) |

---

## Приоритет оставшихся действий

1. 🔴 **Нанести метки на ноды** — без этого `nodeSelector` не найдёт ноду
2. 🔴 **Применить манифесты** — обновить Deployment в кластере
3. 🟡 **Очистить старый PID** — если ещё висит на GPU 1
4. 🟡 **Проверить целостность модели** — хэши, tokenizer, quantize config
5. 🟢 **Тест генерации** — только после проверки модели
6. 🟢 **ClusterDNS** — диагностика, не блокирует запуск
