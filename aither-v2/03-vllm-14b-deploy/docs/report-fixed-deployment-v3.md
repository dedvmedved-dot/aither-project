# Отчёт: Итоговые исправления конфигурации vLLM Deployment (v3)

**Дата:** 2026-07-18  
**Основание:** Анализ рекомендаций ChatGPT (документы «Общий вывод ChatGPT-1.md», «Общий вывод ChatGPT-2.md», «Общий вывод ChatGPT-3.md»)

---

## Выполненные изменения (итерация 3)

### 1. 14B: добавлен `--generation-config vllm` ✅

**Проблема:** 14B не имел `--generation-config vllm`, хотя 32B уже был настроен. Разное поведение серверов.

**Решение:** Добавлен `--generation-config vllm` в args 14B-контейнера — единообразное поведение обоих inference-серверов, отключение server-wide sampling defaults из `generation_config.json` модели.

---

### 2. 14B: `--max-num-seqs 4` → `1` (консервативный старт) ⚠️ MEDIUM

**Проблема:** 14B на одной 23GB GPU может не уместиться с `--max-num-seqs 4` даже с offload, если это полная FP16 модель (требует ~28GB + KV cache).

**Решение:** 
- `--max-num-seqs` снижен с `4` до `1`
- После успешного старта повышать: `1 → 2 → 4`
- Если будет OOM: увеличить `--cpu-offload-gb` до 6-8

---

### 3. Исправлен порядок применения NetworkPolicy 🛡️

**Проблема:** NetworkPolicy не должна применяться до запуска Pod'ов — она может блокировать kubelet probes.

**Правильный порядок:**
1. Сначала пометить namespace клиента меткой
2. Применить ServiceAccount, Service, Deployment
3. Дождаться rollout и готовности Pod'ов
4. **Только после этого** применить NetworkPolicy

---

### 4. Idempotent создание Secret с сохранением ключа 🔐

**Проблема:** Команда `kubectl create secret` завершается ошибкой `AlreadyExists` при повторном запуске.

**Решение — idempotent команда с локальным сохранением:**

```bash
if ! kubectl -n aither-inference get secret vllm-api-key >/dev/null 2>&1; then
  VLLM_API_KEY="$(openssl rand -hex 32)"
  kubectl -n aither-inference create secret generic vllm-api-key \
    --from-literal=VLLM_API_KEY="${VLLM_API_KEY}"
  install -m 0600 /dev/null /root/vllm-api-key
  printf '%s\n' "${VLLM_API_KEY}" > /root/vllm-api-key
  unset VLLM_API_KEY
  echo "Secret created, key saved to /root/vllm-api-key"
else
  echo "Secret vllm-api-key already exists, key unchanged"
fi
```

---

## Исправленный итоговый порядок применения на master-ноде

### Этап 0: Получить доступ к API

```bash
# На master-ноде (не копировать admin.conf в чат!)
export KUBECONFIG=/etc/kubernetes/admin.conf

# Проверить сертификаты
sudo kubeadm certs check-expiration
kubectl get --raw='/readyz?verbose'
kubectl get nodes -o wide
```

### Этап 1: Проверить инфраструктуру

```bash
# Проверить CoreDNS
kubectl -n kube-system get svc kube-dns -o wide
kubectl -n kube-system get pods -l k8s-app=kube-dns -o wide

# Проверить CNI (должен быть calico/cilium/antrea — не Flannel!)
kubectl get daemonset -A | grep -Ei 'calico|cilium|antrea|weave|canal'

# Проверить RuntimeClass
kubectl get runtimeclass nvidia

# Проверить taints на n8
kubectl get node bootsmam-k8s-srv01-n8-gpu -o jsonpath='{.spec.taints}{"\n"}'
```

### Этап 2: Проверить модели на нодах

**На каждой ноде по SSH:**

```bash
# Проверить наличие моделей
for MODEL in /data/models/Qwen2.5-14B-Instruct /data/models/Qwen2.5-32B-GPTQ; do
  echo "=== ${MODEL} ==="
  sudo test -r "${MODEL}/config.json" && echo "config.json: OK" || echo "config.json: MISSING"
  sudo find "${MODEL}" -maxdepth 1 -type f -name '*.safetensors' -printf '%f %s\n' 2>/dev/null
  sudo du -sh "${MODEL}" 2>/dev/null
done

# Проверить GPU
nvidia-smi

# Проверить отсутствие потерянных процессов
nvidia-smi --query-compute-apps=pid,gpu_uuid,process_name,used_gpu_memory --format=csv
```

**Сравнить хэши модели 32B между нодами:**
```bash
# На n7
cd /data/models/Qwen2.5-32B-GPTQ
find . -type f -print0 | sort -z | xargs -0 sha256sum > /tmp/qwen32b.sha256

# На n8 — то же самое, затем сравнить:
diff <(ssh n7 'cat /tmp/qwen32b.sha256') <(cat /tmp/qwen32b.sha256)
```

### Этап 3: Нанести метки на ноды (только где модель есть)

