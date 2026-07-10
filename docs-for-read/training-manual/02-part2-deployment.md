# Часть II. Практическое развёртывание

**Документ 2 из 5.** 6 глав · ~140 стр. · 18 схем · 20 таблиц

> Пошаговый деплой всей системы: от голого железа до production.
> Каждая команда объяснена. Каждый манифест разобран построчно.

---

# Глава 8. Подготовка серверов и установка ОС

> **Цель:** подготовить серверы к работе — установить Astra Linux SE 1.8 через Kickstart, настроить сеть, SSH и драйверы NVIDIA.

---

## 8.1. Обзор инфраструктуры Aither

Прежде чем что-то устанавливать — карта того, с чем работаем.

### Пять узлов платформы

| Узел | IP | Роль | ОС | GPU | Доступ |
|---|---|---|---|---|---|
| **VPS1** | 170.168.91.95 (публ.) / 10.129.100.234 (WG) | Входная точка, nginx, Hermes | Ubuntu 24.04 | — | SSH :22, HTTPS :10443 |
| **VPS2** | 130.17.1.90 (публ.) / 10.99.0.2 (WG) | Портал, BFF, Portal DB | Ubuntu | — | SSH :22 (через WG), BMC-проброс :19443 |
| **Cisco 815** | 10.129.11.0/24 | VPN-терминатор, VLAN 308 | Cisco IOS | — | Консоль, SSH |
| **n8** | 40.51 / 10.129.13.78 | K8s control-plane + worker | Astra Linux SE 1.8 | 2× RTX 6000 | SSH :22, BMC :9443, K8s API :6443 |
| **n7** | 40.50 / 10.129.13.77 | K8s worker | Astra Linux SE 1.8 | 2× RTX 6000 | SSH :22, BMC :9443 |

**Сетевые туннели:**
- VPS1 ↔ VPS2: WireGuard (10.129.100.234 ↔ 10.99.0.2)
- VPS2 → Cisco 815: VPN tun1
- Cisco 815 → n7, n8: VLAN 308 (10.129.13.0/24)
- BMC n7: `:9443 → socat → VPS2:19443 → VPS1:443`

![Пять узлов платформы](diagrams/02-part2-deployment-01.jpg)

*Схема 8.1. Физическая схема всех 5 узлов с IP, портами и туннелями.*

---

## 8.2. Установка Astra Linux SE 1.8 через Kickstart

### Что такое Kickstart

Обычная установка ОС — диалог из 20 экранов: язык → раскладка → диск → пакеты → ... На одном сервере терпимо. На десяти — день работы.

**Kickstart** — текстовый файл с ответами на все вопросы установщика. Один раз написал → автоматическая установка на всех серверах.

### BMC: загрузка ISO удалённо

BMC (Baseboard Management Controller) — встроенный мини-компьютер, работающий даже при выключенном сервере. Через веб-интерфейс BMC можно смонтировать ISO-образ как виртуальный CD-ROM:

1. Заходим в BMC (через цепочку пробросов: VPS1:443 → VPS2:19443 → n7:9443)
2. Virtual Media → Choose File → выбираем ISO-образ Astra Linux
3. Power → Power On → во время загрузки F11 (Boot Menu) → Virtual CD/DVD

### Kickstart-файл ks-node01.cfg — построчный разбор

```bash
# ===== ЯЗЫК И РАСКЛАДКА =====
lang ru_RU.UTF-8
# ↑ Русский язык. UTF-8 — кодировка (кириллица).

keyboard ru
# ↑ Русская раскладка (для BMC-консоли).

timezone Europe/Moscow --isUtc
# ↑ Часовой пояс. --isUtc: аппаратные часы в UTC.

# ===== СЕТЬ =====
network --bootproto=static --device=eth0 \
  --ip=10.129.13.78 --netmask=255.255.255.0 \
  --gateway=10.129.13.1 --nameserver=10.129.13.1 \
  --hostname=bootsmam-k8s-clnt01-n8-gpu
# ↑ Статический IP (не DHCP). Все параметры заданы жёстко.
#   device=eth0 — какой интерфейс.
#   nameserver — обычно шлюз (он же DNS-сервер).

# ===== ПАРОЛЬ ROOT =====
rootpw --iscrypted $6$rounds=656000$...хэш...
# ↑ Пароль root в SHA-512. Генерируется:
#   python3 -c 'import crypt; print(crypt.crypt("password", crypt.mksalt(crypt.METHOD_SHA512)))'

# ===== РАЗМЕТКА ДИСКА =====
clearpart --all --initlabel
# ↑ Удалить ВСЕ существующие разделы.

part /boot --fstype=ext4 --size=1024
# ↑ /boot — загрузочный раздел, 1 GB.

part / --fstype=ext4 --size=102400
# ↑ / — корневой раздел, 100 GB (ОС + программы).

part /data --fstype=ext4 --size=1 --grow
# ↑ /data — раздел для моделей, --grow = занять всё оставшееся место.
#   При диске 42 TB /data получит ~41.9 TB.

bootloader --location=mbr --boot-drive=sda
# ↑ GRUB в MBR первого диска.

# ===== ПАКЕТЫ =====
%packages
@^server-product-environment      # группа «Сервер» (без GUI)
openssh-server                     # удалённый доступ
nano wget curl net-tools           # базовые утилиты
%end

# ===== ПОСТ-УСТАНОВКА (%post) =====
%post --log=/root/kickstart-post.log
# ↑ Всё между %post и %end выполнится после установки ОС.

systemctl enable sshd
# ↑ SSH-сервер будет запускаться при старте.

useradd -m -s /bin/bash admin
echo "admin:ChangeMe123" | chpasswd
usermod -aG wheel admin
# ↑ Создаём администратора. Группа wheel = sudo.

# ВАЖНО: отключаем Parsec (мандатный контроль доступа)
# Он блокирует драйверы NVIDIA и containerd.
sed -i 's/parsec=1/parsec=0/' /etc/default/grub
update-grub
# ↑ Меняем параметр ядра и обновляем GRUB.

mkdir -p /data/models
chown -R admin:admin /data
# ↑ Папка для моделей ИИ.

apt-get install -y chrony
systemctl enable chronyd
# ↑ Точное время критично для K8s (сертификаты, токены).
%end

reboot
```

