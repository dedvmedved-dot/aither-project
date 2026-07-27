# Отчёт: K8s + GPU Operator — верификация задачи #1 ROADMAP

**Задача:** #1 — K8s + GPU Operator на n8
**Дата проверки:** 27.07.2026 17:01 МСК
**Метод:** Live-команды kubectl, nvidia-smi, ssh
**Результат:** ✅ РАБОТАЕТ

---

## 1. Кластер

| Параметр | N8 (control-plane) | N7 (worker) |
|---|---|---|
| **Статус** | Ready | Ready |
| **Роль** | control-plane | none |
| **IP** | 10.129.13.78 | 10.129.13.77 |
| **Версия K8s** | v1.33.5 | v1.33.5 |
| **ОС** | Astra Linux | Astra Linux |
| **Ядро** | 6.6.28-1-generic | 6.6.28-1-generic |
| **Архитектура** | amd64 | amd64 |
| **CPU** | 112 ядер | 112 ядер |
| **RAM** | 791 GB (755 GiB) | 791 GB (755 GiB) |
| **Container Runtime** | containerd 2.2.1 | containerd 2.2.1 |
| **Возраст** | 13 дней | 13 дней |
| **GPU** | 2× Quadro RTX 6000 (23 GB) | 2× Quadro RTX 6000 (23 GB) |

---

## 2. Control Plane (N8)

| Компонент | Статус | Возраст |
|---|---|---|
| etcd | Running | 13d |
| kube-apiserver | Running | 13d |
| kube-controller-manager | Running | 13d |
| kube-scheduler | Running | 13d |
| kube-proxy | Running | 13d |

---

## 3. Сеть и DNS

| Компонент | Статус | Узел |
|---|---|---|
| Flannel CNI | Running | N7 + N8 |
| CoreDNS (2 реплики) | Running | N7 |
| Metrics Server | Running | N7 |

---

## 4. NVIDIA GPU Operator

| Компонент | Тип | N8 | N7 |
|---|---|---|---|
| **gpu-operator** | Deployment | — | Running (1/1) |
| **nvidia-container-toolkit** | DaemonSet | Running | Running |
| **nvidia-device-plugin** | DaemonSet | Running | Running |
| **nvidia-dcgm-exporter** | DaemonSet | Running | Running |
| **gpu-feature-discovery** | DaemonSet | Running | Running |
| **nvidia-operator-validator** | DaemonSet | Running | Running |
| **nvidia-cuda-validator** | Job | — | Completed |
| **nvidia-device-plugin-mps** | DaemonSet | 0/0 (MPS не поддерживается) | 0/0 |
| **nvidia-mig-manager** | DaemonSet | 0/0 (MIG не поддерживается) | 0/0 |

---

## 5. GPU-ресурсы (Allocatable)

| Узел | GPU | Модель | Память (GPU) | Доступно |
|---|---|---|---|---|
| N8 | 2 | Quadro RTX 6000 | 23,040 MiB × 2 | 2/2 allocatable |
| N7 | 2 | Quadro RTX 6000 | 23,040 MiB × 2 | 1/2 allocatable (1 свободна) |

---

## 6. nvidia-smi (N8)

```
Driver Version: 590.48.01    CUDA Version: 13.1

GPU 0: Quadro RTX 6000  |  32°C  |  P0  |  60W/250W  |  20,185/23,040 MiB  |  0% util
GPU 1: Quadro RTX 6000  |  32°C  |  P0  |  61W/250W  |  20,185/23,040 MiB  |  0% util

Процессы:
  GPU 0: /usr/bin/python3 (vLLM 14B)  — 20,170 MiB
  GPU 1: /usr/bin/python3 (vLLM 14B)  — 20,170 MiB
```

## 7. nvidia-smi (N7)

```
Driver Version: 590.48.01    CUDA Version: 13.1

GPU 0: Quadro RTX 6000  |  35°C  |  P0  |  62W/250W  |  21,865/23,040 MiB  |  0% util
GPU 1: Quadro RTX 6000  |  30°C  |  P8  |  24W/250W  |       0/23,040 MiB  |  0% util

Процессы:
  GPU 0: /usr/bin/python3 (vLLM 32B)  — 21,854 MiB
  GPU 1: — (простаивает)
```

> ⚠️ N7 GPU#1 простаивает (P8, 0 MiB). Причина: vLLM-32b запущен с `tensor-parallel-size=1` вместо 2.

---

## 8. Кастомные лейблы узлов

| Лейбл | N8 | N7 | Назначение |
|---|---|---|---|
| `aither.io/vllm14b-primary` | true | — | Привязка 14B к N8 (EMG-01) |
| `aither.io/qwen14b-instruct` | true | true | Доступность 14B |
| `aither.io/qwen32b-gptq` | true | true | Доступность 32B |
| `aither.io/benchmark-node` | true | — | Бенчмарк-узел |
| `aither.io/inference-primary` | — | true | Основной инференс-узел |

---

## 9. Вывод

| Критерий | Статус |
|---|---|
| K8s кластер поднят (2 узла) | ✅ |
| Control plane работает (N8) | ✅ |
| GPU Operator развёрнут | ✅ |
| Все DaemonSet'ы GPU Operator Running | ✅ |
| GPU видны и аллоцируются (nvidia.com/gpu: 2) | ✅ |
| NVIDIA-драйвер (590.48.01, CUDA 13.1) | ✅ |
| vLLM использует GPU (14B на N8, 32B на N7) | ✅ |
| N7 GPU#1 простаивает (TP=1 баг 32B) | ⚠️ Не влияет на задачу #1 |

**Задача #1 ROADMAP («K8s + GPU Operator на n8»): ВЫПОЛНЕНА. Работает.**
