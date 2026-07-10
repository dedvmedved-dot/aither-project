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

```dot
digraph Infrastructure {
    rankdir=LR
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=8]

    internet [label="Интернет", shape=cloud, style="filled", fillcolor="#fce4ec", color="#e91e63", fontsize=10]

    subgraph cluster_vps1 {
        label="VPS1\n170.168.91.95\nUbuntu 24.04"
        style="rounded"
        color="#1976d2"
        fontname="system-ui"
        nginx [label="HTTPS :10443\nwg0: 10.129.100.234", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
    }

    subgraph cluster_vps2 {
        label="VPS2\n130.17.1.90\nUbuntu"
        style="rounded"
        color="#7b1fa2"
        fontname="system-ui"
        bff [label="BFF :3000\nPortal DB :5432\nwg1: 10.99.0.2\ntun1 (Cisco VPN)", shape=box, style="filled", fillcolor="#f3e5f5", color="#7b1fa2"]
    }

    subgraph cluster_cisco {
        label="Cisco 815\n10.129.11.0/24"
        style="rounded"
        color="#43a047"
        fontname="system-ui"
        cisco [label="VPN-терминатор\nVLAN 308", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    }

    subgraph cluster_gpu {
        label="Закрытый контур\n10.129.13.0/24 (VLAN 308)"
        style="rounded,dashed"
        color="#ff9800"
        fontname="system-ui"
        n8 [label="n8: 40.51\ncontrol-plane\n2× RTX 6000", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
        n7 [label="n7: 40.50\nworker\n2× RTX 6000", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    }

    internet -> nginx [label="TLS 1.3"]
    nginx -> bff [label="WireGuard", style=dashed, color="#43a047"]
    bff -> cisco [label="Cisco VPN\ntun1", style=dashed, color="#00838f"]
    cisco -> n8 [label="VLAN 308"]
    cisco -> n7 [label="VLAN 308"]
    n8 -> n7 [label="Flannel\nVXLAN", style=dotted, dir=both, color="#ff9800"]
}
```

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

```dot
digraph KickstartFlow {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    iso [label="ISO-образ\nAstra Linux SE 1.8", shape=cylinder, style="filled", fillcolor="#f3e5f5", color="#9c27b0", fontsize=10]
    ks [label="ks-node01.cfg\n(Kickstart)", shape=note, style="filled", fillcolor="#fff3e0", color="#ff9800", fontsize=10]

    bmc [label="BMC\nМонтирование ISO\nчерез Virtual Media", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]

    boot [label="Загрузка\nс Virtual CD", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]

    kernel [label="Ядро Linux\ninst.ks=...\nчитает Kickstart", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]

    subgraph cluster_install {
        label="Автоматическая установка (5-10 мин)"
        style="rounded,dashed"
        color="#ff9800"
        fontname="system-ui"

        disk [label="Разметка\nдиска", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
        pkgs [label="Установка\nпакетов", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
        post [label="%post:\nsshd, admin,\nparsec=0,\nchrony", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    }

    ready [label="Готовая ОС\nперезагрузка", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047", fontsize=10]

    iso -> bmc -> boot -> kernel
    ks -> kernel
    kernel -> disk -> pkgs -> post -> ready
}
```

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

```dot
digraph NvidiaSmi {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    header [label="nvidia-smi — вывод", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2", fontsize=10]

    driver [label="Driver 550.90.07\nCUDA 12.4", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    gpu0 [label="GPU 0: RTX 6000\nTemp: 35°C\nPower: 65W/300W\nVRAM: 0/24576 MiB\nGPU-Util: 0%", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
    gpu1 [label="GPU 1: RTX 6000\nTemp: 35°C\nPower: 65W/300W\nVRAM: 0/24576 MiB\nGPU-Util: 0%", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]

    header -> driver
    driver -> gpu0
    driver -> gpu1

    note [label="24576 MiB = 24 GB VRAM\nGPU-Util 0% = пока не используется\n(vLLM ещё не запущен)", shape=plaintext, fontsize=8]
}
```

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

