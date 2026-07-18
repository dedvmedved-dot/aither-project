# Этап 1: K8s + GPU Operator на n8

## Конфигурация

### Аппаратное обеспечение

| Компонент | Характеристика |
|-----------|---------------|
| **Сервер** | YADRO VEGMAN S320 (n8, 40.51) |
| **CPU** | 2× Intel Xeon Gold 6258R (28C/56T на сокет, 4.0 GHz Turbo) |
| **RAM** | 768 GB DDR4-2934 ECC (12× Samsung 64GB) |
| **GPU** | 2× NVIDIA Quadro RTX 6000 (24 GB GDDR6 каждая, NVLink bridge) |
| **Диски** | 12× SSD MegaRAID, 2× M.2 NVMe 480GB |
| **ОС** | Astra Linux 1.8.1 (ядро 6.6.28-1-generic) |
| **IP** | 10.129.13.78 (VLAN 308, шлюз 10.129.13.1) |

### K8s кластер

| Параметр | Значение |
|----------|---------|
| **Тип** | kubeadm, single-node (control-plane + worker) |
| **Версия** | v1.33.5 |
| **CNI** | Flannel v0.25.7 (pod CIDR: 10.244.0.0/16) |
| **Runtime** | containerd://2.2.1 |
| **Узлы** | 1 (n8: bootsman-k8s-clnt01-n8-gpu) |
| **Taint** | control-plane: `node-role.kubernetes.io/control-plane-` (удалён) |

### GPU Operator

| Компонент | Статус |
|-----------|--------|
| **Установка** | Helm: `nvidia/gpu-operator` в namespace `gpu-operator` |
| **Режим** | `driver=pre-installed` (драйвер NVIDIA 570.195.03 установлен на хосте) |
| **Device-Plugin** | ✅ Включён — `nvidia.com/gpu: 2` в Capacity узла |
| **DCGM Exporter** | ✅ Включён — метрики GPU |

### Containerd

Серия проблем, решённых в процессе:

1. **Docker Hub заблокирован из РФ** — настроено зеркало `dockerhub.timeweb.cloud`
2. **NVIDIA runtime** — добавлен `nvidia` runtime в `/etc/containerd/config.toml`
3. **GPU Operator auto-import** — перезаписывает секцию `runtimes` через `conf.d/99-nvidia.toml`. Решение: монолитный конфиг без `imports`
4. **CDI vs csv mode** — GPU Operator генерирует CDI-спеки, но containerd не всегда их резолвит. Решение: `mode=csv` в `nvidia-container-runtime`

---

## Последовательность развёртывания

### Шаг 1: Подготовка ОС

```bash
# Установка NVIDIA драйвера
apt-get install -y nvidia-driver-570
# Требуется ребут для выгрузки модуля nouveau
reboot

# После ребута — проверка
nvidia-smi
# → NVIDIA-SMI 570.195.03, CUDA 12.8
# → 2× Quadro RTX 6000, 24 GB

# Восстановление VLAN 308 (не поднимается после ребута)
ip link add link ens1f0 name ens1f0.308 type vlan id 308
```

### Шаг 2: Установка containerd + K8s

```bash
# containerd (идет с Astra Linux, обновить если надо)
apt-get install -y containerd

# kubeadm, kubelet, kubectl
# (бинарники из репозитория Astra или вручную)
kubeadm init \
  --pod-network-cidr=10.244.0.0/16 \
  --apiserver-advertise-address=10.129.13.78

# Разрешить поды на control-plane
kubectl taint nodes --all node-role.kubernetes.io/control-plane-

# CNI Flannel (v0.25.7 — совместим с K8s 1.33)
kubectl apply -f https://github.com/flannel-io/flannel/releases/download/v0.25.7/kube-flannel.yml
```

### Шаг 3: Настройка containerd для NVIDIA

