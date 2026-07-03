# План развёртывания Aither Platform

## Фаза 1: Подготовка хранилища (через BMC)

### На node01 и node02 (идентично)

```bash
# Подключение к BMC через Redfish
BMC=10.129.40.50    # node01
BMC=10.129.40.51    # node02 (повторить)

# Шаг 1: Очистить существующие RAID-конфигурации
# (через веб-интерфейс BMC: Storage → Virtual Disks → Delete All)

# Шаг 2: Создать RAID1 (OS) из 2× 1.7TB SSD
curl -sk -u techvirt:PASS -X POST \
  "https://$BMC/redfish/v1/Systems/system/Storage/RAID/Volumes" \
  -H "Content-Type: application/json" -d '{
    "Name": "VD-OS",
    "RAIDType": "RAID1",
    "Drives": [{"@odata.id": "/redfish/v1/Systems/system/Storage/Drives/..."}]
  }'
```

⚠️ Точный синтаксис — после аудита структуры Storage через Redfish.

## Фаза 2: Установка RED OS 8.0

### Шаг 1: Скачать ISO

ISO уже доступен: https://files.red-soft.ru/redos/8.0/x86_64/iso/redos-8-20250711.4-Everything-x86_64-DVD1.iso (6.1 GB)

### Шаг 2: Залить ISO через Virtual Media

```bash
# Разместить ISO по HTTP на VPS2
scp redos-8.iso root@130.17.1.90:/var/www/html/
# или монтировать напрямую через Redfish VirtualMedia
```

### Шаг 3: Монтирование ISO на сервер

```bash
curl -sk -u techvirt:PASS -X POST \
  "https://$BMC/redfish/v1/Managers/bmc/VirtualMedia/Cd/Actions/VirtualMedia.InsertMedia" \
  -H "Content-Type: application/json" -d '{
    "Image": "http://10.129.40.1:8080/redos-8.iso",
    "Inserted": true,
    "WriteProtected": true
  }'
```

### Шаг 4: Загрузка с ISO

```bash
curl -sk -u techvirt:PASS -X PATCH \
  "https://$BMC/redfish/v1/Systems/system" \
  -H "Content-Type: application/json" -d '{
    "Boot": {
      "BootSourceOverrideEnabled": "Once",
      "BootSourceOverrideTarget": "Cd",
      "BootSourceOverrideMode": "UEFI"
    }
  }'

# Перезагрузка
curl -sk -u techvirt:PASS -X POST \
  "https://$BMC/redfish/v1/Systems/system/Actions/ComputerSystem.Reset" \
  -H "Content-Type: application/json" -d '{"ResetType": "ForceRestart"}'
```

## Фаза 3: Разметка дисков (в установщике RED OS)

### Схема (на VD-OS, ~1.7 TB):

| Точка | ФС | Размер |
|---|---|---|
| /boot/efi | fat32 | 512 MB |
| / | XFS | 200 GB |
| /var/lib/docker | XFS | 300 GB |
| /var/log | XFS | 200 GB |
| swap | swap | 128 GB |

### Схема (на VD-DATA, ~17.5 TB):

| Точка | ФС | Размер |
|---|---|---|
| /data/models | XFS | 5 TB |
| /data/postgres | XFS | 2 TB |
| /data/backup | XFS | 3 TB |
| /data/k8s | XFS | 5 TB |

### M.2 NVMe (~960 GB):

| Точка | ФС | Размер |
|---|---|---|
| /nvme/cache | XFS | 960 GB |

## Фаза 4: Сеть

```bash
# Настройка VLAN 308
nmcli con add type vlan con-name vlan308 dev <iface> id 308
nmcli con mod vlan308 ipv4.addresses 10.129.13.171/24
nmcli con mod vlan308 ipv4.gateway 10.129.13.1
nmcli con mod vlan308 ipv4.dns 10.129.13.65
nmcli con mod vlan308 ipv4.method manual
nmcli con up vlan308
```

| Параметр | node01 | node02 |
|---|---|---|
| IP | 10.129.13.171 | 10.129.13.172 |
| Шлюз | 10.129.13.1 | 10.129.13.1 |
| DNS | 10.129.13.65 | 10.129.13.65 |
| Hostname | aither-node01 | aither-node02 |

## Фаза 5: Базовое ПО

```bash
dnf install -y epel-release
dnf groupinstall -y "Development Tools"
dnf install -y vim htop iotop iftop net-tools bind-utils \
  curl wget git jq python3-pip tmux tcpdump
```

## Фаза 6: Kubernetes (K8s)

```bash
# Установка Docker
dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
dnf install -y docker-ce docker-ce-cli containerd.io
systemctl enable --now docker

# Установка kubeadm
cat > /etc/yum.repos.d/kubernetes.repo << EOF
[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/v1.32/rpm/
enabled=1
gpgcheck=0
EOF
dnf install -y kubeadm kubelet kubectl
```

## Фаза 7: NVIDIA GPU Operator

```bash
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator --create-namespace \
  --set driver.enabled=true \
  --set toolkit.enabled=true
```
