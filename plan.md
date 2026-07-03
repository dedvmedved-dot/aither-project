# Aither Project → План развёртывания

## Статус

**Фаза 1: Инвентаризация — ЗАВЕРШЕНА**

## Аппаратная конфигурация (финальная)

### Node01 (10.129.13.171) — BMC 10.129.40.50

| Компонент | Детали |
|---|---|
| **Сервер** | YADRO VEGMAN S320, S/N 021222058D |
| **CPU** | 2× Intel Xeon Gold 6258R (28c/56t, 2.70/4.00 GHz, 205W) |
| **RAM** | 768 GB — 12× Samsung DDR4-2934 64GB ECC |
| **GPU** | 2× NVIDIA Quadro RTX 6000 (24 GB GDDR6, NVLink) |
| **MegaRAID** | 2× 1.7TB SSD + 10× 3.5TB SSD |
| **M.2** | 2× 480 GB NVMe SSD |

### Node02 (10.129.13.172) — BMC 10.129.40.51

| Компонент | Детали |
|---|---|
| **Сервер** | YADRO VEGMAN S320, S/N 0202230575 |
| **CPU** | 2× Intel Xeon Gold 6258R (28c/56t, 2.70/4.00 GHz, 205W) |
| **RAM** | 768 GB — 12× Samsung DDR4-2934 64GB ECC |
| **GPU** | 2× NVIDIA Quadro RTX 6000 (24 GB GDDR6, NVLink) |
| **MegaRAID** | 2× 1.7TB SSD + 10× 3.5TB SSD |
| **M.2** | 2× 480 GB NVMe SSD |

### Сеть (тестовая зона Cisco)

| Параметр | Значение |
|---|---|
| **VLAN** | 308 |
| **Подсеть** | 10.129.13.0/24 |
| **Шлюз** | 10.129.13.1 |
| **DNS** | 10.129.13.65 |
| **DHCP** | Нет (статическое назначение) |
| **Диапазон** | 10.129.13.170–180 |
| **Node01 IP** | 10.129.13.171 |
| **Node02 IP** | 10.129.13.172 |

---

## Фаза 2: Развёртывание ОС

### 2.1. Подготовка BMC

- [x] admin-доступ получен (`techvirt`, Administrator)
- [ ] Настройка Virtual Media: mount ISO RED OS 8.0
- [ ] Boot override → Cd (однократная загрузка с ISO)

### 2.2. Разметка дисков (BMC → BIOS → RAID)

**Шаг 1:** Создать RAID-группы MegaRAID:
```
VD-1 (OS, RAID1): 2× 1.7 TB → 1.7 TB usable
VD-2 (DATA, RAID10): 10× 3.5 TB → 17.5 TB usable
```

**Шаг 2:** RED OS: ручная разметка:
```
VD-1 (OS, 1.7TB)          VD-2 (DATA, 17.5TB)      M.2 (960GB)
/              200 GB     /data/models    5 TB      /nvme/cache   ~960 GB
/var/lib/docker 300 GB    /data/k8s       5 TB     
/var/log        200 GB    /data/postgres  2 TB     
swap            128 GB    /data/backup    3 TB     
/boot/efi         1 GB    резерв         ~2.5 TB
/home            ~900 GB
```

### 2.3. Установка RED OS 8.0

- [ ] ISO: `redos-8-20250711.4-Everything-x86_64-DVD1.iso` (6.1 GB)
- [ ] Загрузить ISO на VPS1: `/srv/iso/`
- [ ] Раздать через HTTP: `python3 -m http.server 8080 --directory /srv/iso`
- [ ] Подмонтировать ISO через Redfish VirtualMedia
- [ ] Выбрать: «Server with GUI» + Development Tools
- [ ] Настроить сеть (статический IP, VLAN 308)

---

## Фаза 3: Базовая настройка ОС

### 3.1. Сеть
```
Node01: 10.129.13.171/24, GW 10.129.13.1, DNS 10.129.13.65
Node02: 10.129.13.172/24, GW 10.129.13.1, DNS 10.129.13.65
```

### 3.2. Базовые пакеты
- NVIDIA driver 570.x (из репозитория RED OS)
- Docker 28.1 (из репозитория)
- Kubernetes 1.32 (kubeadm)
- etcd (внешний или встроенный в kubeadm)

### 3.3. NVIDIA GPU Operator
- nvidia-container-toolkit
- NVIDIA GPU Operator (Helm)

---

## Фаза 4: K8s-кластер

### 4.1. Архитектура

```
Node01 (10.129.13.171)          Node02 (10.129.13.172)
┌─────────────────────┐        ┌─────────────────────┐
│ control-plane       │        │ worker              │
│ etcd                │        │ etcd                │
│ GPU Operator        │        │ GPU Operator        │
│ vLLM (GPU 0)        │        │ vLLM (GPU 1)        │
│ Portal BFF          │        │ Portal BFF (replica)│
│ PostgreSQL (primary)│        │ PostgreSQL (replica)│
│ NGINX Ingress       │        │ NGINX Ingress       │
└─────────────────────┘        └─────────────────────┘
```

**Почему полный K8s (не K3s):**

| | K3s | K8s | Выбор |
|---|---|---|---|
| GPU Operator | Через костыли | Нативный NVIDIA GPU Operator | **K8s** |
| etcd | По умолчанию SQLite | etcd (отказоустойчивый) | **K8s** |
| Расширение | Болезненно при росте | Штатно до 5000+ нод | **K8s** |
| Production | Edge/IoT/ARM | Стандарт индустрии | **K8s** |

### 4.2. Компоненты платформы

| Компонент | Назначение | Размещение |
|---|---|---|
| **vLLM** | Инференс-сервер | GPU-ноды (по 2 модели на ноду) |
| **PostgreSQL 17** | Portal DB + Core DB | StatefulSet, primary + replica |
| **Portal BFF** | Backend for Frontend | Deployment (2 реплики) |
| **React SPA** | Portal UI | Nginx, отдельный виртуалхост |
| **Redis** | Кэш + сессии | Deployment |
| **Core API** | Управление ключами/платежами | Deployment |
| **NGINX Ingress** | Входная точка | DaemonSet |
| **Cert Manager** | TLS-сертификаты | Deployment |
| **NVIDIA GPU Operator** | Управление GPU | Operator |

---

## Фаза 5: CI/CD и мониторинг

- [ ] GitHub Actions для сборки образов
- [ ] Harbor/Registry для хранения образов
- [ ] Prometheus + Grafana (kube-prometheus-stack)
- [ ] Loki + Promtail для логов
- [ ] ArgoCD или Flux для GitOps

---

**Следующий шаг:** mount ISO RED OS 8.0 через BMC → установка на Node01