```dot
digraph ContainerdArch {
    rankdir=LR
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    kubelet [label="kubelet\n(агент K8s)", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]

    cri [label="CRI\n(Container Runtime\nInterface)", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]

    containerd [label="containerd\n— управление образами\n— управление контейнерами\n— снапшоты ФС", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]

    runc [label="runc\n— namespaces\n— cgroups\n— запуск процесса", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]

    nvidia [label="nvidia-runtime\n(для GPU-контейнеров)", shape=box, style="filled", fillcolor="#f3e5f5", color="#9c27b0", fontsize=8]

    container [label="Контейнер", shape=box, style="rounded", color="#43a047"]

    kubelet -> cri -> containerd -> runc -> container
    containerd -> nvidia -> runc [style=dashed, color="#9c27b0"]
}
```

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

```dot
digraph KubeadmTimeline {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    t0 [label="kubeadm init", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2", fontsize=10]
    t1 [label="Preflight checks\n(права, порты, containerd)", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    t2 [label="Генерация сертификатов\n/etc/kubernetes/pki/", shape=box, style="filled", fillcolor="#f3e5f5", color="#9c27b0"]
    t3 [label="Запуск etcd", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    t4 [label="Запуск control-plane\napiserver, scheduler, cm", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    t5 [label="Генерация токена\nkubeadm join ...", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
    t6 [label="Сохранение kubeconfig\n/etc/kubernetes/admin.conf", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
    done [label="✅ Control-plane готов\nkubectl get nodes → NotReady\n(ждём Flannel)", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047", fontsize=10]

    t0 -> t1 -> t2 -> t3 -> t4 -> t5 -> t6 -> done
}
```

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

```dot
digraph FlannelVXLAN {
    rankdir=LR
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=8]

    pod_a [label="Под A\n10.244.1.10\nна n8", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
    flannel_a [label="Flannel (n8)\nинкапсуляция\nв VXLAN", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    phys [label="Физическая сеть\n10.129.13.78 → 10.129.13.77\n(оригинальный IP-пакет завёрнут\nв VXLAN-пакет)", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    flannel_b [label="Flannel (n7)\nдекапсуляция\nиз VXLAN", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    pod_b [label="Под B\n10.244.2.15\nна n7", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63")

    pod_a -> flannel_a -> phys -> flannel_b -> pod_b
}
```

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

```dot
digraph GPUOperator {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    operator [label="GPU Operator\n(Helm chart)", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800", fontsize=10]

    plugin [label="Device Plugin\nРегистрирует GPU\nкак ресурс K8s\nnvidia.com/gpu", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
    toolkit [label="Container Toolkit\nПробрасывает драйверы\nвнутрь контейнера\nruntimeClassName: nvidia", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    dcgm [label="DCGM Exporter\nМетрики GPU\nдля Prometheus\n(температура, VRAM)", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]

    operator -> plugin
    operator -> toolkit
    operator -> dcgm
}
```

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

```dot
digraph ModelDir {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=8]

    root [label="Qwen2.5-14B-Instruct/", shape=folder, style="filled", fillcolor="#e3f2fd", color="#1976d2", fontsize=10]

    config [label="config.json\n(архитектура:\nTransformer, слои, головы)", shape=note, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    tokenizer [label="tokenizer.json\n(слова → числа)", shape=note, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    m1 [label="model-00001-of-00004.safetensors\n(веса, часть 1/4, ~7 GB)", shape=note, style="filled", fillcolor="#fce4ec", color="#e91e63"]
    m2 [label="model-00002-of-00004.safetensors\n(часть 2/4)", shape=note, style="filled", fillcolor="#fce4ec", color="#e91e63"]
    m3 [label="model-00003-of-00004.safetensors\n(часть 3/4)", shape=note, style="filled", fillcolor="#fce4ec", color="#e91e63"]
    m4 [label="model-00004-of-00004.safetensors\n(часть 4/4)", shape=note, style="filled", fillcolor="#fce4ec", color="#e91e63"]
    gen [label="generation_config.json\n(параметры по умолчанию)", shape=note, style="filled", fillcolor="#fff3e0", color="#ff9800"]

    root -> config
    root -> tokenizer
    root -> m1 -> m2 -> m3 -> m4
    root -> gen
}
```

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