```bash
# n7
kubectl label node bootsmam-k8s-clnt01-n7-gpu \
  aither.io/qwen14b-instruct=true \
  aither.io/qwen32b-gptq=true \
  --overwrite

# n8 — только если модель есть и нет taint control-plane
kubectl label node bootsmam-k8s-srv01-n8-gpu \
  aither.io/qwen14b-instruct=true \
  aither.io/qwen32b-gptq=true \
  --overwrite

# Если taint control-plane есть — НЕ метить n8
kubectl label node bootsmam-k8s-srv01-n8-gpu \
  aither.io/qwen14b-instruct- \
  aither.io/qwen32b-gptq- \
  2>/dev/null || true
```

### Этап 4: Подготовить namespace и клиента

```bash
# Namespace
kubectl create namespace aither-inference --dry-run=client -o yaml | kubectl apply -f -

# Метка на namespace клиента (до NetworkPolicy!)
kubectl label namespace <frontend-namespace> aither.io/vllm-client=true --overwrite

# Если Prometheus собирает метрики — пометить и его namespace
```

### Этап 5: Серверная валидация

```bash
cd /path/to/manifests

kubectl apply --dry-run=server -f vllm-sa.yaml
kubectl apply --dry-run=server -f vllm-service.yaml
kubectl apply --dry-run=server -f vllm-network-policy.yaml
kubectl apply --dry-run=server -f vllm-deployment.yaml

kubectl diff -f vllm-sa.yaml
kubectl diff -f vllm-service.yaml
kubectl diff -f vllm-deployment.yaml
kubectl diff -f vllm-network-policy.yaml
```

### Этап 6: Применить (NetworkPolicy — последней!)

```bash
# 1. ServiceAccount
kubectl apply -f vllm-sa.yaml

# 2. Secret (idempotent)
if ! kubectl -n aither-inference get secret vllm-api-key >/dev/null 2>&1; then
  VLLM_API_KEY="$(openssl rand -hex 32)"
  kubectl -n aither-inference create secret generic vllm-api-key \
    --from-literal=VLLM_API_KEY="${VLLM_API_KEY}"
  install -m 0600 /dev/null /root/vllm-api-key
  printf '%s\n' "${VLLM_API_KEY}" > /root/vllm-api-key
  unset VLLM_API_KEY
  echo "Secret created, key saved to /root/vllm-api-key"
else
  echo "Secret vllm-api-key already exists, key unchanged"
fi

# 3. Service
kubectl apply -f vllm-service.yaml

# 4. Deployment
kubectl apply -f vllm-deployment.yaml

# 5. Дождаться rollout
kubectl -n aither-inference rollout status deployment/vllm-14b-instruct --timeout=10m
kubectl -n aither-inference rollout status deployment/vllm-32b-gptq --timeout=10m

# 6. ТОЛЬКО ПОСЛЕ готовности Pod'ов — NetworkPolicy!
kubectl apply -f vllm-network-policy.yaml
```

### Этап 7: Проверить

```bash
# Pod'ы и Service
kubectl -n aither-inference get pod -o wide
kubectl -n aither-inference get svc
kubectl -n aither-inference get endpointslice -o wide

# Если старый Service vllm-api остался — удалить
kubectl -n aither-inference delete service vllm-api 2>/dev/null || true
```

### Этап 8: Тест через port-forward

```bash
# Терминал 1
kubectl -n aither-inference port-forward service/vllm-32b-gptq 8001:8000

# Терминал 2
VLLM_API_KEY="$(kubectl -n aither-inference get secret vllm-api-key -o jsonpath='{.data.VLLM_API_KEY}' | base64 -d)"

curl --fail-with-body -sS http://127.0.0.1:8001/v1/chat/completions \
  -H "Authorization: Bearer ${VLLM_API_KEY}" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen-32b",
    "messages": [{"role": "user", "content": "Ответь одним словом: столица Франции?"}],
    "temperature": 0,
    "max_tokens": 32
  }' | jq .
```

### Этап 9: Smoke-тесты качества

```bash
MODELS="qwen-32b qwen-14b"
TESTS='("Столица Франции?", "Париж")
("2 + 2", "4")
("Продолжи последовательность: 1, 2, 3", "4")
("Назови столицу России", "Москва")'

for model in $MODELS; do
  echo "=== Testing $model ==="
  curl -s http://127.0.0.1:8001/v1/chat/completions \
    -H "Authorization: Bearer ${VLLM_API_KEY}" \
    -H 'Content-Type: application/json' \
    -d "{
      \"model\": \"$model\",
      \"messages\": [{\"role\": \"user\", \"content\": \"Ответь одним словом: столица Франции?\"}],
      \"temperature\": 0,
      \"max_tokens\": 32
    }" | jq -r '.choices[0].message.content'
done
```

### Этап 10: Проверка NetworkPolicy