> ⚠️ **Почему parsec=0.** Parsec — модуль мандатного контроля доступа в Astra Linux. Каждому файлу и процессу присваивается гриф секретности. Parsec блокирует: (1) загрузку драйверов NVIDIA; (2) запуск контейнеров (containerd не может создать cgroup); (3) некоторые сетевые операции. Параметр `parsec=0` в загрузчике отключает Parsec на уровне ядра. В промышленной эксплуатации Parsec настраивается политиками, а не отключается.

![Kickstart-файл ks-node01.cfg — построчный разбор](diagrams/02-part2-deployment-02.jpg)

*Схема 8.2. Процесс установки через Kickstart: ISO → BMC → загрузка → Kickstart → автоматическая установка → готовая ОС.*

---

## 8.3. Базовая настройка ОС

После установки заходим по SSH и настраиваем.

### Сеть

```bash
# Проверяем IP
ip a show eth0
# → inet 10.129.13.78/24

# Шлюз
ip route | grep default
# → default via 10.129.13.1

# DNS
cat /etc/resolv.conf
# → nameserver 10.129.13.1

# hostname
hostnamectl set-hostname bootsman-k8s-clnt01-n8-gpu

# Проверка связи с соседом
ping -c 2 10.129.13.77
```

### SSH

```bash
# /etc/ssh/sshd_config
Port 22
PermitRootLogin prohibit-password   # root только по ключу
PubkeyAuthentication yes
PasswordAuthentication no            # без паролей

systemctl restart sshd
```

### Брандмауэр (iptables)

```bash
iptables -A INPUT -p tcp --dport 22 -j ACCEPT        # SSH
iptables -A INPUT -p tcp --dport 6443 -j ACCEPT       # K8s API (n8)
iptables -A INPUT -p tcp --dport 30000:32767 -j ACCEPT # NodePort
iptables -A INPUT -p udp --dport 8472 -j ACCEPT       # Flannel VXLAN
iptables -A INPUT -i lo -j ACCEPT                     # localhost
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -P INPUT DROP                                 # остальное — запрет
```

### Системные настройки

```bash
timedatectl set-timezone Europe/Moscow
localectl set-locale LANG=ru_RU.UTF-8
# apt update/upgrade — осторожно в закрытом контуре (нет интернета!)
```

---

## 8.4. Установка драйверов NVIDIA

### Проверка GPU

```bash
lspci | grep -i nvidia
# → 01:00.0 3D controller: NVIDIA AD102 [RTX 6000]
# → 02:00.0 3D controller: NVIDIA AD102 [RTX 6000]
```

### Установка

```bash
apt-get install -y nvidia-driver nvidia-cuda-toolkit nvidia-smi
reboot
```

### nvidia-smi: разбор вывода

```bash
nvidia-smi
```

```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 550.90.07    Driver Version: 550.90.07    CUDA Version: 12.4     |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|===============================+======================+======================|
|   0  RTX 6000            Off  | 00000000:01:00.0 Off |                  Off |
| 30%   35C    P0    65W / 300W |      0MiB / 24576MiB |      0%      Default |
+-------------------------------+----------------------+----------------------+
|   1  RTX 6000            Off  | 00000000:02:00.0 Off |                  Off |
| 30%   35C    P0    65W / 300W |      0MiB / 24576MiB |      0%      Default |
+-------------------------------+----------------------+----------------------+
```

![nvidia-smi: разбор вывода](diagrams/02-part2-deployment-03.jpg)

*Схема 8.3. Разбор вывода nvidia-smi: драйвер, две карты, температура, энергопотребление, VRAM.*

### Дополнительные службы

```bash
systemctl enable nvidia-persistenced
systemctl start nvidia-persistenced
# ↑ Держит драйвер загруженным (без него — задержка при старте vLLM)

apt-get install -y nvidia-container-toolkit
# ↑ Пробрасывает драйверы внутрь контейнеров
#   Настройка containerd — в главе 9
```

---

## 8.5. ✏️ Практикум: голый сервер → готовая ОС

**Задание.** Опишите полный цикл подготовки сервера n7, от включения до `nvidia-smi`:

1. BMC: смонтировать ISO
2. Загрузиться и запустить Kickstart
3. После перезагрузки: проверить IP, DNS, hostname
4. Настроить SSH и iptables
5. Установить драйверы NVIDIA
6. Проверить `nvidia-smi` (две карты, 24 GB каждая)

---

# Глава 9. Развёртывание Kubernetes

> **Цель:** установить containerd, настроить GPU runtime, поднять кластер из двух узлов (n8 — control-plane, n7 — worker), настроить Flannel и GPU Operator.

---

## 9.1. containerd: установка и настройка

**containerd** — промышленная среда выполнения контейнеров. Kubernetes использует её через CRI (Container Runtime Interface).

### Установка

```bash
apt-get update
apt-get install -y containerd
containerd --version
# → containerd github.com/containerd/containerd v1.7.x
```

### Конфигурация

```bash
mkdir -p /etc/containerd
containerd config default > /etc/containerd/config.toml

# КРИТИЧНО: переключаем cgroup driver на systemd
sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
# ↑ Без этого kubelet не сможет управлять ресурсами подов

# Настройка NVIDIA runtime
nvidia-ctk runtime configure --runtime=containerd
# ↑ Добавляет секцию:
#   [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia]
#   runtime_type = "io.containerd.runc.v2"
#   [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia.options]
#   BinaryName = "/usr/bin/nvidia-container-runtime"

systemctl restart containerd
systemctl enable containerd
```