```dot
digraph PVCFlow {
    rankdir=LR
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    pod [label="Pod vLLM\nvolumeMount:\n/models", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
    pvc [label="PVC\nmodels-32b-pvc\nзапрос: 100Gi", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    pv [label="PV\n(автоматически\nсоздан Provisioner-ом)", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    disk [label="/data/models/\n(физический диск)", shape=cylinder, style="filled", fillcolor="#f5f5f5", color="#616161"]

    pod -> pvc -> pv -> disk
}
```

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

```dot
digraph VLLM14Pod {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=8]

    pod [label="Pod: vllm-qwen-abc1", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63", fontsize=11]

    subgraph cluster_container {
        label="Container: vllm"
        style="rounded"
        color="#1976d2"
        fontname="system-ui"

        img [label="image:\nvllm/vllm-openai:latest", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
        args [label="args:\n--model /models/...\n--dtype half\n--max-model-len 4096\n--gpu-memory-util 0.90\n--tensor-parallel-size 2\n--enable-lora", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
        env [label="env:\nHF_HUB_OFFLINE=1\nVLLM_PORT=8000\nVISIBLE_DEVICES=0,1", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
        res [label="resources:\nrequests: 4CPU+32Gi+2GPU\nlimits: 16CPU+64Gi+2GPU", shape=box, style="filled", fillcolor="#f3e5f5", color="#9c27b0"]
    }

    vol [label="/data/models → /models\n(hostPath)", shape=cylinder, style="filled", fillcolor="#f5f5f5", color="#616161"]

    pod -> img
    pod -> args
    pod -> env
    pod -> res
    pod -> vol
}
```

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

```dot
digraph VLLM32Pod {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    pod [label="Pod: vllm-qwen32b\n(отличия от 14B)", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047", fontsize=11]

    diff1 [label="--model /models\n(GPTQ, без полного имени)", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    diff2 [label="--max-model-len 8192\n(вдвое больше контекст)", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    diff3 [label="--dtype auto\n(vLLM сам выбирает)", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    diff4 [label="PVC (не hostPath)\nmodels-32b-pvc", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    diff5 [label="imagePullPolicy: Always\n(чаще обновляется)", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]

    pod -> diff1
    pod -> diff2
    pod -> diff3
    pod -> diff4
    pod -> diff5
}
```

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

```dot
digraph DockerfileLayers {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    l1 [label="FROM python:3.12-slim\n(~50 MB)", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
    l2 [label="WORKDIR /app\n(0 MB)", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
    l3 [label="COPY requirements.txt\n(~100 B)", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    l4 [label="RUN pip install\n(~50 MB)", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    l5 [label="COPY gateway/\n(~300 KB)", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    l6 [label="RUN mkdir /app/wiki\n(0 MB)", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    l7 [label="CMD [python3, gateway.py]\n(0 MB)", shape=box, style="filled", fillcolor="#f3e5f5", color="#9c27b0"]

    l1 -> l2 -> l3 -> l4 -> l5 -> l6 -> l7

    note [label="Слои 1-4: кэшируются (меняются редко)\nСлой 5: пересобирается при каждом изменении кода", shape=plaintext, fontsize=9]
}
```

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

