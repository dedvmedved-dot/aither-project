# Этап 2: Containerd + NVIDIA Container Runtime

## Роль в дорожной карте

Этап 2 — фундаментальный слой для запуска GPU-инференса в Kubernetes.
Без него Pod'ы не могут запросить `nvidia.com/gpu`, а vLLM — стартовать модель.

```
┌──────────────────────────────────────────────────┐
│                    Этап 7                         │
│                 OAuth / Portal                    │
├──────────────────────────────────────────────────┤
│                    Этап 6                         │
│              Portal SPA + BFF + SSE               │
├──────────────────────────────────────────────────┤
│                    Этап 5                         │
│            Gateway + Redis / Rate Limit           │
├──────────────────────────────────────────────────┤
│                    Этап 4                         │
│        Tensor Parallelism (2× RTX 6000)           │
├──────────────────────────────────────────────────┤
│                    Этап 3                         │
│              vLLM 14B deploy                      │
├──────────────────────────────────────────────────┤
│      ┌──────────────┴──────────────┐              │
│      │   ЭТАП 2 (containerd+GPU)   │  ← ВЫ ЗДЕСЬ │
│      └──────────────┬──────────────┘              │
├──────────────────────────────────────────────────┤
│                    Этап 1                         │
│            K8s + GPU Operator                    │
└──────────────────────────────────────────────────┘
```

---

## Конфигурация

### Узлы

| Хост | IP | Роль | GPU |
|------|-----|------|-----|
| **n8** | `10.129.13.78` | Worker (K8s) | 2× Quadro RTX 6000 23GB |
| **n7** | `10.129.13.77` | Worker (K8s) | 2× Quadro RTX 6000 23GB |
| **core3** | `10.129.13.3` | Bastion / ProxyJump | — |

### 2.1 containerd — установка через apt

```bash
# Установка containerd.io (через официальный репозиторий Docker)
apt-get update
apt-get install -y containerd.io

# Сгенерировать конфиг по умолчанию
containerd config default > /etc/containerd/config.toml

# Обязательно включить SystemdCgroup
# В секции [plugins."io.containerd.cri.v1.runtime".containerd.runtimes.runc.options]
#   SystemdCgroup = true
```

### 2.2 NVIDIA Container Toolkit — установка

```bash
# Добавить репозиторий NVIDIA
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  > /etc/apt/sources.list.d/nvidia-container-toolkit.list

apt-get update && apt-get install -y nvidia-container-toolkit
```

### 2.3 NVIDIA Runtime Class для containerd

```bash
nvidia-ctk runtime configure --runtime=containerd
systemctl restart containerd
```

После выполнения в `/etc/containerd/config.toml` добавляется секция:

```toml
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia]
  runtime_type = "io.containerd.runc.v2"
  [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia.options]
    BinaryName = "/usr/local/nvidia/toolkit/nvidia-container-runtime"
    SystemdCgroup = true
```

> **Важно:** в `config.toml` версии 3 (containerd ≥2.0) секции лежат в пространстве
> `io.containerd.cri.v1.runtime`, а также дублируются в legacy `io.containerd.grpc.v1.cri`
> для обратной совместимости. Обе должны быть обновлены.

### 2.4 RuntimeClass в K8s

```yaml
# manifests/runtimeclass-nvidia.yaml
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: nvidia
handler: nvidia
```

Применение:
```bash
kubectl apply -f manifests/runtimeclass-nvidia.yaml
```

---

## Последовательность развёртывания

```
Шаг 2.1  Установка / проверка containerd
               │
               ▼
Шаг 2.2  NVIDIA Container Toolkit (apt install nvidia-container-toolkit)
               │
               ▼
Шаг 2.3  nvidia-ctk runtime configure --runtime=containerd
         → добавляет runtime nvidia в /etc/containerd/config.toml
               │
               ▼
Шаг 2.4  systemctl restart containerd
               │
               ▼
Шаг 2.5  kubectl apply -f manifests/runtimeclass-nvidia.yaml
               │
               ▼
Шаг 2.6  Проверка: kubectl get runtimeclass
         → NAME=nvidia  HANDLER=nvidia
               │
               ▼
Шаг 2.7  Проверка: k8s Node capacity
         → nvidia.com/gpu: 2
           (появляется только после GPU Operator — Этап 1)
```

---

## Текущее состояние (18.07.2026)

### Containerd

| Узел | Статус | Версия |
|------|--------|---------|
| **n8** | ✅ Работает | containerd 2.2.x (через пакет docker.io) |
| **n7** | ✅ Работает | containerd 2.2.1 (пакет `containerd`) |
| **core3** | N/A | Bastion, без containerd |

### NVIDIA Container Toolkit