```bash
# Из разрешённого namespace — должен работать
kubectl -n <CLIENT_NAMESPACE> exec <CLIENT_POD> -- \
  curl -s http://vllm-32b-gptq.aither-inference.svc.cluster.local:8000/health

# Из непомеченного namespace — должен блокироваться
kubectl -n default exec <ANY_POD> -- \
  curl -s --connect-timeout 5 http://vllm-32b-gptq.aither-inference.svc.cluster.local:8000/health
```

---

## Полная сводка изменений за 3 итерации

| № | Изменение | Итерация | Статус |
|---|---|---|---|
| 1 | `hostPID: true` удалён + startup-cleanup (kill -9) | v1 | ✅ |
| 2 | `terminationGracePeriodSeconds: 120` | v1 | ✅ |
| 3 | Service разделён на два с точным selector | v1 | ✅ |
| 4 | `--quantization gptq` (не Marlin/BitBLAS — CC 7.5 < SM80) | v1 | ✅ |
| 5 | `--generation-config vllm` для 32B | v1 | ✅ |
| 6 | Probes → startupProbe (failureThreshold: 60 × 5s) | v1 | ✅ |
| 7 | Resources → Guaranteed QoS (requests=limits) | v1 | ✅ |
| 8 | `nodeName` → `nodeSelector` с метками | v1 | ✅ |
| 9 | `automountServiceAccountToken: false` | v1 | ✅ |
| 10 | Модели `readOnly: true` | v1 | ✅ |
| 11 | `--trust-remote-code` удалён | v1 | ✅ |
| 12 | 32B порт 8001 → 8000 | v1 | ✅ |
| 13 | Rollout strategy: `maxSurge:0, maxUnavailable:1` | v2 | ✅ |
| 14 | `CUDA_VISIBLE_DEVICES=0` удалён | v2 | ✅ |
| 15 | RAM: 14B→64Gi, 32B→48Gi; `/dev/shm`→8Gi | v2 | ✅ |
| 16 | `--served-model-name qwen-14b` для 14B | v2 | ✅ |
| 17 | Pod anti-affinity (preferred, hostname) | v2 | ✅ |
| 18 | `hostPath` сужен до `/data/models/Qwen2.5-*/` | v2 | ✅ |
| 19 | `VLLM_API_KEY` через Secret | v2 | ✅ |
| 20 | `--disable-log-requests --disable-fastapi-docs` | v2 | ✅ |
| 21 | NetworkPolicy `vllm-ingress` | v2 | ✅ |
| 22 | 14B: `--generation-config vllm` | v3 | ✅ |
| 23 | 14B: `--max-num-seqs 4` → `1` (консервативно) | v3 | ✅ |
| 24 | Idempotent Secret + сохранение ключа локально | v3 | ✅ |
| 25 | Порядок apply: NetworkPolicy последней (после rollout) | v3 | ✅ |
| 26 | ClusterDNS диагностика, проверка CNI, taints n8 | v3 | ✅ |

---

## Что остаётся блокером

**1. Доступ к API кластера** — нужен рабочий kubeconfig. Содержимое `admin.conf` **не передавать в чат** — там приватный ключ с правами cluster-admin. Способ:

- **Вариант А (рекомендуемый):** Выполнять команды прямо на master-ноде под `export KUBECONFIG=/etc/kubernetes/admin.conf`
- **Вариант Б:** Скопировать `admin.conf` через `scp` в `/root/.kube/config` на этот сервер

**2. Качество 32B GPTQ** — ранее был мусорный вывод. `/health = 200` не гарантирует корректный инференс. Нужны smoke-тесты.

**3. Нагрузочное тестирование** — минимум 30-60 минут непрерывной работы.

---

## Ссылки на запушенные файлы

| Файл | Описание |
|---|---|
| [vllm-deployment.yaml](https://github.com/dedvmedved-dot/aither-project/blob/aither-v2/aither-v2/03-vllm-14b-deploy/manifests/vllm-deployment.yaml) | Deployment (14B + 32B), финальная версия |
| [vllm-service.yaml](https://github.com/dedvmedved-dot/aither-project/blob/aither-v2/aither-v2/03-vllm-14b-deploy/manifests/vllm-service.yaml) | Два отдельных Service с точным selector |
| [vllm-network-policy.yaml](https://github.com/dedvmedved-dot/aither-project/blob/aither-v2/aither-v2/03-vllm-14b-deploy/manifests/vllm-network-policy.yaml) | NetworkPolicy (ingress, namespaceSelector) |
| [vllm-sa.yaml](https://github.com/dedvmedved-dot/aither-project/blob/aither-v2/aither-v2/03-vllm-14b-deploy/manifests/vllm-sa.yaml) | ServiceAccount (без избыточных RBAC) |
| [vllm-namespace.yaml](https://github.com/dedvmedved-dot/aither-project/blob/aither-v2/aither-v2/03-vllm-14b-deploy/manifests/vllm-namespace.yaml) | Namespace aither-inference |
| [Отчёт v3](https://github.com/dedvmedved-dot/aither-project/blob/aither-v2/aither-v2/03-vllm-14b-deploy/docs/report-fixed-deployment-v3.md) | Полный отчёт с порядком применения |
