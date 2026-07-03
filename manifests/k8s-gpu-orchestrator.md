# Оркестратор: выбор K3s → K8s (полный Kubernetes)

## Решение: использовать полный Kubernetes

**Причина:** K3s не соответствует production-требованиям для GPU-кластера на YADRO VEGMAN S320.

## Сравнение K3s vs K8s

| Критерий | K3s | K8s (полный) | Влияние на Aither |
|---|---|---|---|
| **etcd** | SQLite (нет HA) | etcd RAFT-кластер | Критично: финансовая целостность |
| **GPU Operator** | Костыли (device-plugin) | Нативный NVIDIA GPU Operator | Критично: MIG, NVLink, мониторинг |
| **Сеть** | Flannel (overlay) | Calico/Cilium (eBPF, NetworkPolicy) | Важно: изоляция трафика |
| **Масштабирование** | До 100 нод (болезненно) | 5000+ нод штатно | Будущее: добавление GPU-нод |
| **Безопасность** | Ограниченная RBAC | Полная RBAC + PodSecurity | Критично: платёжные данные |
| **PV/PVC** | local-path по умолчанию | CSI-драйверы (MegaRAID) | Важно: 38 TB дисков |
| **Обновления** | Ручные, без отката | Штатный rolling update | Важно: бесперебойная работа |
| **Мониторинг** | Ограниченный | Prometheus Operator из коробки | Критично: SLO/SLI |

## Архитектура K8s-кластера

```
┌─────────────────────────────────────────────────┐
│                  K8s CLUSTER                     │
│                                                  │
│  ┌─────────────────────┐  ┌──────────────────┐  │
│  │    node01 (CP)       │  │   node02 (W)     │  │
│  │  10.129.13.171       │  │  10.129.13.172   │  │
│  │                      │  │                   │  │
│  │  etcd ───────────────│──│── etcd            │  │
│  │  api-server          │  │                   │  │
│  │  controller-manager  │  │  vLLM pods        │  │
│  │  scheduler           │  │  PostgreSQL        │  │
│  │                      │  │  Redis             │  │
│  │  GPU 0 + GPU 1       │  │  GPU 0 + GPU 1    │  │
│  │  (NVLink)            │  │  (NVLink)         │  │
│  └─────────────────────┘  └──────────────────┘  │
│                                                  │
│         Calico/Cilium (VLAN 308)                 │
│         NVIDIA GPU Operator                      │
│         Prometheus + Grafana                     │
│         Cert-Manager                             │
└─────────────────────────────────────────────────┘
```

## Компоненты

| Компонент | Версия | Назначение |
|---|---|---|
| Kubernetes | 1.32.x | Оркестрация |
| etcd | 3.5.x | RAFT-хранилище (3 экземпляра, 2 ноды + 1?) |
| Cilium | 1.16+ | CNI, NetworkPolicy, eBPF |
| NVIDIA GPU Operator | 25.x | GPU-драйверы, MIG, device-plugin, мониторинг |
| cert-manager | 1.16+ | TLS-сертификаты |
| Prometheus-stack | 68.x | Мониторинг |

## GPU: NVLink и vLLM

Два RTX 6000 соединены NVLink Bridge (50 GB/s). Это даёт единое адресное пространство 48 GB для моделей до 70B параметров (4-bit quant).

```yaml
# GPU Operator конфигурация
nvidia:
  mig:
    enabled: false  # RTX 6000 не поддерживает MIG (только A100/H100+)
  driver:
    version: "570.144"  # из RED OS 8.0
  toolkit:
    enabled: true
  dcgm:
    enabled: true  # мониторинг
  devicePlugin:
    enabled: true
  gfd:
    enabled: true  # GPU Feature Discovery для NVLink
```

## Что нужно для перехода с K3s на K8s

1. При установке RED OS 8.0 — не ставить K3s
2. Установить kubeadm + containerd (штатный путь RED OS)
3. Инициализировать кластер: `kubeadm init` на node01, `kubeadm join` на node02
4. Развернуть Cilium, GPU Operator, Prometheus через Helm
5. Настроить CSI-драйвер для MegaRAID

**ИТОГ: K3s → K8s. Решение окончательное.**