![Конфигурация](diagrams/02-part2-deployment-04.jpg)

*Схема 9.1. Архитектура containerd: kubelet → CRI → containerd → runc → контейнер. NVIDIA runtime — альтернативный путь для GPU.*

### Проверка

```bash
systemctl status containerd
crictl pull nginx:alpine
crictl images
# → nginx:alpine  ...  40MB
```

> 🔤 **crictl** — CLI для containerd (как `docker` для Docker). `crictl ps` = `docker ps`, `crictl images` = `docker images`, `crictl logs` = `docker logs`.

| Команда containerd | Аналог Docker |
|---|---|
| `crictl pull <img>` | `docker pull <img>` |
| `crictl ps` | `docker ps` |
| `crictl images` | `docker images` |
| `crictl logs <id>` | `docker logs <id>` |
| `crictl exec -it <id> sh` | `docker exec -it <id> sh` |
| `crictl rmi <img>` | `docker rmi <img>` |

---

## 9.2. kubeadm init: control-plane

### Установка kubeadm, kubelet, kubectl

```bash
apt-get install -y apt-transport-https ca-certificates curl gpg
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.33/deb/Release.key | \
  gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.33/deb/ /' \
  > /etc/apt/sources.list.d/kubernetes.list
apt-get update
apt-get install -y kubelet kubeadm kubectl
apt-mark hold kubelet kubeadm kubectl
```

> 🔤 **Три инструмента — три роли:** `kubeadm` (создаёт кластер), `kubelet` (агент на узле), `kubectl` (команды администратора).

### Инициализация

```bash
kubeadm init \
  --pod-network-cidr=10.244.0.0/16 \
  --apiserver-advertise-address=10.129.13.78 \
  --cri-socket=unix:///var/run/containerd/containerd.sock
```

![Инициализация](diagrams/02-part2-deployment-05.jpg)

*Схема 9.2. Временная диаграмма kubeadm init: 7 шагов за ~1 минуту.*

### Настройка kubectl

```bash
mkdir -p $HOME/.kube
cp /etc/kubernetes/admin.conf $HOME/.kube/config
chown $(id -u):$(id -g) $HOME/.kube/config

kubectl get nodes
# → bootsman-k8s-clnt01-n8-gpu   NotReady   control-plane   30s
```

| Команда | Назначение |
|---|---|
| `kubeadm init` | Создать control-plane |
| `kubeadm token create --print-join-command` | Создать токен для worker |
| `kubeadm reset` | Сбросить кластер (осторожно!) |
| `kubectl get nodes` | Список узлов |
| `kubectl get pods -A` | Все поды (все namespace) |

---

## 9.3. Flannel: overlay-сеть

```bash
kubectl apply -f https://raw.githubusercontent.com/flannel-io/flannel/master/Documentation/kube-flannel.yml
```

Что внутри манифеста:

```yaml
kind: ConfigMap
data:
  net-conf.json: |
    {
      "Network": "10.244.0.0/16",
      "Backend": {"Type": "vxlan"}
    }
---
kind: DaemonSet           # по одному экземпляру на каждом узле
spec:
  template:
    spec:
      containers:
      - name: kube-flannel
        image: flannelcni/flannel:v0.23.0
```

![9.3. Flannel: overlay-сеть]([Схема — ошибка рендеринга])

*Схема 9.3. Flannel VXLAN: IP-пакет от пода A заворачивается в VXLAN, идёт через физическую сеть, распаковывается и доставляется поду B.*

```bash
kubectl get nodes
# → n8   Ready   control-plane   2m
kubectl get pods -n kube-flannel
# → kube-flannel-ds-abc1   1/1   Running
```

---

## 9.4. kubeadm join: worker node

На **n7** выполняем команду, полученную при `kubeadm init`:

```bash
kubeadm join 10.129.13.78:6443 \
  --token abcdef.0123456789abcdef \
  --discovery-token-ca-cert-hash sha256:1234...abcd \
  --cri-socket=unix:///var/run/containerd/containerd.sock
```

Проверка на n8:
```bash
kubectl get nodes
# → n8   Ready   control-plane   5m
# → n7   Ready   <none>          30s
```

---

## 9.5. NVIDIA GPU Operator

```bash
helm repo add nvidia https://nvidia.github.io/gpu-operator
helm repo update
helm install gpu-operator nvidia/gpu-operator \
  --set driver.enabled=false \
  --set toolkit.enabled=true
```

![9.5. NVIDIA GPU Operator](diagrams/02-part2-deployment-07.jpg)

*Схема 9.4. Компоненты GPU Operator: Device Plugin (ресурс), Container Toolkit (доступ), DCGM (метрики).*

Проверка:
```bash
kubectl describe node n8 | grep nvidia.com/gpu
# → nvidia.com/gpu: 2
# → nvidia.com/gpu: 2
kubectl get pods -n gpu-operator
# → Все Running
```

---

## 9.6. Системные компоненты

```bash
# Metrics Server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl top nodes

# cert-manager (автоматические TLS-сертификаты)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml
```

### Системные поды kube-system

| Под | Назначение |
|---|---|
| `etcd-n8` | Хранилище состояния кластера |
| `kube-apiserver-n8` | Приём команд `kubectl` |
| `kube-controller-manager-n8` | Контроллеры (Deployment, Service, etc.) |
| `kube-scheduler-n8` | Планирование подов по узлам |
| `coredns-*` | DNS внутри кластера |
| `kube-proxy-*` | Сетевые правила на каждом узле |
| `metrics-server-*` | Сбор CPU/памяти (`kubectl top`) |

