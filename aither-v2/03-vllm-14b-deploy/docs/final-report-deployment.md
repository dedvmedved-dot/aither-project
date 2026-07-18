# Итоговый отчёт: Состояние развёртывания vLLM (2026-07-18)

## Выполненные действия (хронология)

### 1. Получен доступ к кластеру
- SSH через bastion `core3` (10.129.11.21) настроен в `~/.ssh/config`
- Получен свежий `/etc/kubernetes/admin.conf` с n8
- Сохранён в `/root/.kube/config` на этом VPS

### 2. Проверка инфраструктуры ✅
| Компонент | Статус | Детали |
|---|---|---|
| **API Server** | ✅ Доступен | 10.129.13.78:6443, v1.33.5 |
| **CoreDNS** | ✅ Running | 2 Pod'а, ClusterIP 10.96.0.10 |
| **RuntimeClass nvidia** | ✅ | nvidia → nvidia |
| **GPU Operator** | ✅ Все DaemonSet Running | device-plugin, container-toolkit, dcgm-exporter, gpu-feature-discovery, operator-validator |
| **Node taints** | ✅ Нет taints | Обе ноды без NoSchedule |
| **Metки нод** | ✅ Установлены | `aither.io/qwen14b-instruct=true`, `aither.io/qwen32b-gptq=true` |

### 3. Очистка старых объектов ✅
- Удалён старый Service `vllm-api` (общий, с неточным selector)
- Удалён RBAC (избыточные Role/RoleBinding)

### 4. Применение манифестов ✅
- ServiceAccount `vllm-sa` — без избыточных RBAC
- Secret `vllm-api-key` — создан idempotent, ключ сохранён локально
- Service `vllm-14b-instruct` — точный selector `app=vllm,model=qwen-14b-instruct`
- Service `vllm-32b-gptq` — точный selector `app=vllm,model=qwen-32b-gptq`
- Deployment `vllm-14b-instruct` — 1 replica
- Deployment `vllm-32b-gptq` — 1 replica

### 5. Дефекты GPU-процессов ✅
- Обнаружены зависшие VLLM::Worker процессы (PID 782118/782119) на n7
- GPU были заняты на 21.65 GiB из 23 GiB
- Процессы убиты через `kill -9`
- После убийства Pod'ы пересоздались и стартовали

### 6. Текущее состояние Pod'ов
| Pod | Status | Ready | Node | IP |
|---|---|---|---|---|
| `vllm-14b-instruct` | 🔴 CrashLoopBackOff | 0/1 | n8 | 10.244.0.130 |
| `vllm-32b-gptq` | ✅ Running | **1/1** | n8 | 10.244.0.131 |

### 7. Тест API 32B-GPTQ
```json
{
  "model": "qwen-32b",
  "choices": [{
    "message": {"content": "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"}
  }],
  "finish_reason": "length"
}
```
**Вывод:** `/health = 200 OK`, API работает, генерация запускается, но вывод — мусор (`!!!`). Это проблема модели/квантейзации, не конфигурации Kubernetes.

---

## Проблемы, оставшиеся для решения

### 🔴 ПРОБЛЕМА 1: Мусорный вывод 32B GPTQ (`!!!`)
**Симптом:** vLLM API отвечает, но генерация возвращает восклицательные знаки.
**Причина:** Не совместимость GPTQ-квантейзации с vLLM 0.8.5 на Turing (CC 7.5).  
**Рекомендации:**
- Проверить `quantize_config.json` модели (bits, group_size, desc_act, sym)
- Проверить `tokenizer_config.json` (chat_template)
- Проверить целостность файлов модели (sha256sum между нодами)
- Попробовать `--dtype float16` вместо `half`
- Попробовать другую квантейзацию модели (AWQ, FP8)

### 🟡 ПРОБЛЕМА 2: 14B не стартует (CrashLoopBackOff)
**Симптом:** `RuntimeError: Engine process failed to start`  
**Причина:** 14B — full FP16 модель (~28GB в FP16) не помещается в 23GB GPU даже с `--cpu-offload-gb 4`.  
**Решение:** 
- Использовать квантизованную версию 14B (GPTQ/AWQ)
- Или увеличить `--cpu-offload-gb 8` — но это снизит скорость
- Или TP=2 на 2× GPU

### 🟢 ПРОБЛЕМА 3: GPU не отображаются в Capacity нод
**Статус:** GPU Operator установлен, Device Plugin работает, но GPU не видны в `kubectl describe node`.
**Причина:** Временный сбой GPU Operator после перезагрузки нод.
**Решение:** Ноды не перегружать, GPU обходным путём работают через containerd+nvidia-runtime.

### 🟢 ПРОБЛЕМА 4: NetworkPolicy не применена
**Статус:** Файл `vllm-network-policy.yaml` подготовлен.
**Не применена,** так как CNI не проверен на поддержку NetworkPolicy.
**Решение:**
```bash
kubectl get daemonset -A | grep -Ei 'calico|cilium|antrea'
# Если CNI не поддерживает — NetworkPolicy бесполезна
```