| Узел | Статус | Версия |
|------|--------|---------|
| **n8** | ✅ Установлен | 1.19.1 |
| **n7** | ✅ Установлен | 1.19.1 |

### nvidia-runtime в containerd

| Узел | Статус | Файл конфига |
|------|--------|-------------|
| **n8** | ✅ **BinaryName** = `/usr/bin/nvidia-container-runtime` | `/etc/containerd/conf.d/99-nvidia.toml` |
| **n7** | ✅ **BinaryName** = `/usr/bin/nvidia-container-runtime` | `/etc/containerd/conf.d/99-nvidia.toml` |

### RuntimeClass

```bash
$ kubectl get runtimeclass
NAME     HANDLER   AGE
nvidia   nvidia    7d
```

✅ RuntimeClass `nvidia` существует и работает на обеих нодах.

### GPU в Capacity

```bash
$ kubectl get nodes -o custom-columns=NAME:.metadata.name,GPU:.status.capacity.nvidia\\.com/gpu
NAME                             GPU
bootsmam-k8s-clnt01-n7-gpu       2
bootsman-k8s-clnt01-n8-gpu       2
```

✅ **nvidia.com/gpu = 2** на каждой ноде.

### GPU Operator

```bash
$ kubectl get pods -n gpu-operator -o wide

NAME                                                         READY   NODE                         GPU
gpu-feature-discovery-697qs                                  1/1     bootsmam-k8s-clnt01-n7-gpu   ✅
gpu-feature-discovery-sr2qp                                  1/1     bootsman-k8s-clnt01-n8-gpu   ✅
gpu-operator-7d9956bc88-lthll                                1/1     bootsman-k8s-clnt01-n8-gpu   —
nvidia-container-toolkit-daemonset-8cmp8                     1/1     bootsmam-k8s-clnt01-n7-gpu   ✅
nvidia-container-toolkit-daemonset-qwr9x                     1/1     bootsman-k8s-clnt01-n8-gpu   ✅
nvidia-dcgm-exporter-gxwgn                                   1/1     bootsmam-k8s-clnt01-n7-gpu   ✅
nvidia-dcgm-exporter-xxx                                     1/1     bootsman-k8s-clnt01-n8-gpu   ✅
nvidia-device-plugin-daemonset-ssqkm                         1/1     bootsmam-k8s-clnt01-n7-gpu   ✅
nvidia-device-plugin-daemonset-xxx                           1/1     bootsman-k8s-clnt01-n8-gpu   ✅
nvidia-operator-validator-57c46                              1/1     bootsmam-k8s-clnt01-n7-gpu   —
```

✅ GPU Operator **полностью работает** на обеих нодах.

### Сводка

| Компонент | n8 (worker) | n7 (worker) |
|-----------|-------------|-------------|
| GPU | ✅ 2× Quadro RTX 6000 | ✅ 2× Quadro RTX 6000 |
| containerd | ✅ 2.2.x | ✅ 2.2.1 |
| NVIDIA Container Toolkit | ✅ 1.19.1 | ✅ 1.19.1 |
| RuntimeClass nvidia | ✅ создан | ✅ создан |
| nvidia-runtime в config.toml | ✅ `/usr/bin/nvidia-container-runtime` | ✅ `/usr/bin/nvidia-container-runtime` |
| GPU в Capacity | ✅ 2/2 | ✅ 2/2 |
| GPU Operator DaemonSet | ✅ Все Running | ✅ Все Running |

### RuntimeClass

```bash
$ kubectl get runtimeclass
NAME     HANDLER   AGE
nvidia   nvidia    7d
```

✅ RuntimeClass `nvidia` существует в кластере.

На n8 может работать как дефолтный handler (`runc`), так и `nvidia`.
На n7 не будет работать, пока не установлен NVIDIA Container Toolkit.

### GPU Operator

```bash
$ kubectl get pods -n gpu-operator
NAME                                                   READY   STATUS      RESTARTS   AGE
gpu-operator-77b98fbc57-ntdbt                          1/1     Running     0          13d
nvidia-container-toolkit-daemonset-2g988                1/1     Running     0          13d
nvidia-cuda-validator-jf7w6                            0/1     Completed   0          13d
nvidia-dcgm-exporter-dbscj                             1/1     Running     0          13d
nvidia-device-plugin-daemonset-tw58d                   1/1     Running     0          13d
nvidia-feature-discovery-daemonset-db579              1/1     Running     0          13d
nvidia-mig-manager-7wslk                               1/1     Running     0          13d
nvidia-node-status-exporter-2d2s5                      1/1     Running     0          13d
nvidia-operator-validator-bb8xk                        1/1     Running     0          13d
```