Финальная проверка:
```bash
kubectl get pods -A
# Все Running!
```

---

## 9.7. ✏️ Практикум: K8s с нуля

Повторите всю цепочку (можно на ВМ):
1. `apt install containerd` → `SystemdCgroup = true`
2. `apt install kubeadm kubelet kubectl`
3. `kubeadm init --pod-network-cidr=10.244.0.0/16`
4. `kubectl apply -f kube-flannel.yml`
5. `kubeadm join ...` (на втором узле)
6. `helm install gpu-operator`
7. `kubectl get nodes` → 2 узла Ready

### Словарь термина
- CRI, containerd, runc, crictl, SystemdCgroup
- kubeadm, kubelet, kubectl
- CNI, Flannel, VXLAN, DaemonSet
- GPU Operator, DCGM, device-plugin

---

# Глава 10. Развёртывание vLLM и моделей

> **Цель:** задеплоить 14B и 32B модели в K8s, подключить LoRA, проверить скорость.

---

## 10.1. Подготовка моделей

**Hugging Face** — крупнейший репозиторий моделей ИИ (как GitHub для кода, но для моделей). Каждая модель — это репозиторий с файлами весов, конфигурацией и токенизатором.

```bash
pip install huggingface_hub

# 14B (~28 GB)
huggingface-cli download Qwen/Qwen2.5-14B-Instruct \
  --local-dir /data/models/Qwen2.5-14B-Instruct

# 32B GPTQ (~20 GB)
huggingface-cli download Qwen/Qwen2.5-32B-Instruct-GPTQ-Int4 \
  --local-dir /data/models/Qwen2.5-32B-Instruct-GPTQ
```

![10.1. Подготовка моделей](diagrams/02-part2-deployment-08.jpg)

*Схема 10.1. Структура каталога модели HuggingFace.*

> 🔤 **safetensors** (Safe + Tensor) — безопасный формат: только числа, без исполняемого кода.

### Перенос в закрытый контур

```bash
tar -czf models.tar.gz -C /data/models Qwen2.5-14B-Instruct Qwen2.5-32B-Instruct-GPTQ
sha256sum models.tar.gz > checksum.txt
# → внешний диск → закрытый контур
sha256sum -c checksum.txt && tar -xzf models.tar.gz -C /data/models/
```

---

## 10.2. PVC и StorageClass

| Подход | Плюсы | Минусы | Для |
|---|---|---|---|
| hostPath | Прямой доступ = быстро | Привязан к узлу | 14B на n8 |
| PVC | Переносимый | Чуть медленнее | 32B на n7 |

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: models-32b-pvc
spec:
  accessModes: [ReadWriteOnce]
  resources: {requests: {storage: 100Gi}}
  storageClassName: local-path
```

![10.2. PVC и StorageClass](diagrams/02-part2-deployment-09.jpg)

*Схема 10.2. Цепочка PVC: Pod → PVC (запрос) → PV (хранилище) → физический диск.*

---

## 10.3. Деплой vLLM 14B

### Построчный разбор deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-qwen
spec:
  replicas: 1                      # один экземпляр
  strategy:
    type: Recreate                 # убить старый → запустить новый
                                   # (иначе deadlock GPU — см. гл. 3)

  selector:
    matchLabels:
      app: vllm-qwen

  template:
    metadata:
      labels:
        app: vllm-qwen

    spec:
      runtimeClassName: nvidia     # доступ к GPU
      nodeSelector:
        kubernetes.io/hostname: bootsman-k8s-clnt01-n8-gpu

      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        imagePullPolicy: IfNotPresent

        command: ["python3", "-m", "vllm.entrypoints.openai.api_server"]
        args:
          - --model /models/Qwen2.5-14B-Instruct
          - --dtype half
          - --max-model-len 4096
          - --gpu-memory-utilization 0.90
          - --tensor-parallel-size 2
          - --enable-lora
          - --lora-modules astra-14b=/models/lora-qwen14b-astra/
          - --max-lora-rank 8

        env:
        - name: HF_HUB_OFFLINE
          value: "1"               # не лезть в интернет
        - name: VLLM_PORT
          value: "8000"
        - name: NVIDIA_VISIBLE_DEVICES
          value: "0,1"             # обе карты

        ports:
        - containerPort: 8000

        resources:
          requests:
            cpu: "4"
            memory: 32Gi
            nvidia.com/gpu: "2"
          limits:
            cpu: "16"
            memory: 64Gi
            nvidia.com/gpu: "2"

        volumeMounts:
        - name: models
          mountPath: /models

      volumes:
      - name: models
        hostPath:
          path: /data/models
          type: DirectoryOrCreate
```

![Построчный разбор deployment.yaml](diagrams/02-part2-deployment-10.jpg)

*Схема 10.3. Аннотированная схема пода vLLM 14B: образ, аргументы, окружение, ресурсы, том.*

### Деплой и проверка

```bash
kubectl apply -f k8s/vllm-14b/deployment.yaml
kubectl apply -f k8s/vllm-14b/service.yaml

kubectl get pods -l app=vllm-qwen -w
# → ContainerCreating → Running → Ready

kubectl logs vllm-qwen-abc1 | tail -5
# → Model loaded in 45.2s
# → GPU memory: 18.4 GB / 24.0 GB (76.7%)
# → Application startup complete.

curl http://10.129.13.78:32293/health
# → OK

# Первый запрос (прогрев — 15-30 сек)
curl -X POST http://10.129.13.78:32293/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-14b","messages":[{"role":"user","content":"Привет!"}],"max_tokens":50}'
```

---

## 10.4. Деплой vLLM 32B (GPTQ)

