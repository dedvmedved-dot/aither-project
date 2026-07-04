# Адаптация ТР №1 и ТР №2 под один сервер 40.51

**Дата:** 04.07.2026
**Причина:** сервер 40.50 недоступен (RAID сбой + CMOS 2001г). MVP разворачивается на единственном сервере 40.51.

---

## ТР №1: Ядро Aither — Single-Node MVP

### Исходная архитектура (ТР №1, раздел 3.11)

2 сервера RedOS 7.3, 4× RTX 6000, K3s-кластер:

| Сервер | Компоненты |
|---|---|
| Server-1 | Gateway + Billing + Redis + 2× vLLM (RTX 6000 #1, #2) + PostgreSQL (protected) |
| Server-2 | Gateway replica + 2× vLLM (RTX 6000 #3, #4) + model cache (RAID0) |

### Адаптированная архитектура

ВСЁ на одном сервере 40.51 (Astra Linux 1.8), 2× RTX 6000 (24 GB):

```
┌─────────────────────────────────────────────────┐
│                VPS2 (130.17.1.90)                │
│  ┌───────────────────────────────────────────┐  │
│  │  Reverse Proxy (nginx)                    │  │
│  │  TLS termination + WAF                    │  │
│  │  :443 → 10.129.13.78:8080                 │  │
│  └───────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────┐  │
│  │  Портал Aither (ТР №2)                    │  │
│  │  Portal BFF + Portal DB                   │  │
│  └───────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────┘
                   │ SSH-туннель / VPN (52ms)
                   ▼
┌─────────────────────────────────────────────────┐
│          40.51 — Single-Node K8s                 │
│  Astra Linux 1.8, 2×28C/56T, 754GB, 2×RTX6000   │
│                                                   │
│  ┌─────────────┐  ┌──────────┐  ┌─────────────┐ │
│  │ API Gateway │  │ Billing  │  │ Usage       │ │
│  │ (LiteLLM)   │  │ Service  │  │ Collector   │ │
│  └──────┬──────┘  └────┬─────┘  └──────┬──────┘ │
│         │              │               │         │
│  ┌──────┴──────────────┴───────────────┴──────┐  │
│  │         PostgreSQL + Redis                 │  │
│  │  (локально, без репликации — SPOF)         │  │
│  └────────────────────────────────────────────┘  │
│                                                   │
│  ┌──────────────┐    ┌──────────────┐            │
│  │ vLLM GPU #0  │    │ vLLM GPU #1  │            │
│  │ RTX 6000     │    │ RTX 6000     │            │
│  │ Qwen3-14B    │    │ Qwen3-14B    │            │
│  └──────────────┘    └──────────────┘            │
└─────────────────────────────────────────────────┘
```

### Изменения относительно ТР №1

| Параметр | ТР №1 (исходный) | Single-node |
|---|---|---|
| Серверов | 2 | 1 |
| GPU | 4× RTX 6000 | 2× RTX 6000 |
| ОС | RedOS 7.3/8.0.2 | Astra Linux 1.8 |
| Оркестрация | K3s (2 узла) | K8s single-node |
| PostgreSQL | с репликацией | без репликации (SPOF) |
| Redis | single (SPOF) | single (SPOF, без изменений) |
| Входная точка | Внешний ALB | nginx на VPS2 |
| vLLM-реплик | 4 | 2 |

### Дисковая разметка

| Устройство | Назначение |
|---|---|
| sda (447G) | ОС Astra Linux |
| sdb (1.7T) | PostgreSQL data + WAL |
| sdc (3.5T) | Redis + логи |
| sdd (3.5T) | Модели (model cache) |
| sde (3.5T) | Бэкапы |
| sdf–sdm | Резерв / доразметка при необходимости |

### Что остаётся без изменений

- ✅ Billing Service (reserve → settle → refund)
- ✅ Append-only PostgreSQL ledger
- ✅ Gateway + Rate Limiter + Admission Controller
- ✅ Observability (Prometheus, логи, трейсы)
- ✅ Модель угроз (Threat Model)
- ✅ Все Gates (0–5), просто Gate 0 теперь для Astra Linux

### Что документируется как SPOF

| Компонент | Последствия отказа |
|---|---|
| Сервер 40.51 | Полная недоступность API и инференса |
| PostgreSQL | Финансовые операции остановлены (fail-closed) |
| Redis | Rate limiting остановлен, новые запросы 503 |
| 1 GPU из 2 | Деградация: 1 vLLM вместо 2 |

---

## ТР №2: Портал Aither

### Без изменений

Портал изначально проектировался для VPS2 и взаимодействует с ядром через Core Management API. Никаких адаптаций не требуется.

```
VPS2
├── Portal BFF (Fastify/Node.js)
├── Portal DB (PostgreSQL)
├── Frontend (React/Vite)
└── → Core Management API → 10.129.13.78 (ядро на 40.51)
```

---

## План реализации (Gate 0 → MVP)

### Gate 0: Compatibility Study (Astra Linux 1.8)

```bash
# На 40.51:
nvidia-smi
uname -a
cat /etc/astra-release
docker --version
kubectl version
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
python -m vllm.entrypoints.openai.api_server --version
kubectl get nodes -o wide
```

**Критерий GO:** Qwen3-14B загружается на одном RTX 6000, health check зелёный, тестовая генерация работает.

### Gate 1: Model Fit
- Qwen3-14B в 4-bit — ~8–10 GB VRAM, помещается с запасом
- Две независимые реплики на двух GPU (без тензорного параллелизма)

### Gate 2: K8s single-node
```bash
kubeadm init --pod-network-cidr=10.244.0.0/16
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
# NVIDIA GPU Operator
helm install nvidia-gpu-operator nvidia/gpu-operator
```

### Gate 3: Развёртывание ядра Aither
- Gateway + Billing + Usage Collector — как поды K8s
- PostgreSQL + Redis — как StatefulSet / локальные сервисы
- vLLM — 2 реплики, по одной на GPU

### Gate 4: Портал на VPS2
- Portal BFF + Portal DB
- nginx reverse proxy: внешний мир → VPS2 → 40.51

---

## Сравнение: было vs стало

| | ТР №1 (исходный) | Single-node MVP |
|---|---|---|
| GPU-слотов | 4 | 2 |
| Пропускная способность | ~4× Qwen3-14B | ~2× Qwen3-14B |
| Отказоустойчивость | частичная | документированный SPOF |
| PostgreSQL HA | репликация | без репликации |
| Срок до MVP | дольше (2 сервера) | быстрее (1 сервер) |
| Готовность к Pilot | требуется 2-й сервер или cloud | то же самое |
