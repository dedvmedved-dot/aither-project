# Отчёт: Итоговые исправления конфигурации vLLM Deployment (v2)

**Дата:** 2026-07-18  
**Основание:** Анализ рекомендаций ChatGPT (документы `Общий вывод ChatGPT-1.md` и `Общий вывод ChatGPT-2.md`)

---

## Выполненные изменения (итерация 2)

### 1. Rollout strategy — явно задана ⚠️ MEDIUM

**Проблема:** Стандартный RollingUpdate (25% maxSurge, 25% maxUnavailable) для 1 Pod может вызвать зависание rollout — новый Pod не может получить GPU, пока старый жив.

**Решение — для обоих Deployment:**

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 0
      maxUnavailable: 1
```

→ Старый Pod завершается → GPU освобождается → запускается новый.

---

### 2. Удалён `CUDA_VISIBLE_DEVICES=0` ✅

**Проблема:** Избыточно (NVIDIA Device Plugin уже назначает GPU). Мешает TP=2 и диагностике.

**Решение:** Переменная удалена из обоих Deployment. NVIDIA Container Runtime сам передаёт выделенную GPU как устройство с индексом 0.

---

### 3. Увеличен memory limit + уменьшен /dev/shm ⚠️ MEDIUM

**Проблема:** 36Gi для 14B с `--cpu-offload-gb 4 --swap-space 8` и tmpfs `/dev/shm` размером 32Gi слишком жёстко — риск OOM.

**Решение:**

| Параметр | 14B | 32B |
|---|---|---|
| Memory requests/limits | **64Gi** | **48Gi** |
| `/dev/shm` sizeLimit | **8Gi** (было 32Gi) | **8Gi** (было 32Gi) |

На ноде 791 GiB RAM — запас оправдан. После тестов можно уменьшить по `kubectl top pod`.

---

### 4. Добавлен `--served-model-name qwen-14b` ✅

**Проблема:** Без `--served-model-name` vLLM использует путь `/models/Qwen2.5-14B-Instruct` как имя модели.

**Решение:** Добавлено:
```yaml
- --served-model-name
- qwen-14b
```

Теперь оба Deployment имеют явные имена моделей для API.

---

### 5. Pod anti-affinity + проверка taints на n8 ✅

**Проблема:** Оба Pod могут оказаться на одной ноде, если там свободны 2 GPU.

**Решение:** Добавлена мягкая anti-affinity:

```yaml
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
          podAffinityTerm:
            labelSelector:
              matchLabels:
                app: vllm
            topologyKey: kubernetes.io/hostname
```

Scheduler предпочтёт разнести Pod'ы по разным нодам, но при недоступности одной — запустит оба на оставшейся.

> **Для проверки taints на n8 (на master-ноде):**
> ```bash
> kubectl get node bootsmam-k8s-srv01-n8-gpu -o jsonpath='{.spec.taints}{"\n"}'
> ```

---

### 6. `hostPath` сужен до конкретной модели ⚠️ MEDIUM

**Проблема:** Оба Pod монтировали весь `/data/models` и получали доступ к чужим файлам.

**Решение:** Каждый Pod монтирует только свою модель:

| Deployment | hostPath | mountPath |
|---|---|---|
| vllm-14b-instruct | `/data/models/Qwen2.5-14B-Instruct` | `/model` |
| vllm-32b-gptq | `/data/models/Qwen2.5-32B-GPTQ` | `/model` |

Аргумент `--model /model` — для обоих.

---

### 7. Добавлен VLLM_API_KEY через Secret 🔐

**Проблема:** API не защищён — любой Pod в кластере может отправлять запросы.

**Решение:**
- Secret `vllm-api-key` создаётся отдельно (не в Git):
  ```bash
  kubectl -n aither-inference create secret generic vllm-api-key \
    --from-literal=VLLM_API_KEY="$(openssl rand -hex 32)"
  ```
- В обоих контейнерах:
  ```yaml
  env:
    - name: VLLM_API_KEY
      valueFrom:
        secretKeyRef:
          name: vllm-api-key
          key: VLLM_API_KEY
  ```
- `/health` остаётся доступным без ключа (для probes)

---

### 8. Добавлены `--disable-log-requests --disable-fastapi-docs` ✅

**Проблема:** vLLM может логировать все запросы; FastAPI docs (/docs, /redoc, /openapi.json) доступны.

**Решение:** Добавлены в args обоих Deployment.

---

### 9. Добавлена NetworkPolicy 🔐

**Проблема:** Service типа ClusterIP доступен всем Pod'ам кластера.

**Решение — новый манифест `vllm-network-policy.yaml`:**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: vllm-ingress
  namespace: aither-inference
spec:
  podSelector:
    matchLabels:
      app: vllm
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              aither.io/vllm-client: "true"
      ports:
        - protocol: TCP
          port: 8000
```

**На master-ноде:** пометить namespace клиента:
```bash
kubectl label namespace <frontend-namespace> aither.io/vllm-client=true
```