```yaml
# Отличия от 14B (ключевые):
args:
  - --model /models                          # GPTQ: папка с весами
  - --served-model-name qwen2.5-32b          # имя в API
  - --host 0.0.0.0 --port 8000
  - --max-model-len 8192                     # вдвое больше контекст
  - --gpu-memory-utilization 0.90
  - --dtype auto                             # vLLM сам выберет
  - --tensor-parallel-size 2

volumes:
- name: models
  persistentVolumeClaim:
    claimName: models-32b-pvc               # PVC вместо hostPath
```

![10.4. Деплой vLLM 32B (GPTQ)](diagrams/02-part2-deployment-11.jpg)

*Схема 10.4. Отличия деплоя vLLM 32B от 14B.*

### Сравнение производительности

| Метрика | 14B (fp16) | 32B (GPTQ) |
|---|---|---|
| Размер на диске | 28 GB | 20 GB |
| VRAM (с KV-кэшем) | 18.4 GB | 22.1 GB |
| tok/s | ~28 | ~35 |
| Контекст | 4096 | 8192 |
| Качество | Хорошее | Отличное |

---

## 10.5. Подключение LoRA-адаптера

```bash
cp -r lora-qwen14b-astra/ /data/models/
kubectl rollout restart deploy/vllm-qwen
# Проверка:
curl http://10.129.13.78:32293/v1/models | jq '.data[] | select(.id=="astra-14b")'
# → {"id":"astra-14b","root":"qwen2.5-14b"}

# Тест:
curl ... -d '{"model":"astra-14b","messages":[...]}'
# → Более точный ответ с деталями Astra Linux
```

| Параметр LoRA | Значение |
|---|---|
| rank | 8 |
| alpha | 16 |
| Обучаемых параметров | ~65M |
| Размер файла | 65 MB |
| Целевые слои | q_proj, v_proj |

---

## 10.6. HPA для vLLM

```bash
kubectl apply -f k8s/hpa/hpa.yaml
kubectl get hpa
# → vllm-qwen-hpa   Deployment/vllm-qwen   44%/80%   1   max=1
```

Почему `max=1`? 2 GPU заняты одной репликой (TP=2). Масштабирование — только при добавлении GPU-узлов.

---

# Глава 11. Развёртывание Gateway

> **Цель:** собрать Docker-образ Gateway, задеплоить с PostgreSQL/Redis/ChromaDB, проверить биллинг и Rate Limiter.

---

## 11.1. Сборка Docker-образа Gateway

### Dockerfile — построчный разбор

```dockerfile
FROM python:3.12-slim
# ↑ Базовый образ: Python 3.12, облегчённый (slim = без компиляторов и документации).
#   Размер ~50 MB против ~900 MB у полного python:3.12.

WORKDIR /app
# ↑ Все следующие команды выполняются из /app.

COPY gateway/requirements.txt .
# ↑ Копируем ТОЛЬКО requirements.txt первым — чтобы закэшировать слой pip install.
#   Если копировать весь gateway/ сразу, pip install будет выполняться заново
#   при ЛЮБОМ изменении кода (даже если зависимости не менялись).

RUN pip install --no-cache-dir -r requirements.txt
# ↑ Устанавливаем Python-пакеты. --no-cache-dir: не хранить кэш pip
#   (экономия места в образе).

COPY gateway/ .
# ↑ Теперь копируем весь код (11 модулей). Этот слой будет пересобираться
#   при каждом изменении кода, но слой с pip install — нет (кэш).

RUN mkdir -p /app/wiki
# ↑ Папка для базы знаний RAG.

EXPOSE 8080
# ↑ Декларация: контейнер слушает порт 8080. Порт не открывается автоматически!

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python3 -c "import urllib.request; ..." || exit 1
# ↑ Проверка здоровья каждые 10 секунд.

CMD ["python3", "gateway.py"]
# ↑ Команда при запуске контейнера.
```

![Dockerfile — построчный разбор](diagrams/02-part2-deployment-12.jpg)

*Схема 11.1. Слои Docker-образа Gateway. Первые 4 слоя кэшируются, 5-й — нет.*

Сборка:
```bash
docker build -t ghcr.io/dedvmedved-dot/aither-project-gateway:latest -f gateway/Dockerfile .
docker run -d -p 8080:8080 --name gw-test -e PG_URL=... -e REDIS_URL=redis gateway:latest
curl http://localhost:8080/health
docker rm -f gw-test
```

---

## 11.2. Push в registry и деплой в K8s

```bash
# Публичный registry
echo "$GHCR_TOKEN" | docker login ghcr.io -u dedvmedved-dot --password-stdin
docker push ghcr.io/dedvmedved-dot/aither-project-gateway:latest

# ИЛИ локальный registry (закрытый контур)
docker run -d -p 5000:5000 --restart always --name registry registry:2
docker tag gateway:latest localhost:5000/gateway:latest
docker push localhost:5000/gateway:latest

# Деплой
kubectl create secret generic pg-url \
  --from-literal=url="postgresql://aither:***@postgres/aither"
kubectl apply -f k8s/gateway/deployment.yaml
kubectl apply -f k8s/gateway/service.yaml
kubectl wait --for=condition=Ready pod -l app=gateway --timeout=120s
```

---

## 11.3. ConfigMap и Secret — детально

| Ресурс | Содержимое | Создание |
|---|---|---|
| `gateway-catalog` | catalog.yaml (2 модели) | `kubectl create configmap ... --from-file=catalog.yaml` |
| `gateway-wiki` | wiki/index.md, llm-wiki.md | `kubectl create configmap ... --from-file=wiki/` |
| `delegation-public-key` | delegation/public.pem | `kubectl create configmap ... --from-file=delegation/public.pem` |
| `pg-url` (Secret) | postgresql://... | `kubectl create secret generic pg-url --from-literal=url=...` |

Обновление без пересоздания:
```bash
kubectl create configmap gateway-catalog --from-file=catalog.yaml --dry-run=client -o yaml | kubectl apply -f -
kubectl rollout restart deploy/gateway
```