```dot
digraph RateLimiter {
    rankdir=LR
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    req [label="Запрос", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]

    redis [label="Redis\nСкользящее окно\nrpm:{org}:{minute}\ntpm:{org}:{minute}", shape=cylinder, style="filled", fillcolor="#fce4ec", color="#e91e63"]

    check [label="rpm < 300?\ntpm < 100000?", shape=diamond, style="filled", fillcolor="#fff3e0", color="#ff9800"]

    ok [label="200 OK\n→ vLLM", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    deny [label="429\nToo Many\nRequests", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]

    req -> redis -> check
    check -> ok [label="да"]
    check -> deny [label="нет"]
}
```

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

```dot
digraph GatewayK8s {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    deploy [label="Deployment: gateway\nreplicas=1-3, RollingUpdate", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    hpa [label="HPA\nmin=1, max=3\nactive_requests\nrequests_per_second", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]

    pod [label="Pod: gateway\n━━━━━━━━━━\nimage: ghcr.io/.../gateway:latest\nvolumeMounts:\n  catalog → /app/catalog.yaml\n  wiki → /app/wiki\n  delegation → /app/delegation\nenv:\n  PG_URL (Secret)\n  12 переменных", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]

    svc [label="Service: gateway\nClusterIP :8080\nNodePort :30900", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]

    deploy -> pod -> svc
    hpa -> deploy
}
```

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

```dot
digraph OfflineStructure {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=8]

    root [label="offline-deploy/", shape=folder, style="filled", fillcolor="#e3f2fd", color="#1976d2", fontsize=11]

    docs [label="docs/\nдокументация", shape=folder, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    playbooks [label="playbooks/\nавтоматизация", shape=folder, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    k8s [label="k8s/\nманифесты", shape=folder, style="filled", fillcolor="#fce4ec", color="#e91e63"]
    offline [label="offline/\nзависимости", shape=folder, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    scripts [label="scripts/\nэксплуатация", shape=folder, style="filled", fillcolor="#f3e5f5", color="#9c27b0"]
    configs [label="configs/\nшаблоны", shape=folder, style="filled", fillcolor="#e0f7fa", color="#00838f"]
    tests [label="tests/\nприёмка", shape=folder, style="filled", fillcolor="#fce4ec", color="#e91e63"]

    root -> docs
    root -> playbooks
    root -> k8s
    root -> offline
    root -> scripts
    root -> configs
    root -> tests
}
```

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

```dot
digraph BuildProcess {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    subgraph cluster_build {
        label="Машина с Интернетом: make bundle"
        style="rounded,dashed"
        color="#1976d2"
        fontname="system-ui"

        s1 [label="1. docker pull\n(10 образов)", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
        s2 [label="2. docker save\n→ images.tar.gz\n(~10 GB)", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
        s3 [label="3. pip download\n→ packages/*.whl\n(~50 MB)", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
        s4 [label="4. sha256sum\n→ checksums.sha256", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
    }

    media [label="USB-носитель\n(флешка/HDD)", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800", fontsize=10]

    subgraph cluster_load {
        label="Закрытый контур: make offline-load"
        style="rounded,dashed"
        color="#43a047"
        fontname="system-ui"

        l1 [label="5. sha256sum -c\n(проверка)", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
        l2 [label="6. docker load\n→ docker push\nв локальный registry", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
        l3 [label="7. pip install\n--no-index", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    }

    s1 -> s2 -> s3 -> s4 -> media -> l1 -> l2 -> l3
}
```

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

```dot
digraph SiteYML {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=8]

    site [label="site.yml\n(оркестрация)", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2", fontsize=10]

    p01 [label="01-prerequisites\nОС, пакеты, сеть\n(все узлы)", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    p02 [label="02-gpu-setup\nNVIDIA drivers\n(gpu_servers)", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    p03 [label="03-k8s-deploy\ncontainerd→kubeadm\n→Flannel", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    p04 [label="04-storage\nLocal Path, PVC", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    p05 [label="05-vllm-deploy\n14B+32B, прогрев", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
    p06 [label="06-gateway-deploy\nGateway+PG+Redis\n+ChromaDB", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
    p07 [label="07-portal-deploy\nnginx, BFF, Portal DB\n(VPS2)", shape=box, style="filled", fillcolor="#f3e5f5", color="#9c27b0"]
    p08 [label="08-monitoring\nPrometheus+Grafana\n+DCGM", shape=box, style="filled", fillcolor="#e0f7fa", color="#00838f"]
    p09 [label="09-post-deploy\nseed, smoke-тесты", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]

    site -> p01 -> p02 -> p03 -> p04 -> p05 -> p06 -> p07 -> p08 -> p09
}
```

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