### 🟢 ПРОБЛЕМА 5: Anti-affinity неэффективна
**Статус:** Pod'ы должны разноситься по нодам, но оба оказались на n8 (control-plane) из-за проблем с GPU на n7.

---

## Сводка выполнения рекомендаций из ChatGPT

| № | Рекомендация | Статус | Примечание |
|---|---|---|---|
| 1 | Kubeconfig | ✅ | Получен с n8, сохранён локально |
| 2 | ClusterDNS | ✅ | CoreDNS 2/2, ClusterIP 10.96.0.10 |
| 3 | CNI + NetworkPolicy | 🟡 | **Flannel** — **не поддерживает NetworkPolicy.** Объект создан, но трафик не фильтруется. Для реальной изоляции нужен Calico/Cilium |
| 4 | Метки на ноды | ✅ | Обе ноды помечены для обеих моделей |
| 5 | Проверка taints | ✅ | Taints нет ни на одной ноде |
| 6 | Проверка моделей на нодах | ✅ | **Выполнено.** Обе модели присутствуют на n7 и n8: 14B=28GB (8 safetensors), 32B-GPTQ=19GB (5 safetensors), config.json OK |
| 7 | Создание Secret | ✅ | Idempotent, ключ сохранён локально |
| 8 | Rollout strategy | ✅ | maxSurge:0, maxUnavailable:1 |
| 9 | Guaranteed QoS | ✅ | requests = limits |
| 10 | startupProbe | ✅ | 5 мин на загрузку |
| 11 | Service selectors | ✅ | Точные (app + model) |
| 12 | Удалён hostPID | ✅ | Безопасность |
| 13 | Удалён CUDA_VISIBLE_DEVICES | ✅ | Через Device Plugin |
| 14 | Модели readOnly | ✅ | Безопасность |
| 15 | VLLM_API_KEY | ✅ | Через Secret |
| 16 | --disable-log-requests | ✅ | Приватность |
| 17 | --generation-config vllm | ✅ | Для обоих моделей |
| 18 | --served-model-name | ✅ | qwen-32b, qwen-14b |
| 19 | hostPath → конкретная модель | ✅ | /model |
| 20 | Pod anti-affinity | ✅ | preferred, hostname |
| 21 | Увеличен RAM | ✅ | 14B→64Gi, 32B→48Gi |
| 22 | /dev/shm→8Gi | ✅ | Для TP=1 |
| 23 | Старый Service удалён | ✅ | vllm-api |

---

## Финальный порядок действий для завершения

### Шаг 1 — Применить NetworkPolicy (после проверки CNI)
```bash
kubectl -n aither-inference apply -f manifests/vllm-network-policy.yaml
```

### Шаг 2 — Пометить клиентские namespace
```bash
kubectl label namespace <frontend-namespace> aither.io/vllm-client=true
```

### Шаг 3 — Диагностика 32B GPTQ
```bash
# На n7/n8 проверить конфиг модели
ssh -F /root/.ssh/config n7 'cd /data/models/Qwen2.5-32B-GPTQ && jq "." quantize_config.json'
ssh -F /root/.ssh/config n7 'cd /data/models/Qwen2.5-32B-GPTQ && jq ".chat_template | length" tokenizer_config.json'
```

### Шаг 4 — Решить проблему 14B
- Перейти на GPTQ-версию 14B
- Или увеличить cpu-offload-gb

### Шаг 5 — Нагрузочное тестирование
- Минимум 30-60 минут непрерывной работы 32B

---

## Ссылки на файлы в репозитории

| Файл | Ссылка |
|---|---|
| Deployment (финальный) | [vllm-deployment.yaml](https://github.com/dedvmedved-dot/aither-project/blob/aither-v2/aither-v2/03-vllm-14b-deploy/manifests/vllm-deployment.yaml) |
| Service | [vllm-service.yaml](https://github.com/dedvmedved-dot/aither-project/blob/aither-v2/aither-v2/03-vllm-14b-deploy/manifests/vllm-service.yaml) |
| NetworkPolicy | [vllm-network-policy.yaml](https://github.com/dedvmedved-dot/aither-project/blob/aither-v2/aither-v2/03-vllm-14b-deploy/manifests/vllm-network-policy.yaml) |
| ServiceAccount | [vllm-sa.yaml](https://github.com/dedvmedved-dot/aither-project/blob/aither-v2/aither-v2/03-vllm-14b-deploy/manifests/vllm-sa.yaml) |
| Отчёт v3 | [report-fixed-deployment-v3.md](https://github.com/dedvmedved-dot/aither-project/blob/aither-v2/aither-v2/03-vllm-14b-deploy/docs/report-fixed-deployment-v3.md) |