---

## 11.4. Переменные окружения — каждая с объяснением

| Переменная | Значение | Зачем |
|---|---|---|
| `VLLM_URL` | `http://vllm:8000` | K8s Service 14B (DNS-имя внутри кластера) |
| `VLLM_32B_URL` | `http://vllm-qwen32b:8000` | K8s Service 32B |
| `CATALOG_PATH` | `/app/catalog.yaml` | Где смонтирован ConfigMap с каталогом |
| `REDIS_URL` | `redis` | K8s Service Redis (порт 6379 — умолчание) |
| `RATE_LIMIT_RPM` | `300` | Максимум запросов в минуту на организацию |
| `RATE_LIMIT_TPM` | `100000` | Максимум токенов в минуту на организацию |
| `PORT` | `8080` | Порт HTTP-сервера |
| `TOKEN_COST` | `*** | Коэффициент токен → рубли |
| `CHROMA_URL` | `http://chromadb:8000` | K8s Service ChromaDB (RAG) |
| `WIKI_ROOT` | `/app/wiki` | Папка с базой знаний |
| `PG_URL` | Secret `pg-url` | URL базы данных биллинга |
| `ADMIN_KEY` | `admin-388b...` | Ключ супер-админа |

---

## 11.5. Rate Limiter и биллинг — проверка

### RPM

```bash
for i in $(seq 301); do
  code=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer *** \
    -d '{"model":"qwen2.5-14b","messages":[{"role":"user","content":"t"}],"max_tokens":1}' \
    http://gateway:8080/v1/chat/completions)
  echo "$i: $code"
done | tail -3
# → 299: 200
# → 300: 200
# → 301: 429  ← Too Many Requests
```

![RPM](diagrams/02-part2-deployment-13.jpg)

*Схема 11.2. Rate Limiter: Redis хранит счётчики RPM/TPM, при превышении — 429.*

### Биллинг

```bash
curl ... -H "Authorization: Bearer *** -d '{"model":"qwen2.5-14b","messages":[...]}'
# Проверка ДО и ПОСЛЕ:
kubectl exec -it deploy/postgres -- psql -U aither -d aither \
  -c "SELECT org_id, balance, tokens_used FROM billing_accounts WHERE org_id='abc-123';"
# ДО:  balance=10000, tokens_used=0
# ПОСЛЕ: balance=9950, tokens_used=50  ← списалось!
```

---

## 11.6. HPA Gateway

```yaml
# k8s/hpa/gateway-hpa.yaml
spec:
  scaleTargetRef: {kind: Deployment, name: gateway}
  minReplicas: 1
  maxReplicas: 3
  metrics:
  - type: External
    external:
      metric: {name: gateway_active_requests}
      target: {type: AverageValue, averageValue: "5"}
  - type: External
    external:
      metric: {name: gateway_requests_per_second}
      target: {type: AverageValue, averageValue: "10"}
  behavior:
    scaleDown: {stabilizationWindowSeconds: 300}   # 5 мин
    scaleUp:   {stabilizationWindowSeconds: 60}     # 1 мин
```

```bash
kubectl apply -f k8s/hpa/gateway-hpa.yaml
kubectl get hpa
# → gateway-hpa   Deployment/gateway   1%/70%   1   max=3

# Нагрузочный тест
hey -n 100 -c 10 -m POST -H "Authorization: Bearer ..." \
  -d '{"model":"qwen2.5-14b","messages":[...]}' \
  http://gateway:8080/v1/chat/completions

kubectl get hpa -w  # наблюдаем масштабирование
```

![11.6. HPA Gateway](diagrams/02-part2-deployment-14.jpg)

*Схема 11.3. Gateway в K8s: Deployment + HPA + Pod (образ + тома + переменные) + Service.*

---

## 11.7. ✏️ Практикум: Gateway от сборки до прода

1. `docker build -t gateway .` → `docker run` → `curl /health`
2. `docker push` → `kubectl apply` → `kubectl wait`
3. `curl /v1/chat/completions` → проверка списания токенов
4. 301 запрос → проверка 429

| Команда Docker | Назначение |
|---|---|
| `docker build -t name .` | Собрать образ |
| `docker run -d -p 8080:8080 name` | Запустить контейнер |
| `docker push name` | Отправить в registry |
| `docker save/load` | Сохранить/загрузить в файл |

---

# Глава 12. Развёртывание в закрытом контуре — air-gap

> **Цель:** развернуть всю платформу в сети без Интернета через пакет offline-deploy v1.1.0 и Ansible.

---

## 12.1. Пакет offline-deploy — обзор

```
offline-deploy/
├── README.md          ← инструкция для принимающей стороны
├── VERSION            ← 1.1.0
├── Makefile           ← make bundle / deploy / test / verify
├── CHANGELOG.md       ← история версий
├── docs/              ← 8 документов (архитектура, деплой, админ, ...)
├── playbooks/         ← 10 Ansible playbooks
├── k8s/               ← манифесты (gateway, vllm, postgres, redis, chromadb, hpa)
├── offline/           ← зависимости (docker save/load, pip download, npm pack)
├── scripts/           ← эксплуатация (backup, restore, rotate-keys, health-check)
├── configs/           ← шаблоны (nginx, bff, gateway, vllm)
└── tests/             ← приёмо-сдаточные (smoke, api, security, load)
```

![12.1. Пакет offline-deploy — обзор](diagrams/02-part2-deployment-15.jpg)

*Схема 12.1. Структура пакета offline-deploy: 7 каталогов с определёнными ролями.*

### Makefile: ключевые цели