```dot
digraph TestFlow {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    start [label="make test", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2", fontsize=10]

    smoke [label="01-smoke.sh\nВсе поды Running?\nHealth-чеки?", shape=diamond, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    api [label="02-api.sh\n/v1/models ≥2?\n/chat/completions\nотвечает?", shape=diamond, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    security [label="03-security.sh\nDLP блокирует?\nRate Limiter → 429?", shape=diamond, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    load [label="04-load.sh\nНагрузка 100 rps\nбез ошибок?", shape=diamond, style="filled", fillcolor="#fff3e0", color="#ff9800"]

    pass [label="✅ ПРИНЯТО", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047", fontsize=10]
    fail [label="❌ ОТКЛОНЕНО", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63", fontsize=10]

    start -> smoke
    smoke -> api [label=" PASS"]
    smoke -> fail [label=" FAIL"]
    api -> security [label=" PASS"]
    api -> fail [label=" FAIL"]
    security -> load [label=" PASS"]
    security -> fail [label=" FAIL"]
    load -> pass [label=" PASS"]
    load -> fail [label=" FAIL"]
}
```

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

```dot
digraph FullAirgap {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=8]

    internet [label="Интернет-машина", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
    bundle [label="make bundle\nсборка пакета", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
    media [label="USB-носитель\n+ журнал учёта", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    verify [label="sha256sum -c\nпроверка", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
    load [label="make offline-load\nзагрузка", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
    deploy [label="make deploy\nansible site.yml", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    test [label="make test\n4 теста", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    done [label="✅ Готово", shape=box, style="filled", fillcolor="#43a047", color="#1a1a2e", fontcolor="#ffffff", fontsize=11]

    internet -> bundle -> media -> verify -> load -> deploy -> test -> done
}
```

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

```dot
digraph MonitoringFlow {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    gateway [label="Gateway\n/metrics", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    vllm [label="vLLM\n/metrics", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
    node [label="Node Exporter\n:9100", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
    dcgm [label="DCGM\n:9400", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]

    prom [label="Prometheus\nСбор + хранение", shape=cylinder, style="filled", fillcolor="#f3e5f5", color="#9c27b0", fontsize=10]
    grafana [label="Grafana :30300\nДашборды", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047", fontsize=10]
    alert [label="AlertManager\nУведомления", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]

    gateway -> prom
    vllm -> prom
    node -> prom
    dcgm -> prom
    prom -> grafana
    prom -> alert
}
```

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

```dot
digraph BackupFlow {
    rankdir=LR
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    pg [label="PostgreSQL\n(Gateway DB)", shape=cylinder, style="filled", fillcolor="#f3e5f5", color="#9c27b0"]
    portal [label="Portal DB\n(VPS2)", shape=cylinder, style="filled", fillcolor="#f3e5f5", color="#9c27b0"]
    models [label="/data/models/\n(модели)", shape=cylinder, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    git [label="Git\n(конфиги)", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]

    pgdump [label="pg_dump →\nbackup.sql", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    rsync [label="rsync →\n/backup/models/", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    push [label="git push", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    disk [label="/backup/\n(внешний диск)", shape=cylinder, style="filled", fillcolor="#f5f5f5", color="#616161"]

    pg -> pgdump -> disk
    portal -> pgdump
    models -> rsync -> disk
    git -> push -> disk [style=dashed]
}
```

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