✅ GPU Operator работает, его DaemonSet'ы уже развёрнуты.
На n8 DaemonSet'ы функционируют, но сама нода без GPU.
На n7 DaemonSet'ы не могут зарегистрировать GPU, пока отсутствует NVIDIA CTK.

### Конфигурация containerd на n7

```
Версия:    3
Runtime:   runc (default) + SystemdCgroup = true
nvidia:    ✅ /etc/containerd/conf.d/99-nvidia.toml
           BinaryName = /usr/bin/nvidia-container-runtime
           SystemdCgroup = true
```

NVIDIA container runtime настроен через `nvidia-ctk runtime configure`:

```toml
# /etc/containerd/conf.d/99-nvidia.toml
version = 3

[plugins]

  [plugins."io.containerd.cri.v1.runtime"]

    [plugins."io.containerd.cri.v1.runtime".cni]
      bin_dirs = ["/opt/cni/bin"]
      conf_dir = "/etc/cni/net.d"

    [plugins."io.containerd.cri.v1.runtime".containerd]
      default_runtime_name = "runc"

      [plugins."io.containerd.cri.v1.runtime".containerd.runtimes]

        [plugins."io.containerd.cri.v1.runtime".containerd.runtimes.nvidia]
          runtime_type = "io.containerd.runc.v2"

          [plugins."io.containerd.cri.v1.runtime".containerd.runtimes.nvidia.options]
            BinaryName = "/usr/bin/nvidia-container-runtime"
            SystemdCgroup = true

        [plugins."io.containerd.cri.v1.runtime".containerd.runtimes.runc]
          runtime_type = "io.containerd.runc.v2"

          [plugins."io.containerd.cri.v1.runtime".containerd.runtimes.runc.options]
            SystemdCgroup = true
```

### Сводка

| Компонент | n8 (worker) | n7 (worker) |
|-----------|-------------|-------------|
| GPU | ✅ 2× Quadro RTX 6000 | ✅ 2× Quadro RTX 6000 |
| containerd | ✅ 2.2.x | ✅ 2.2.1 |
| NVIDIA Container Toolkit | ✅ 1.19.1 | ✅ 1.19.1 |
| RuntimeClass nvidia | ✅ создан | ✅ создан |
| nvidia-runtime в config.toml | ✅ `/usr/bin/nvidia-container-runtime` | ✅ `/usr/bin/nvidia-container-runtime` |
| GPU в Capacity | ✅ 2/2 | ✅ 2/2 |
| GPU Operator DaemonSet | ✅ Все Running | ✅ Все Running |

---

## Диаграмма компонентов (DOT)

```dot
// Этап 2: Containerd + NVIDIA Runtime — компоненты и связи
// Сохранено: docs/diagrams/02-containerd-nvidia-runtime.dot

digraph G {
    rankdir=LR;
    splines=ortho;
    node [shape=box, style=rounded];
    ranksep=1.2;

    subgraph cluster_legend {
        label="Легенда";
        color=lightgrey;
        n8 [label="n8: Worker + 2×RTX6000", shape=box, style=filled, fillcolor=lightgreen];
        n7 [label="n7: Worker + 2×RTX6000", shape=box, style=filled, fillcolor=lightsalmon];
    }

    subgraph cluster_k8s {
        label="Kubernetes";
        runtimeclass [label="RuntimeClass: nvidia", shape=cylinder, style=filled, fillcolor=lightblue];
        gpu_op [label="GPU Operator (Helm)", shape=box3d, style=filled, fillcolor=lightyellow];
        pod_gpu [label="Pod: nvidia.com/gpu=1", shape=box, style=filled, fillcolor=lightcyan];
    }

    subgraph cluster_n8 {
        label="Узел n8 (10.129.13.78)";
        containerd_n8 [label="containerd 2.2.x ✔", shape=box, style=filled, fillcolor=green, fontcolor=white];
        ctr_n8 [label="runtime: runc + nvidia", shape=box, style=filled, fillcolor=lightgreen];
        nvidia_ctk_n8 [label="NVIDIA CTK ✅\n1.19.1", shape=box, style=filled, fillcolor=green, fontcolor=white];
        gpu_hw_n8 [label="2× RTX 6000 23GB", shape=box, style=filled, fillcolor=lightgrey];
        gpu_ok_n8 [label="GPU в Capacity: ✅ 2/2", shape=box, style=filled, fillcolor=green, fontcolor=white];

        containerd_n8 -> nvidia_ctk_n8;
        nvidia_ctk_n8 -> gpu_ok_n8 [label="runtime готов"];
        gpu_hw_n8 -> gpu_ok_n8 [label="GPU зарегистрированы", style=dashed];
    }

    subgraph cluster_n7 {
        label="Узел n7 (10.129.13.77)";
        containerd_n7 [label="containerd 2.2.1 ✔", shape=box, style=filled, fillcolor=green, fontcolor=white];
        nvidia_ctk_n7 [label="NVIDIA CTK ✅\n1.19.1", shape=box, style=filled, fillcolor=green, fontcolor=white];
        gpu_hw_n7 [label="2× RTX 6000 23GB", shape=box, style=filled, fillcolor=lightgrey];
        gpu_ok_n7 [label="GPU в Capacity: ✅ 2/2", shape=box, style=filled, fillcolor=green, fontcolor=white];

        containerd_n7 -> nvidia_ctk_n7;
        nvidia_ctk_n7 -> gpu_ok_n7 [label="runtime готов"];
        gpu_hw_n7 -> gpu_ok_n7 [label="GPU зарегистрированы", style=dashed];
    }

    // Связи кластера
    gpu_op -> runtimeclass [label="создаёт"];
    gpu_op -> gpu_ok_n8 [label="DaemonSet на n8"];
    gpu_op -> gpu_ok_n7 [label="DaemonSet на n7"];
    runtimeclass -> gpu_ok_n8 [label="handler = nvidia"];
    runtimeclass -> gpu_ok_n7 [label="handler = nvidia"];
    pod_gpu -> gpu_ok_n8 [label="может запросить GPU", style=dashed];
    pod_gpu -> gpu_ok_n7 [label="может запросить GPU", style=dashed];
}
```