| Команда | Действие |
|---|---|
| `make bundle` | Собрать ВСЕ офлайн-зависимости в один архив |
| `make offline-load` | Загрузить зависимости на целевую машину |
| `make deploy` | `ansible-playbook site.yml` |
| `make test` | Приёмо-сдаточные тесты |
| `make verify` | Проверка контрольных сумм |

---

## 12.2. Сборка офлайн-пакета (на машине с интернетом)

### offline/docker/save.sh — построчно

```bash
#!/bin/bash
# Читаем список образов
IMAGES=$(cat offline/docker/images.txt)

# Скачиваем каждый образ
for img in $IMAGES; do
  docker pull $img
done

# Сохраняем ВСЕ образы в ОДИН tar.gz
docker save $IMAGES | gzip > offline/docker/images.tar.gz
# → ~10 GB для postgres, redis, vllm/vllm-openai, chromadb, prometheus, grafana, nginx
```

### offline/pip/download.sh — построчно

```bash
#!/bin/bash
mkdir -p offline/pip/packages
pip download -d offline/pip/packages/ -r offline/pip/requirements.txt
# → ~50 MB файлов .whl
```

### checksums.sha256

```bash
cd offline
find . -type f ! -name checksums.sha256 -exec sha256sum {} \; > checksums.sha256
# Каждая строка: <хэш>  <путь/к/файлу>
```

![checksums.sha256](diagrams/02-part2-deployment-16.jpg)

*Схема 12.2. Процесс сборки и загрузки: 7 шагов от docker pull до pip install.*

---

## 12.3. Перенос на носитель → целевая машина

### Носители

| Тип | Ёмкость | Скорость | Для |
|---|---|---|---|
| USB-флешка | 32-256 GB | ~50 MB/s | Мелкие пакеты |
| Внешний HDD | 1-5 TB | ~100 MB/s | Модели + пакет |
| Внешний SSD | 1-4 TB | ~500 MB/s | Быстрый перенос |
| Оптический BD-R | 50 GB | ~20 MB/s | ГОСТ-режим |

### Перенос

```bash
rsync -av --progress offline-deploy/ /mnt/usb/offline-deploy/
umount /mnt/usb
# Физический перенос носителя в закрытый контур
mount /dev/sdb1 /mnt/usb

# ПРОВЕРКА ЦЕЛОСТНОСТИ (обязательно!)
cd /mnt/usb/offline-deploy/offline
sha256sum -c checksums.sha256
# → ВСЕ должны быть OK. Если хоть один FAILED — копировать заново!
```

---

## 12.4. Загрузка зависимостей

### offline/docker/load.sh — построчно

```bash
#!/bin/bash
# Загружаем образы из архива
docker load -i offline/docker/images.tar.gz

# Пушим каждый в локальный registry
REGISTRY=localhost:5000
IMAGES=$(cat offline/docker/images.txt)
for img in $IMAGES; do
  docker tag $img $REGISTRY/$img
  docker push $REGISTRY/$img
done
```

### offline/pip/install.sh

```bash
#!/bin/bash
pip install --no-index --find-links=offline/pip/packages/ -r offline/pip/requirements.txt
```

---

## 12.5. Ansible playbooks — мастер-класс

![12.5. Ansible playbooks — мастер-класс](diagrams/02-part2-deployment-17.jpg)

*Схема 12.3. Граф зависимостей Ansible playbook-ов: строго последовательно, каждый зависит от предыдущего.*

### 01-prerequisites.yml (пример)

```yaml
- name: Подготовка ОС
  hosts: all
  tasks:
    - name: Установка пакетов
      apt:
        name:
          - openssh-server
          - curl
          - wget
          - nano
          - net-tools
          - chrony
        state: present          # идемпотентность!
    - name: Часовой пояс
      timezone: {name: Europe/Moscow}
    - name: SSH
      systemd: {name: sshd, enabled: yes, state: started}
    - name: Брандмауэр
      iptables:
        chain: INPUT
        protocol: tcp
        destination_port: "22"
        jump: ACCEPT
```

### 06-gateway-deploy.yml (пример)

```yaml
- name: Деплой Gateway
  hosts: n7
  tasks:
    - name: Загрузить образ в registry
      command: docker push localhost:5000/gateway:latest
    - name: Secret с URL БД
      shell: |
        kubectl create secret generic pg-url \
          --from-literal=url={{ pg_url }} \
          --dry-run=client -o yaml | kubectl apply -f -
    - name: Применить манифесты
      command: kubectl apply -f /opt/offline-deploy/k8s/gateway/
    - name: Ждать готовности
      command: kubectl wait --for=condition=Ready pod -l app=gateway --timeout=120s
```

---

## 12.6. Приёмо-сдаточные тесты

![12.6. Приёмо-сдаточные тесты](diagrams/02-part2-deployment-18.jpg)

*Схема 12.4. Блок-схема приёмо-сдаточных испытаний: 4 теста, PASS/FAIL.*

### 01-smoke.sh — построчно

```bash
#!/bin/bash
echo "=== Smoke Test ==="

# Все поды Running?
kubectl get pods -A | grep -v Running | grep -v NAMESPACE && echo "FAIL" && exit 1

# Gateway
curl -sf http://gateway:8080/health || { echo "FAIL: Gateway"; exit 1; }

# vLLM
curl -sf http://vllm:8000/health || { echo "FAIL: vLLM 14B"; exit 1; }
curl -sf http://vllm-qwen32b:8000/health || { echo "FAIL: vLLM 32B"; exit 1; }

echo "PASS: All services healthy"
```

---

## 12.7. Чек-лист развёртывания

