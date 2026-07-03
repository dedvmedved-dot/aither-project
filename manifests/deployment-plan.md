# План развёртывания RED OS 8.0 — Aither Platform

**Дата:** 2026-07-03  
**Статус:** готов к исполнению

## Серверы

| Сервер | BMC IP | Имя хоста | OS IP | Назначение |
|---|---|---|---|---|
| node01 | 10.129.40.50 | aither-node01 | **10.129.13.171** | K8s control-plane, worker, GPU-ноды |
| node02 | 10.129.40.51 | aither-node02 | **10.129.13.172** | K8s worker, GPU-ноды, standby control-plane |

## Сеть

| Параметр | Значение |
|---|---|
| VLAN | **308** |
| Подсеть | 10.129.13.0/24 |
| Шлюз | 10.129.13.1 |
| DNS | 10.129.13.65 |
| DHCP | Отсутствует |
| Диапазон | 10.129.13.170–180 |

## Фаза 1: Подготовка ISO и BMC

### 1.1. Скачать ISO

```bash
# На VPS2 (есть доступ к Cisco-зоне)
ssh root@130.17.1.90
cd /tmp
wget -c https://files.red-soft.ru/redos/8.0/x86_64/iso/redos-8-20250711.4-Everything-x86_64-DVD1.iso
```

### 1.2. Раздать ISO через HTTP (для Virtual Media)

```bash
# На VPS2: запустить временный HTTP-сервер
cd /tmp && python3 -m http.server 8888 &
# ISO будет доступен по: http://10.129.100.235:8888/redos-8-...iso
```

### 1.3. Примонтировать ISO на BMC через Redfish

```bash
# Для каждого BMC:
# 1. Вставить Virtual Media
curl -sk -u "techvirt:..." -X POST \
  "https://<BMC_IP>/redfish/v1/Managers/bmc/VirtualMedia/Cd/.../Insert" \
  -H "Content-Type: application/json" \
  -d '{"Image": "http://10.129.100.235:8888/redos-8-...iso", "Inserted": true}'

# 2. Установить Boot Override на Cd
curl -sk -u "techvirt:..." -X PATCH \
  "https://<BMC_IP>/redfish/v1/Systems/system" \
  -H "Content-Type: application/json" \
  -d '{"Boot": {"BootSourceOverrideTarget": "Cd", "BootSourceOverrideEnabled": "Once"}}'

# 3. Перезагрузить
curl -sk -u "techvirt:..." -X POST \
  "https://<BMC_IP>/redfish/v1/Systems/system/Actions/ComputerSystem.Reset" \
  -H "Content-Type: application/json" \
  -d '{"ResetType": "ForceRestart"}'
```

## Фаза 2: Установка RED OS 8.0

### 2.1. Разметка дисков (MegaRAID)

**Предварительно через BIOS/BMC:**
- RAID1 из 2× ~1.7 TB SSD → **VD-OS** (~1.7 TB usable)
- RAID10 из 10× ~3.5 TB SSD → **VD-DATA** (~17.5 TB usable)
- M.2 2× 480GB → оставить как есть

### 2.2. Схема монтирования (инсталлятор Anaconda)

```
/                  200 GB  XFS  [VD-OS]
/var/lib/docker    300 GB  XFS  [VD-OS]
/var/log           200 GB  XFS  [VD-OS]
swap               128 GB  swap [VD-OS]
/nvme/cache        ~960 GB XFS  [M.2 RAID1]
/data/models        5 TB   XFS  [VD-DATA]
/data/k3s           5 TB   XFS  [VD-DATA]
/data/postgres      2 TB   XFS  [VD-DATA]
/data/backup        3 TB   XFS  [VD-DATA]
```

### 2.3. Параметры установки

```
Язык: en_US.UTF-8 (English)
Раскладка: us + ru
Часовой пояс: Europe/Moscow
Сеть:
  Интерфейс: trunk → VLAN 308
  IP (node01): 10.129.13.171/24
  IP (node02): 10.129.13.172/24
  Gateway: 10.129.13.1
  DNS: 10.129.13.65
  Hostname: aither-node01 / aither-node02
Пакеты:
  - Server with GUI (минимально)
  - Development Tools
  - Container Management
Пользователь:
  root: <пароль>
  admin: <пароль> (wheel group)
```