---

## Сводка изменений манифестов

| Файл | Статус | Изменения в этой итерации |
|---|---|---|
| `vllm-deployment.yaml` | ✅ Обновлён | strategy, CUDA_VISIBLE_DEVICES удалён, RAM: 14B→64Gi/32B→48Gi, /dev/shm→8Gi, served-model-name для 14B, podAntiAffinity, hostPath→конкретная модель, VLLM_API_KEY, --disable-log-requests/docs |
| `vllm-service.yaml` | ✅ Без изменений | Два отдельных Service — уже корректно |
| `vllm-sa.yaml` | ✅ Без изменений | Уже очищен от RBAC |
| `vllm-network-policy.yaml` | **🆕 Новый** | Ограничение входящего трафика по namespace-метке |
| `vllm-namespace.yaml` | ✅ Без изменений | Namespace как есть |

---

## Применение на кластере (порядок)

### Шаг 0: Аудит старого мусора
```bash
# Проверить старые объекты
kubectl -n aither-inference get svc
kubectl -n aither-inference get role,rolebinding
kubectl get clusterrole,clusterrolebinding | grep -i vllm

# Удалить старый Service (только после переключения клиентов)
kubectl -n aither-inference delete service vllm-api
```

### Шаг 1: Namespace
```bash
kubectl create namespace aither-inference --dry-run=client -o yaml | kubectl apply -f -
```

### Шаг 2: Secret с API-ключом (не в Git!)
```bash
kubectl -n aither-inference create secret generic vllm-api-key \
  --from-literal=VLLM_API_KEY="$(openssl rand -hex 32)"
```

### Шаг 3: ServiceAccount и метки
```bash
kubectl apply -f manifests/vllm-sa.yaml

# Метки — только после проверки наличия моделей на нодах
kubectl label node bootsmam-k8s-clnt01-n7-gpu \
  aither.io/qwen14b-instruct=true aither.io/qwen32b-gptq=true --overwrite
kubectl label node bootsmam-k8s-srv01-n8-gpu \
  aither.io/qwen14b-instruct=true aither.io/qwen32b-gptq=true --overwrite
```

### Шаг 4: Service + NetworkPolicy
```bash
kubectl apply -f manifests/vllm-service.yaml
kubectl apply -f manifests/vllm-network-policy.yaml
```

### Шаг 5: Deployment
```bash
# Dry-run для проверки
kubectl apply --dry-run=server -f manifests/vllm-deployment.yaml
kubectl diff -f manifests/vllm-deployment.yaml

# Apply
kubectl apply -f manifests/vllm-deployment.yaml
```

### Шаг 6: Контроль запуска
```bash
kubectl -n aither-inference rollout status deployment/vllm-14b-instruct --timeout=10m
kubectl -n aither-inference rollout status deployment/vllm-32b-gptq --timeout=10m

kubectl -n aither-inference get pod -o wide
kubectl -n aither-inference get svc,endpointslice
```

### Шаг 7: Метка для NetworkPolicy (на namespace клиента)
```bash
kubectl label namespace <frontend-namespace> aither.io/vllm-client=true
```

### Шаг 8: Тест через port-forward
```bash
# Терминал 1: port-forward
kubectl -n aither-inference port-forward service/vllm-32b-gptq 8001:8000

# Терминал 2: тест
VLLM_API_KEY=$(kubectl -n aither-inference get secret vllm-api-key -o jsonpath='{.data.VLLM_API_KEY}' | base64 -d)
curl -s http://127.0.0.1:8001/v1/chat/completions \
  -H "Authorization: Bearer ${VLLM_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-32b",
    "messages": [{"role": "user", "content": "Ответь одним словом: столица Франции?"}],
    "temperature": 0,
    "max_tokens": 32
  }' | jq -r '.choices[0].message.content'
```

**Ожидаемый вывод:** `Париж`

---

## Итоговый статус

| Категория | Статус |
|---|---|
| **Безопасность** | ✅ hostPID убран, automountServiceAccountToken: false, модели readOnly, VLLM_API_KEY, NetworkPolicy, --trust-remote-code удалён |
| **Сетевое взаимодействие** | ✅ Два отдельных Service с точным selector, NetworkPolicy, --disable-log-requests |
| **Ресурсы** | ✅ Guaranteed QoS, 64Gi/48Gi RAM, /dev/shm 8Gi, CPU 8 |
| **Probes** | ✅ startupProbe (5 мин), readiness (3×5s), liveness (3×30s) |
| **Scheduling** | ✅ nodeSelector (метки), podAntiAffinity, rollout strategy |
| **Квантейзация** | ✅ --quantization gptq (не Marlin/BitBLAS), --generation-config vllm |
| **Модели** | ✅ hostPath → конкретная модель, served-model-name, /model |
| **Старый мусор** | ⚠️ Требуется `kubectl delete service vllm-api` на кластере + очистка RBAC |