| Шаг | Действие | Ожидаемый результат |
|---|---|---|
| 1 | Вставить флешку | `mount /dev/sdb1 /mnt/usb` |
| 2 | Проверить суммы | `sha256sum -c checksums.sha256` → все OK |
| 3 | Загрузить зависимости | `make offline-load` → все образы в registry |
| 4 | Настроить inventory | `vim playbooks/inventory.yml` |
| 5 | Запустить деплой | `make deploy` → 9 playbook-ов PASS |
| 6 | Приёмо-сдаточные | `make test` → 4 теста PASS |
| 7 | Создать админа | `bash scripts/create-admin.sh` |
| 8 | Открыть портал | Браузер → `https://IP:10443` → чат |
| 9 | Первый запрос | «Привет!» → ответ модели |
| 10 | Подписать акт | Чек-лист → подписи |

![12.7. Чек-лист развёртывания](diagrams/02-part2-deployment-19.jpg)

*Схема 12.5. Полная карта air-gap деплоя: от интернет-машины до готовой платформы.*

---

# Глава 13. Мониторинг и эксплуатация

> **Цель:** настроить Prometheus + Grafana, логи, бэкапы, ротацию ключей.

---

## 13.1. Что мониторим и зачем

| Категория | Метрики | Порог тревоги |
|---|---|---|
| **GPU** | Температура (°C), загрузка (%), VRAM (GB), throttle | >85°C, VRAM >95% |
| **vLLM** | requests/sec, latency (p50/p95/p99), tokens/sec | p95 > 5s |
| **Gateway** | RPM, TPM, active_requests, 429 count | RPM > 250 |
| **Биллинг** | Балансы организаций, списания/мин | Баланс < 0 |
| **Инфраструктура** | CPU (%), RAM (GB), диск (%), сеть (MB/s) | RAM > 90% |

---

## 13.2. Prometheus + Grafana — настройка

```yaml
# prometheus.yml (scrape_configs)
- job_name: 'gateway'
  static_configs:
    - targets: ['gateway:8080']
- job_name: 'vllm'
  static_configs:
    - targets: ['vllm:8000', 'vllm-qwen32b:8000']
- job_name: 'node'
  static_configs:
    - targets: ['n8:9100', 'n7:9100']
- job_name: 'gpu'
  static_configs:
    - targets: ['n8:9400', 'n7:9400']
```

Ключевые метрики DCGM:
- `DCGM_FI_DEV_GPU_UTIL` — загрузка GPU (%)
- `DCGM_FI_DEV_GPU_TEMP` — температура (°C)
- `DCGM_FI_DEV_FB_USED` — использование VRAM
- `DCGM_FI_DEV_MEM_COPY_UTIL` — утилизация шины памяти

![13.2. Prometheus + Grafana — настройка]([Схема — ошибка рендеринга])

*Схема 13.1. Архитектура мониторинга: 4 источника → Prometheus → Grafana + AlertManager.*

---

## 13.3. Логи: где и как читать

| Источник | Команда | Пример |
|---|---|---|
| systemd | `journalctl -u <unit>` | `journalctl -u kubelet -p 3 --since "1h"` |
| Контейнеры | `kubectl logs <pod>` | `kubectl logs -f deploy/gateway --tail=100` |
| Все поды | `kubectl logs -l app=X` | `kubectl logs -l app=vllm-qwen --all-containers` |
| Предыдущий | `--previous` | `kubectl logs --previous vllm-abc1` |

| Ошибка | Причина | Решение |
|---|---|---|
| `OOMKilled` | Превышен `limits.memory` | Увеличить `limits.memory` |
| `CrashLoopBackOff` | Ошибка в команде/аргументах | `kubectl logs` → исправить |
| `ImagePullBackOff` | Образ не найден | Проверить `image:` и registry |
| `CreateContainerConfigError` | Ошибка в ConfigMap/Secret | Проверить имена и ключи |
| `insufficient nvidia.com/gpu` | Нет свободных GPU | Ждать или уменьшить запрос |

---

## 13.4. Резервное копирование

![13.4. Резервное копирование](diagrams/02-part2-deployment-21.jpg)

*Схема 13.2. Потоки резервного копирования: БД → pg_dump, модели → rsync, конфиги → git push.*

```bash
# Ежедневный бэкап
#!/bin/bash
DATE=$(date +%Y%m%d)
kubectl exec -it deploy/postgres -- pg_dump -U aither -d aither > /backup/gateway-$DATE.sql
ssh root@130.17.1.90 "pg_dump -U aither -d aither" > /backup/portal-$DATE.sql
rsync -av /data/models/ /backup/models/
cd /root/aither-project && git add -A && git commit -m "backup: $DATE" && git push
ls -t /backup/*.sql | tail -n +8 | xargs rm -f   # только 7 последних
```

---

## 13.5. Ротация ключей и сертификатов

```bash
#!/bin/bash
# rotate-keys.sh
NEW_SECRET=$(openssl rand -base64 64)
kubectl create secret generic jwt-secret \
  --from-literal=secret="$NEW_SECRET" --dry-run=client -o yaml | kubectl apply -f -
kubectl rollout restart deploy/gateway

echo "JWT_SECRET=$NEW_SECRET" | ssh root@130.17.1.90 \
  "tee -a /opt/aither/.env && systemctl restart aither-bff"
```

Сертификаты TLS: cert-manager автообновляет. Ручной режим: `openssl req -x509 -nodes -days 365 -newkey rsa:2048 ...`

---

## 13.6. ✏️ Практикум: инцидент

**Сценарий:** «Пользователи жалуются — модель не отвечает».

1. Открыть Grafana → GPU Overview: GPU-Util = 0%
2. `kubectl get pods` → vLLM в CrashLoopBackOff
3. `kubectl logs vllm-abc1 --previous` → `CUDA out of memory`
4. Причина: `--gpu-memory-utilization 0.95` (слишком много)
5. Исправить: `kubectl edit deploy vllm-qwen` → 0.95 → 0.85
6. `kubectl rollout restart` → под Running → модель отвечает

---

**Часть II завершена: ~140 стр., 18 схем, 20 таблиц.**