```toml
# /etc/containerd/config.toml (фрагмент)
[plugins."io.containerd.grpc.v1.cri".registry.mirrors."docker.io"]
  endpoint = ["https://dockerhub.timeweb.cloud", "https://mirror.gcr.io"]

[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia]
  runtime_type = "io.containerd.runc.v2"
  [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia.options]
    BinaryName = "/usr/local/nvidia/toolkit/nvidia-container-runtime"
    SystemdCgroup = true
```

### Шаг 4: GPU Operator

```bash
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm install gpu-operator nvidia/gpu-operator \
  -n gpu-operator --create-namespace
```

### Шаг 5: Проверка

```bash
kubectl describe node bootsman-k8s-clnt01-n8-gpu | grep -A4 Capacity
# Capacity:
#   cpu:                112
#   nvidia.com/gpu:     2
#   nvidia.com/gpu.memory:  23040
#   nvidia.com/gpu.count:   2
```

---

## Текущее состояние (18.07.2026)

| Компонент | Статус | Детали |
|-----------|--------|--------|
| **K8s API Server** | ✅ Running | v1.33.5, etcd 2/2 |
| **K8s Nodes** | ✅ Ready | 1 узел (n8) |
| **containerd** | ✅ Running | версия: 2.2.1 |
| **GPU Operator** | ⚠️ Частично | GPU в Capacity есть, но namespace `gpu-operator` пуст (поды не найдены) |
| **NVIDIA driver** | ✅ | 570.195.03, CUDA 12.8 |
| **GPU доступность** | ✅ | Обе RTX 6000 видны, каждая ~20.3/23 GB занято под vLLM |
| **Flannel** | ✅ | v0.25.7, pod network работает |
| **CoreDNS** | ✅ | 2 пода Running (много рестартов из-за стабильности containerd) |

### Проблемы

1. **GPU Operator pods не найдены** — возможно, удалены или namespace пересоздан. GPU при этом работают через containerd-nvidia напрямую
2. **CoreDNS/Flannel имеют рестарты** (455 на kube-controller-manager) — не критично, но указывает на нестабильность
3. **Много рестартов системных подов** — при перезагрузке containerd/K8s без graceful shutdown
4. **Parsec Смоленск(2) блокирует** — решено через `parsec=0` в GRUB
5. **imports в containerd** — GPU Operator создаёт `conf.d/99-nvidia.toml`, который конфликтует с основным конфигом

---

## Схема архитектуры (DOT)