## Диаграмма последовательности развёртывания (DOT)

```dot
// Последовательность развёртывания Этапа 2
// Сохранено: docs/diagrams/02-deploy-sequence.dot

digraph deploy_seq {
    rankdir=TB;
    splines=ortho;
    node [shape=box, style=rounded];
    ranksep=0.7;

    start [label="2.1 Проверить containerd\nctr version", shape=box, style=filled, fillcolor=lightblue];

    subgraph cluster_n7_setup {
        label="На узле n7 (через SSH)";
        install_ctr [label="2.1b Если нет →\napt install containerd.io", shape=box, style=filled, fillcolor=lightgreen];
        add_repo [label="2.2a Добавить репозиторий NVIDIA\ncurl -fsSL nvidia.github.io/...", shape=box, style=filled, fillcolor=lightblue];
        install_ctk [label="2.2b apt install\nnvidia-container-toolkit", shape=box, style=filled, fillcolor=lightgreen];
        ctk_cfg [label="2.3 nvidia-ctk runtime configure\n--runtime=containerd", shape=box, style=filled, fillcolor=lightblue];
        restart_ctr [label="2.4 systemctl restart containerd", shape=box, style=filled, fillcolor=lightblue];
        verify_ctk [label="Проверка nvidia в config.toml", shape=diamond, style=filled, fillcolor=lightyellow];
        verify_runtime [label="Проверка RuntimeClass:\nkubectl get runtimeclass", shape=box, style=filled, fillcolor=lightgreen];
        verify_gpu_k8s [label="Проверка GPU в K8s:\nkubectl describe node n7", shape=diamond, style=filled, fillcolor=lightyellow];
    }

    finish [label="✅ Этап 2 завершён\ncontainerd + nvidia-runtime\nGPU 2/2 в Capacity", shape=box, style=filled, fillcolor=green, fontcolor=white];
    fail_gpu_op [label="⚠️ GPU = 0\n→ GPU Operator не видит n7\n→ возврат к Этапу 1", shape=box, style=filled, fillcolor=red, fontcolor=white];

    start -> install_ctr [label="нет containerd"];
    start -> add_repo [label="containerd есть"];
    install_ctr -> add_repo;
    add_repo -> install_ctk;
    install_ctk -> ctk_cfg;
    ctk_cfg -> restart_ctr;
    restart_ctr -> verify_ctk;
    verify_ctk -> verify_runtime [label="✅ nvidia runtime в config"];
    verify_ctk -> ctk_cfg [label="❌ нет nvidia секции"];
    verify_runtime -> verify_gpu_k8s;
    verify_gpu_k8s -> finish [label="nvidia.com/gpu: 2"];
    verify_gpu_k8s -> fail_gpu_op [label="nvidia.com/gpu: 0"];
}
```

---

## Файлы в каталоге

| Файл | Описание |
|------|----------|
| `README.md` | Этот файл — описание, конфигурация, состояние, схемы |
| `docs/diagrams/02-containerd-nvidia-runtime.dot` | Схема компонентов и связей (DOT) |
| `docs/diagrams/02-deploy-sequence.dot` | Схема последовательности развёртывания (DOT) |
| `containerd-config-n7.toml` | Реальный `/etc/containerd/config.toml` с n7 |
| `manifests/runtimeclass-nvidia.yaml` | Манифест RuntimeClass для K8s |