## Фаза 3: Постустановочная настройка

### 3.1. Базовые пакеты

```bash
dnf install -y epel-release
dnf install -y vim htop iotop net-tools curl wget git \
  bash-completion tmux lsof strace tcpdump
```

### 3.2. Драйверы NVIDIA

```bash
dnf config-manager --add-repo https://developer.download.nvidia.com/compute/cuda/repos/rhel8/x86_64/cuda-rhel8.repo
dnf install -y nvidia-driver nvidia-driver-NVML nvidia-driver-cuda
# Проверить: nvidia-smi
```

### 3.3. Docker + NVIDIA Container Toolkit

```bash
dnf install -y docker-ce docker-ce-cli containerd.io
dnf install -y nvidia-container-toolkit
nvidia-ctk runtime configure --runtime=docker
systemctl enable --now docker
```

### 3.4. Kubernetes (K8s, полный)

```bash
# kubeadm + kubelet + kubectl
cat > /etc/yum.repos.d/kubernetes.repo << EOF
[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/v1.32/rpm/
enabled=1
gpgcheck=0
EOF
dnf install -y kubeadm kubelet kubectl
systemctl enable --now kubelet
```

### 3.5. Настройка сети

```bash
# /etc/sysconfig/network-scripts/ifcfg-<iface>
DEVICE=<iface>
VLAN=yes
ONBOOT=yes
BOOTPROTO=none
IPADDR=10.129.13.171  # или .172
PREFIX=24
GATEWAY=10.129.13.1
DNS1=10.129.13.65
```

## Фаза 4: K8s-кластер

### 4.1. Инициализация control-plane (node01)

```bash
kubeadm init \
  --pod-network-cidr=10.244.0.0/16 \
  --apiserver-advertise-address=10.129.13.171 \
  --control-plane-endpoint=10.129.13.171
```

### 4.2. CNI (Flannel)

```bash
kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml
```

### 4.3. NVIDIA GPU Operator

```bash
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm install gpu-operator nvidia/gpu-operator \
  --set driver.enabled=false \
  --set toolkit.enabled=true
```

### 4.4. Присоединение node02

```bash
kubeadm join 10.129.13.171:6443 --token <token> --discovery-token-ca-cert-hash <hash>
```

## Команды BMC Redfish (шпаргалка)

```bash
# Перезагрузка
curl -sk -u "techvirt:..." -X POST \
  "https://<BMC>/redfish/v1/Systems/system/Actions/ComputerSystem.Reset" \
  -H "Content-Type: application/json" \
  -d '{"ResetType": "GracefulRestart"}'

# Выключение
curl -sk -u "techvirt:..." -X POST \
  "https://<BMC>/redfish/v1/Systems/system/Actions/ComputerSystem.Reset" \
  -H "Content-Type: application/json" \
  -d '{"ResetType": "ForceOff"}'

# Включение
curl -sk -u "techvirt:..." -X POST \
  "https://<BMC>/redfish/v1/Systems/system/Actions/ComputerSystem.Reset" \
  -H "Content-Type: application/json" \
  -d '{"ResetType": "On"}'

# Virtual Media — вставить ISO
curl -sk -u "techvirt:..." -X POST \
  "https://<BMC>/redfish/v1/Managers/bmc/VirtualMedia/<id>/Actions/VirtualMedia.InsertMedia" \
  -H "Content-Type: application/json" \
  -d '{"Image": "http://...iso", "Inserted": true}'

# Virtual Media — извлечь
curl -sk -u "techvirt:..." -X POST \
  "https://<BMC>/redfish/v1/Managers/bmc/VirtualMedia/<id>/Actions/VirtualMedia.EjectMedia" \
  -H "Content-Type: application/json" \
  -d '{}'
```