```dot
digraph K8sGPUOperator {
    rankdir=LR;
    bgcolor="#ffffff";
    fontname="Inter";
    splines=ortho;
    node [shape=box, style=filled, fontname="Inter", fontsize=11];

    subgraph cluster_hardware {
        label="Сервер n8 (YADRO VEGMAN S320)";
        style=filled;
        bgcolor="#f0f4ff";
        color="#6366f1";
        fontcolor="#6366f1";
        fontsize=13;

        cpu [label="CPU: 2× Xeon Gold 6258R\n28C/56T @ 4.0 GHz" fillcolor="#e0e7ff"];
        ram [label="RAM: 768 GB DDR4-2934\n12× Samsung 64GB ECC" fillcolor="#e0e7ff"];
        gpu0 [label="GPU 0: Quadro RTX 6000\n24 GB GDDR6" fillcolor="#c7d2fe"];
        gpu1 [label="GPU 1: Quadro RTX 6000\n24 GB GDDR6" fillcolor="#c7d2fe"];
        nvlink [label="NVLink Bridge\nGPU↔GPU" fillcolor="#a5b4fc"];

        gpu0 -> nvlink [dir=none];
        nvlink -> gpu1 [dir=none];
    }

    subgraph cluster_os {
        label="ОС";
        style=filled;
        bgcolor="#fef3c7";
        color="#f59e0b";
        fontcolor="#f59e0b";
        fontsize=13;

        astra [label="Astra Linux 1.8.1\nядро 6.6.28-1-generic" fillcolor="#fde68a"];
        nvidia [label="NVIDIA Driver 570.195.03\nCUDA 12.8" fillcolor="#fef3c7"];
        containerd [label="containerd 2.2.1\nnvidia-runtime" fillcolor="#fef3c7"];
        flannel [label="Flannel CNI v0.25.7\n10.244.0.0/16" fillcolor="#fef3c7"];

        astra -> nvidia;
        astra -> containerd;
        astra -> flannel;
    }

    subgraph cluster_k8s {
        label="Kubernetes v1.33.5 (kubeadm)";
        style=filled;
        bgcolor="#ecfdf5";
        color="#10b981";
        fontcolor="#10b981";
        fontsize=13;

        apiserver [label="API Server\n10.129.13.78:6443" fillcolor="#d1fae5"];
        etcd [label="etcd" fillcolor="#d1fae5"];
        scheduler [label="Scheduler" fillcolor="#d1fae5"];
        controller [label="Controller Manager" fillcolor="#d1fae5"];
        coredns [label="CoreDNS" fillcolor="#d1fae5"];
        kubelet [label="Kubelet\ncontainerd://2.2.1" fillcolor="#d1fae5"];
        metrics [label="metrics-server" fillcolor="#d1fae5"];

        apiserver -> etcd;
        apiserver -> scheduler;
        apiserver -> controller;
        apiserver -> coredns;
        apiserver -> kubelet;
        apiserver -> metrics;
    }

    subgraph cluster_gpu {
        label="GPU Operator (Helm)";
        style=filled;
        bgcolor="#fce7f3";
        color="#ec4899";
        fontcolor="#ec4899";
        fontsize=13;

        device_plugin [label="NVIDIA Device Plugin\nnvidia.com/gpu: 2" fillcolor="#fbcfe8"];
        dcgm [label="DCGM Exporter\nGPU метрики" fillcolor="#fbcfe8"];
        gpu_feature [label="Feature Discovery\nGPU topology" fillcolor="#fbcfe8"];
        validator [label="Validator\nGPU readiness" fillcolor="#fbcfe8"];

        device_plugin -> dcgm;
        device_plugin -> gpu_feature;
    }

    subgraph cluster_vllm {
        label="vLLM под (default ns)";
        style=filled;
        bgcolor="#ede9fe";
        color="#8b5cf6";
        fontcolor="#8b5cf6";
        fontsize=13;

        vllm_pod [label="vllm-coder-14b\n1/1 Running\nTP=2 (2 GPU)\nQwen2.5-Coder-14B" fillcolor="#ddd6fe"];
    }

    # Связи
    kubelet -> containerd [style=dashed];
    kubelet -> device_plugin [style=dashed];
    kubelet -> vllm_pod [style=dashed];

    nvidia -> containerd [style=dashed];
    containerd -> device_plugin [style=dashed];

    gpu0 -> vllm_pod [style=dashed, color="#8b5cf6"];
    gpu1 -> vllm_pod [style=dashed, color="#8b5cf6"];

    gpu0 -> device_plugin [style=dotted];
    gpu1 -> device_plugin [style=dotted];

    # Легенда
    legend [shape=none, fontsize=10, label=<
        <TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
        <TR><TD COLSPAN="3" ALIGN="left"><B>Легенда:</B></TD></TR>
        <TR><TD BGCOLOR="#d1fae5" WIDTH="12" HEIGHT="12"></TD><TD>— K8s компонент</TD></TR>
        <TR><TD BGCOLOR="#c7d2fe" WIDTH="12" HEIGHT="12"></TD><TD>— GPU / Аппаратное обеспечение</TD></TR>
        <TR><TD BGCOLOR="#fde68a" WIDTH="12" HEIGHT="12"></TD><TD>— Системное ПО</TD></TR>
        <TR><TD BGCOLOR="#fbcfe8" WIDTH="12" HEIGHT="12"></TD><TD>— GPU Operator</TD></TR>
        <TR><TD BGCOLOR="#ddd6fe" WIDTH="12" HEIGHT="12"></TD><TD>— Пользовательский под</TD></TR>
        </TABLE>
    >];
}
```
