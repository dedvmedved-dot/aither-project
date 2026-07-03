# План развёртывания RED OS 8.0 + K8s

## Этап 1: Подготовка BMC и RAID

### 1.1 Настройка RAID-массивов (через MegaRAID Web UI или CLI)

```bash
# Через Redfish (если доступен Storage API):
# 1. Создать VD-1: RAID1 из 2× 1.746 TB SSD
curl -k -u techvirt:... -X POST https://10.129.40.50/redfish/v1/Systems/system/Storage/.../Volumes \
  -H "Content-Type: application/json" \
  -d '{"Name":"OS","RAIDType":"RAID1","Drives":[...]}'

# Альтернативно: через BIOS MegaRAID (Ctrl+R при загрузке) или MegaCLI
```

### 1.2 Примонтировать ISO RED OS 8.0 через Virtual Media

```bash
# Через Redfish VirtualMedia:
curl -k -u techvirt:fhtfdh2\!RF78 -X POST \
  "https://10.129.40.50/redfish/v1/Managers/bmc/VirtualMedia/..." \
  -H "Content-Type: application/json" \
  -d '{"Image":"https://files.red-soft.ru/redos/8.0/x86_64/iso/...","Inserted":true}'
```

### 1.3 Загрузка с ISO

```bash
# Установить BootSourceOverride = Cd, режим = UEFI
curl -k -u ... -X PATCH https://10.129.40.50/redfish/v1/Systems/system \
  -H "Content-Type: application/json" \
  -d '{"Boot":{"BootSourceOverrideEnabled":"Once","BootSourceOverrideMode":"UEFI","BootSourceOverrideTarget":"Cd"}}'

# Перезагрузка
curl -k -u ... -X POST \
  https://10.129.40.50/redfish/v1/Systems/system/Actions/ComputerSystem.Reset \
  -H "Content-Type: application/json" \
  -d '{"ResetType":"ForceRestart"}'
```

## Этап 2: Установка RED OS 8.0

### 2.1 Параметры установки (Kickstart)

```bash
# Язык и раскладка
lang ru_RU.UTF-8
keyboard ru

# Часовой пояс
timezone Europe/Moscow --utc

# Сеть
network --device=ens1f0 --bootproto=static --ip=10.129.13.171 --netmask=255.255.255.0 --gateway=10.129.13.1 --nameserver=10.129.13.65 --hostname=node01.aither.local

# Разметка дисков (VD-1, ~1.7 TB)
part /boot --fstype=ext4 --size=1024
part swap --size=131072                                  # 128 GB
part / --fstype=xfs --size=204800                       # 200 GB
part /var/lib/docker --fstype=xfs --size=307200         # 300 GB
part /var/log --fstype=xfs --size=204800                # 200 GB

# M.2 кэш
part /nvme/cache --fstype=xfs --ondisk=nvme0n1 --size=1 --grow

# DATA-раздел (смонтировать позже, после RAID10)
# /data будет создан на VD-2 после установки

# Пакеты
%packages
@^graphical-server-environment
@container-management
@development
@network-file-system-client
kexec-tools
nvidia-driver
dkms
kernel-devel
%end

# Постустановочные скрипты
%post
# Включить Docker
systemctl enable docker
# Настроить firewall
firewall-cmd --permanent --add-port=6443/tcp
firewall-cmd --permanent --add-port=2379-2380/tcp
firewall-cmd --permanent --add-port=10250-10252/tcp
firewall-cmd --permanent --add-port=30000-32767/tcp
firewall-cmd --reload
%end
```

### 2.2 Повторить на node02 (IP: 10.129.13.172)

```bash
# Идентично, за исключением:
network --hostname=node02.aither.local --ip=10.129.13.172
```

## Этап 3: Постустановочная настройка

### 3.1 Монтирование DATA-раздела (VD-2, ~17.5 TB)

```bash
# На обоих узлах
mkfs.xfs -f /dev/sdb1
mkdir -p /data/{models,postgres,backup,k3s}
mount /dev/sdb1 /data

# В /etc/fstab
/dev/sdb1 /data xfs defaults,noatime 0 2
```

### 3.2 NVIDIA GPU Driver + Container Toolkit

```bash
# Проверить драйвер
nvidia-smi

# NVIDIA Container Toolkit
dnf install -y nvidia-container-toolkit
nvidia-ctk runtime configure --runtime=docker
systemctl restart docker

# Проверка
docker run --rm --gpus all nvidia/cuda:12.6-base nvidia-smi
```

### 3.3 Установка K8s через kubeadm

```bash
# На обоих узлах
cat > /etc/yum.repos.d/kubernetes.repo << EOF
[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/v1.32/rpm/
enabled=1
gpgcheck=1
EOF

dnf install -y kubeadm kubelet kubectl
systemctl enable kubelet

# Только на node01
kubeadm init --config kubeadm-config.yaml

# На node02
kubeadm join 10.129.13.171:6443 --token ... --discovery-token-ca-cert-hash ...
```

### 3.4 NVIDIA GPU Operator

```bash
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm install gpu-operator nvidia/gpu-operator \
  --set driver.enabled=false \
  --set toolkit.enabled=false \
  --namespace gpu-operator --create-namespace
```

### 3.5 Сеть: Calico (eBPF)

```bash
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.28/manifests/tigera-operator.yaml
```

## Этап 4: Развёртывание компонентов Aither

### 4.1 Core API + vLLM

```bash
# Helm chart из репозитория
kubectl create namespace aither
helm install aither-core ./helm/aither-core --namespace aither
```

### 4.2 Portal BFF (на VPS2)

```bash
# Размещается на VPS2 (130.17.1.90), доступен из интернета
# Конфигурация в docker-compose или Helm (внешний развёртывание)
```

### 4.3 PostgreSQL

```bash
# Развёртывается на node01, данные в /data/postgres
# CloudNativePG operator или прямой StatefulSet
```

## Проверка

```bash
# K8s
kubectl get nodes
kubectl get pods -A

# GPU
kubectl describe node node01 | grep nvidia.com/gpu

# vLLM
curl http://aither-api:8000/v1/models
```
