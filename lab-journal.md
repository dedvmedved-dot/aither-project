# Лабораторный журнал: Aither Single-Node MVP

**Проект:** Aither — Token-as-a-Service платформа  
**Репозиторий:** `dedvmedved-dot/aither-project`  
**Стенд:** YADRO VEGMAN S320, сервер 40.51 (bootsman-k8s-clnt01-n8-gpu)  
**Дата начала:** 04.07.2026

---

## Исходное состояние

- **40.51:** Astra Linux 1.8 (6.6.28-1), 2× Xeon 6258R (28C/56T ×2), 754 GB RAM, 2× RTX 6000 (24 GB), 42 TB SAS SSD
- **40.50:** недоступен (RAID сбой + CMOS 2001г)
- **VPS2:** 130.17.1.90, SSH-туннели к BMC, доступ к 40.51 через sshpass
- **NVIDIA-драйвер:** не установлен
- **Docker:** не установлен
- **Kubernetes:** kubectl v1.33.5 (только клиент)

## Цель

Адаптировать ТР №1 (ядро Aither) и ТР №2 (портал) под single-node MVP на 40.51 + VPS2. Пройти Gate 0 → Gate 5.

---

### Шаг 0: Подготовка репозитория

**Цель:** привести репозиторий в состояние, соответствующее lab-workflow.

**Выполнено:**
- Удалены лишние репозитории (vegman-lab, yadro-gpu-lab)
- Всё перенесено в `aither-project`
- Обновлена спецификация 40.51 по реальному железу
- Создан документ адаптации `references/single-node-adaptation.md`
- Удалены устаревшие схемы (topology-2026-06-21.*)
- Добавлена актуальная топология (yadro-topology.*)

Статус: ✅ OK

---

### Шаг 1: Gate 0 — установка NVIDIA-драйвера

**Узел:** 40.51 (10.129.13.78)

**Цель:** установить NVIDIA-драйвер 570, проверить `nvidia-smi`.

**Окружение:**
- Astra Linux 1.8, ядро 6.6.28-1-generic
- Internet доступен (8.8.8.8 — 22ms, download.astralinux.ru — 32ms)
- linux-headers-6.6.28-1-generic уже установлены
- GCC отсутствовал (подтянется зависимостями)

**Команда:**
```bash
apt-get update
nvidia-detect  # → рекомендует nvidia-driver
DEBIAN_FRONTEND=noninteractive apt-get install -y nvidia-driver-570
```

**Разбор:** `nvidia-detect-570` определяет GPU (TU102GL [Quadro RTX 6000]) и рекомендует пакет. `nvidia-driver-570` — метапакет, тянет kernel module (DKMS), userspace-библиотеки, утилиты. `DEBIAN_FRONTEND=noninteractive` — без диалогов (сервер headless).

**Результат:** установка запущена в фоне...

Статус: 🔄 In Progress

**Результат (после ребута):**
```
NVIDIA-SMI 570.195.03   Driver Version: 570.195.03   CUDA Version: 12.8
GPU 0: Quadro RTX 6000 | 24 GB | 26°C | P8 | 19W/250W
GPU 1: Quadro RTX 6000 | 24 GB | 26°C | P8 | 20W/250W
```

**Дополнительно установлено:**
- Docker 28.3.3 + nvidia-container-toolkit
- GPU доступны внутри контейнеров (`docker run --gpus all nvidia/cuda:12.8 nvidia-smi` ✅)

**Питфолл:** после `apt-get install nvidia-driver-570` модуль nouveau остался в памяти. Требуется ребут. После ребута не поднялся VLAN 308 — ручная настройка `ip link add link ens1f0 name ens1f0.308 type vlan id 308`.

**Чек-лист Gate 0:**

| Критерий | Статус |
|---|---|
| nvidia-smi | ✅ 570.195.03, CUDA 12.8 |
| uname -a | ✅ 6.6.28-1-generic |
| Astra Linux | ✅ 1.8.1 |
| docker --version | ✅ 28.3.3 |
| nvidia-container-toolkit | ✅ |
| GPU в Docker | ✅ обе карты видны |
| 2× RTX 6000 24GB | ✅ |

Статус: ✅ Gate 0 пройден

---

### Шаг 2: Gate 1 — K8s single-node

**Узел:** 40.51 (10.129.13.78)

**Цель:** развернуть одноузловой Kubernetes с NVIDIA GPU Operator.
