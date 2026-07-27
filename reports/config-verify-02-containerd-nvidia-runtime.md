# Отчёт: containerd + nvidia-runtime — верификация задачи #2 ROADMAP

**Задача:** #2 — containerd + nvidia-runtime
**Дата проверки:** 27.07.2026 17:10 МСК
**Метод:** Live-команды ssh, containerd config, nvidia-smi, kubectl
**Результат:** ✅ РАБОТАЕТ

---

## 1. containerd

| Параметр | N8 (control-plane) | N7 (worker) |
|---|---|---|
| **Версия** | 2.2.1.astra0 | 2.2.1.astra0 |
| **Config** | `/etc/containerd/config.toml` (v3) | `/etc/containerd/config.toml` (v3) |
| **Config imports** | `/etc/containerd/conf.d/*.toml` | `/etc/containerd/conf.d/*.toml` |
| **Default runtime** | `runc` | `runc` |
| **SystemdCgroup** | true | true |
| **CDI enabled** | true | true |
| **CDI dirs** | `/etc/cdi`, `/var/run/cdi` | `/etc/cdi`, `/var/run/cdi` |
| **Registry mirror** | `dockerhub.timeweb.cloud` | локальный registry |

---

## 2. nvidia-runtime — конфигурация

### N8: `/etc/containerd/conf.d/`

| Файл | Содержит |
|---|---|
| `99-nvidia.toml` | Полная конфигурация GPU Operator: 3 runtime + CDI |
| `nvidia.toml` | Дополнительный (ручной) конфиг nvidia runtime |

### N7: `/etc/containerd/conf.d/`

| Файл | Содержит |
|---|---|
| `99-nvidia.toml` | Полная конфигурация GPU Operator: 3 runtime + CDI |

### Зарегистрированные NVIDIA-рантаймы (оба узла)

| Runtime | BinaryName |
|---|---|
| `nvidia` | `/usr/local/nvidia/toolkit/nvidia-container-runtime` |
| `nvidia-cdi` | `/usr/local/nvidia/toolkit/nvidia-container-runtime.cdi` |
| `nvidia-legacy` | `/usr/local/nvidia/toolkit/nvidia-container-runtime.legacy` |

Все три используют `runtime_type = io.containerd.runc.v2` + `SystemdCgroup = true`.

---

## 3. K8s RuntimeClass

| Имя | Handler | Возраст | Создан |
|---|---|---|---|
| `nvidia` | `nvidia` | 13 дней | GPU Operator (ClusterPolicy) |

```yaml
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: nvidia
  labels:
    app.kubernetes.io/component: gpu-operator
handler: nvidia
```

---

## 4. Использование nvidia-runtime подами

| Под | Namespace | RuntimeClass | Узел | GPU |
|---|---|---|---|---|
| `vllm-14b-instruct` | aither-inference | **nvidia** | N8 | 2× RTX 6000 |
| `vllm-32b-gptq` | aither-inference | **nvidia** | N7 | 1× RTX 6000 (TP=1) |
| Все остальные поды | aither-inference | (default = runc) | N8/N7 | — |

---

## 5. GPU visibility внутри подов

### vLLM 14B (N8) — `nvidia-smi` внутри пода

```
GPU 0: Quadro RTX 6000  |  20,185/23,040 MiB  |  P0
GPU 1: Quadro RTX 6000  |  20,185/23,040 MiB  |  P0
→ CUDA available: True, Device count: 2 ✅
```

### vLLM 32B (N7) — `nvidia-smi` внутри пода

```
GPU 0: Quadro RTX 6000  |  21,865/23,040 MiB  |  P0
→ GPU 1 не виден (TP=1) ⚠️
```

---

## 6. CDI (Container Device Interface)

| Узел | /etc/cdi/ | /var/run/cdi/ |
|---|---|---|
| N8 | `nvidia.yaml`, `management.nvidia.com-gpu.yaml` | `nvidia.yaml`, `management.nvidia.com-gpu.yaml`, `k8s.device-plugin.nvidia.com-gpu.json` |
| N7 | `nvidia.yaml`, `management.nvidia.com-gpu.yaml`, `k8s.device-plugin.nvidia.com-gpu.json` | `nvidia.yaml`, `management.nvidia.com-gpu.yaml`, `k8s.device-plugin.nvidia.com-gpu.json` |

CDI-спеки содержат маппинг GPU-устройств (`/dev/nvidia0`, `/dev/dri/card0`, `/dev/dri/renderD128`).

---

## 7. Вывод

| Критерий | Статус |
|---|---|
| containerd установлен на обоих узлах | ✅ v2.2.1 |
| nvidia-runtime зарегистрирован в containerd | ✅ 3 runtime: nvidia, nvidia-cdi, nvidia-legacy |
| RuntimeClass `nvidia` создан в K8s | ✅ Handler: nvidia, возраст 13d |
| CDI-спекы присутствуют | ✅ На обоих узлах |
| vLLM-поды используют `runtimeClassName: nvidia` | ✅ |
| GPU видны внутри подов | ✅ 14B: 2 GPU. 32B: 1 GPU |
| nvidia-smi работает внутри контейнеров | ✅ |
| Обычные поды используют runc (не nvidia) | ✅ |

**Задача #2 ROADMAP («containerd + nvidia-runtime»): ВЫПОЛНЕНА. Работает на обоих узлах.**
