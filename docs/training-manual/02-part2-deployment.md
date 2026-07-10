# Часть II. Практическое развёртывание

> **Документ 2 из 5.** Пошаговый деплой всей платформы Aither — от голого железа до production. Каждая команда объяснена. Каждый манифест разобран построчно.

---

# Глава 8. Подготовка серверов и установка ОС

> **Цель главы:** подготовить серверы YADRO VEGMAN S320 к работе: установить Astra Linux SE 1.8 через Kickstart, настроить сеть, SSH, драйверы NVIDIA. После этой главы сервер будет готов к установке Kubernetes.

---

## 8.1. Обзор инфраструктуры: что и где устанавливаем

Прежде чем что-то устанавливать, освежим в памяти карту нашей инфраструктуры:

| Узел | IP | Роль | ОС | GPU | Что будем ставить |
|---|---|---|---|---|---|
| **n8** | 10.129.13.78 | K8s control-plane + worker | Astra Linux SE 1.8 | 2× RTX 6000 | ОС → драйверы → containerd → kubeadm init |
| **n7** | 10.129.13.77 | K8s worker | Astra Linux SE 1.8 | 2× RTX 6000 | ОС → драйверы → containerd → kubeadm join |
| **VPS1** | 170.168.91.95 | Входная точка | Ubuntu 24.04 | — | Уже настроен (nginx, WireGuard) |
| **VPS2** | 130.17.1.90 | Портал | Ubuntu | — | Уже настроен (BFF, nginx, PostgreSQL) |

Сегодня мы работаем с n7 и n8 — серверами YADRO VEGMAN S320. Это мощные машины:
- 2× Xeon 6258R (28C/56T на сокет)
- 754 GB RAM
- 42 TB SAS SSD
- 2× NVIDIA RTX 6000 (24 GB VRAM каждая)
- BMC для удалённого управления

---

## 8.2. Установка Astra Linux SE 1.8 через Kickstart

### Что такое Kickstart

Обычно установка ОС — это диалог: выбрать язык → разметить диск → выбрать пакеты → ... 20 экранов, 20 минут кликов. Для одного сервера — терпимо. Для десяти — ад.

**Kickstart** — это файл с ответами на все вопросы установщика. Вы пишете его один раз, и установка проходит полностью автоматически.

Структура Kickstart-файла:
```
# 1. Команды (что делать)
network --bootproto=static --ip=10.129.13.78 --netmask=255.255.255.0
lang ru_RU.UTF-8
keyboard ru
timezone Europe/Moscow

# 2. Разметка диска
clearpart --all --initlabel
part /boot --fstype=ext4 --size=1024
part / --fstype=ext4 --size=102400
part /data --fstype=ext4 --size=1 --grow

# 3. Пакеты (что установить)
%packages
@^server-product-environment
openssh-server
nano
wget
%end

# 4. Пост-установочный скрипт
%post
# Здесь — команды, которые выполнятся после установки
systemctl enable sshd
useradd -m -s /bin/bash admin
echo "admin:password" | chpasswd
%end
```

### Разбор ks-node01.cfg построчно

Наш Kickstart-файл для n8 (`scripts/ks-node01.cfg`):

```bash
# ===== ЯЗЫК И РАСКЛАДКА =====
lang ru_RU.UTF-8
# ↑ Русский язык интерфейса и консоли. UTF-8 — кодировка.

keyboard ru
# ↑ Русская раскладка клавиатуры (для BMC-консоли).

timezone Europe/Moscow --isUtc
# ↑ Часовой пояс. --isUtc: аппаратные часы в UTC.

# ===== СЕТЬ =====
network --bootproto=static --device=eth0 --ip=10.129.13.78 --netmask=255.255.255.0 --gateway=10.129.13.1 --nameserver=10.129.13.1 --hostname=bootsmam-k8s-clnt01-n8-gpu
# ↑ Статический IP (не DHCP). Все параметры жёстко заданы.
#   device=eth0 — какой интерфейс настраивать.
#   nameserver=10.129.13.1 — DNS-сервер (обычно шлюз).

# ===== ПАРОЛЬ ROOT =====
rootpw --iscrypted $6$rounds=656000$...хэш_пароля...
# ↑ Пароль root в зашифрованном виде (SHA-512).
#   Генерируется командой: python3 -c 'import crypt; print(crypt.crypt("password"))'

# ===== РАЗМЕТКА ДИСКА =====
clearpart --all --initlabel
# ↑ Удалить ВСЕ существующие разделы. --initlabel: создать новую таблицу разделов.

part /boot --fstype=ext4 --size=1024
# ↑ /boot — загрузочный раздел. 1 GB (с запасом под несколько ядер).

part / --fstype=ext4 --size=102400
# ↑ / — корневой раздел. 100 GB. Здесь ОС и все программы.

part /data --fstype=ext4 --size=1 --grow
# ↑ /data — раздел для моделей и данных. --grow: занять всё оставшееся место.
#   При диске 42 TB /data получит примерно 41.9 TB.

# ===== ЗАГРУЗЧИК =====
bootloader --location=mbr --boot-drive=sda
# ↑ Установить загрузчик GRUB в MBR первого диска.

# ===== ПАКЕТЫ =====
%packages
@^server-product-environment
# ↑ Группа пакетов «Сервер» (без графического интерфейса).

openssh-server
# ↑ SSH-сервер для удалённого доступа.

nano
wget
curl
net-tools
# ↑ Базовые утилиты.
%end

# ===== ПОСТ-УСТАНОВКА (%post) =====
%post --log=/root/kickstart-post.log
# ↑ Всё, что между %post и %end, выполнится после установки ОС.
#   --log: сохранить вывод в файл (для отладки).

# 1. Включаем SSH
systemctl enable sshd
# ↑ sshd будет запускаться при старте системы.

# 2. Создаём администратора
useradd -m -s /bin/bash admin
echo "admin:ChangeMe123" | chpasswd
usermod -aG wheel admin
# ↑ Группа wheel = sudo (в Astra Linux).

# 3. Отключаем Parsec (мандатный контроль доступа)
#    Он блокирует работу драйверов NVIDIA и containerd.
sed -i 's/parsec=1/parsec=0/' /etc/default/grub
update-grub
# ↑ Меняем параметр загрузки ядра и обновляем GRUB.

# 4. Настройка /data
mkdir -p /data/models
chown -R admin:admin /data
# ↑ Создаём папку для моделей ИИ.

# 5. Установка Chrony (синхронизация времени)
apt-get install -y chrony
systemctl enable chronyd
# ↑ Точное время критично для Kubernetes (сертификаты, токены).
%end

# ===== ПЕРЕЗАГРУЗКА =====
reboot
```

### Как загрузить ISO через BMC

BMC (Baseboard Management Controller) — это маленький компьютер внутри сервера, который работает даже когда сервер выключен. Через BMC мы можем:

1. **Смонтировать ISO-образ удалённо:**
   - Заходим в веб-интерфейс BMC (через цепочку пробросов: VPS1:443 → VPS2:19443 → n7:9443)
   - Virtual Media → Choose File → выбираем ISO-образ Astra Linux
   - Нажимаем «Mount»

2. **Загрузиться с ISO:**
   - Power → Power On
   - Во время загрузки нажать F11 (Boot Menu)
   - Выбрать «Virtual CD/DVD»

3. **Установка:**
   - В меню загрузки выбрать «Install (Kickstart)»
   - Нажать Tab и дописать: `inst.ks=http://10.129.13.1/ks/ks-node01.cfg`
   - Нажать Enter — дальше всё автоматически

```dot
digraph KickstartInstall {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    admin [label="Администратор\n(браузер)", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]

    subgraph cluster_bmc {
        label="BMC (IPMI)"
        style="rounded,dashed"
        color="#ff9800"
        fontname="system-ui"

        mount [label="1. Монтируем\nISO-образ", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
        power [label="3. Включаем\nсервер", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    }

    subgraph cluster_server {
        label="Сервер (n7/n8)"
        style="rounded,dashed"
        color="#43a047"
        fontname="system-ui"

        boot [label="4. BIOS →\nVirtual CD", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
        kernel [label="5. Загрузка\nядра Linux", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
        kickstart [label="6. Чтение\nks-node01.cfg", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
        install [label="7. Автоматическая\nустановка\n(5-10 минут)", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
        reboot [label="8. Перезагрузка\n→ готовая ОС", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    }

    iso [label="ISO-образ\nAstra Linux", shape=cylinder, style="filled", fillcolor="#f3e5f5", color="#9c27b0"]
    ks [label="ks-node01.cfg\n(Kickstart)", shape=note, style="filled", fillcolor="#f3e5f5", color="#9c27b0"]

    admin -> mount
    mount -> iso
    admin -> power
    power -> boot
    boot -> kernel -> kickstart
    ks -> kickstart
    kickstart -> install -> reboot
}
```

*Схема 8.1. Процесс установки Astra Linux через Kickstart: от монтирования ISO до готовой ОС.*

---

## 8.3. Базовая настройка ОС

После перезагрузки сервер загружается в свежеустановленную Astra Linux. Заходим по SSH и настраиваем.

### Проверка установки

```bash
# Версия ОС
cat /etc/astra_version
# → Astra Linux Special Edition 1.8.1

# Ядро
uname -r
# → 6.1.0-... (версия зависит от сборки)

# Разметка диска
df -h
# Должны увидеть:
# /dev/sda1  /boot  1 GB
# /dev/sda2  /      100 GB
# /dev/sda3  /data  41.9 TB
```

### Настройка сети (проверка)

```bash
# Проверяем IP
ip a show eth0
# → inet 10.129.13.78/24

# Проверяем шлюз
ip route | grep default
# → default via 10.129.13.1 dev eth0

# Проверяем DNS
cat /etc/resolv.conf
# → nameserver 10.129.13.1

# Пинг до соседа (n7, если мы на n8)
ping -c 2 10.129.13.77
```

### Настройка SSH

```bash
# Редактируем /etc/ssh/sshd_config
# Ключевые параметры:
Port 22                         # стандартный порт (можно сменить)
PermitRootLogin prohibit-password  # root только по ключу
PubkeyAuthentication yes        # вход по SSH-ключу
PasswordAuthentication no       # НЕ по паролю (безопаснее)

# После изменений:
systemctl restart sshd
```

⚠️ **Различие `ssh` и `sshd`:**
- `ssh` — клиент (команда для подключения К другому серверу)
- `sshd` — демон (сервер, принимающий подключения)
- `ssh.service` не существует — `systemctl restart sshd`

### Брандмауэр

```bash
# Astra Linux использует iptables
iptables -L -n    # посмотреть правила

# Минимальный набор (разрешаем только нужное):
iptables -A INPUT -p tcp --dport 22 -j ACCEPT      # SSH
iptables -A INPUT -p tcp --dport 6443 -j ACCEPT     # K8s API (только n8!)
iptables -A INPUT -p tcp --dport 30000:32767 -j ACCEPT  # NodePort
iptables -A INPUT -p udp --dport 8472 -j ACCEPT     # Flannel VXLAN
iptables -A INPUT -i lo -j ACCEPT                   # localhost
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -P INPUT DROP                               # всё остальное — запретить
```

---

## 8.4. Установка драйверов NVIDIA

### Проверяем, видит ли система GPU

```bash
lspci | grep -i nvidia
# → 01:00.0 3D controller: NVIDIA Corporation AD102 [RTX 6000] (rev a1)
# → 02:00.0 3D controller: NVIDIA Corporation AD102 [RTX 6000] (rev a1)
# Две карты, видны!

# Но драйверов пока нет:
nvidia-smi
# → command not found
```

### Установка драйверов

Astra Linux основан на Debian, поэтому пакеты устанавливаются через `apt`:

```bash
# 1. Добавляем репозиторий NVIDIA (если есть интернет)
#    В закрытом контуре — пакеты должны быть в offline-пакете
apt-get update

# 2. Устанавливаем драйвер и утилиты
apt-get install -y nvidia-driver nvidia-cuda-toolkit nvidia-smi

# 3. Перезагружаемся
reboot
```

После перезагрузки:

```bash
nvidia-smi
```

Вывод:
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

Ключевые поля:
- **Driver Version: 550.90.07** — версия драйвера
- **CUDA Version: 12.4** — поддерживаемая версия CUDA
- **24576MiB** — 24 GB VRAM на каждой карте
- **GPU-Util: 0%** — карты пока не используются (vLLM ещё не запущен)

### nvidia-persistenced

По умолчанию драйвер NVIDIA выгружается, когда GPU не используется. Это нормально для игр, но плохо для сервера: при запуске vLLM драйвер должен загрузиться заново, что занимает секунды.

```bash
systemctl enable nvidia-persistenced
systemctl start nvidia-persistenced
```

Эта служба держит драйвер загруженным постоянно.

### NVIDIA Container Toolkit

Для работы GPU из контейнеров (Docker, containerd) нужен специальный «переходник» — nvidia-container-toolkit:

```bash
# Установка
apt-get install -y nvidia-container-toolkit

# Настройка containerd (будет в главе 9)
nvidia-ctk runtime configure --runtime=containerd
systemctl restart containerd
```

После этого контейнеры смогут использовать GPU через `--gpus all` (Docker) или `runtimeClassName: nvidia` (Kubernetes).

```dot
digraph NvidiaStack {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    subgraph cluster_hw {
        label="Физический уровень"
        style="rounded"
        color="#616161"

        gpu0 [label="RTX 6000 #0\n24 GB VRAM", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
        gpu1 [label="RTX 6000 #1\n24 GB VRAM", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
    }

    subgraph cluster_driver {
        label="Уровень драйвера"
        style="rounded"
        color="#ff9800"

        driver [label="nvidia-driver 550.90\n+ CUDA 12.4", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
        persist [label="nvidia-persistenced\n(держит драйвер загруженным)", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    }

    subgraph cluster_container {
        label="Уровень контейнеров"
        style="rounded"
        color="#1976d2"

        toolkit [label="nvidia-container-toolkit\n(пробрасывает драйверы\nвнутрь контейнера)", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
        containerd [label="containerd\n(nvidia runtime)", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2")]
    }

    subgraph cluster_app {
        label="Приложения"
        style="rounded"
        color="#43a047"

        vllm [label="vLLM\n(видит GPU)", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    }

    gpu0 -> driver
    gpu1 -> driver
    driver -> persist
    driver -> toolkit
    toolkit -> containerd
    containerd -> vllm
}
```

*Схема 8.2. Стек NVIDIA: от физической карты до vLLM в контейнере.*

---

## 8.5. ✏️ Практикум

### Задание 1. «Kickstart»
Объясните, зачем нужна строка `parsec=0` в Kickstart-файле. Что произойдёт, если её убрать?

### Задание 2. «nvidia-smi»
Подключитесь к серверу (если есть доступ) и выполните `nvidia-smi`. Ответьте:
- Драйвер какой версии?
- Сколько GPU?
- Сколько VRAM на каждой?
- Какая температура?

### Задание 3. «Сеть»
Напишите команду `iptables`, которая разрешит входящие подключения на порт 3000 (BFF).

### Задание 4. «Словарь»
- Kickstart, BMC, ISO, IPMI
- Parsec, GRUB, MBR
- nvidia-smi, CUDA, VRAM
- nvidia-persistenced, nvidia-container-toolkit

---

**Итог главы 8.** Вы узнали:
- Как установить Astra Linux автоматически через Kickstart (построчный разбор ks-node01.cfg)
- Как загрузить ISO через BMC удалённо
- Как настроить сеть, SSH, брандмауэр после установки
- Как установить драйверы NVIDIA и проверить их через nvidia-smi
- Зачем нужны nvidia-persistenced и nvidia-container-toolkit

В следующей главе — установка Kubernetes.


# Глава 9. Развёртывание Kubernetes

> **Цель главы:** установить containerd, настроить его для работы с GPU, поднять кластер Kubernetes из двух узлов (n8 — control-plane, n7 — worker), настроить Flannel и GPU Operator.

---

## 9.1. containerd: установка и настройка

**containerd** (произносится «контэйнэр-ди») — это среда выполнения контейнеров, которую использует Kubernetes. В отличие от Docker, containerd — только runtime, без сборки образов и CLI.

### Установка

```bash
# Установка containerd (Debian-путь, работает в Astra Linux)
apt-get update
apt-get install -y containerd

# Проверка
containerd --version
# → containerd github.com/containerd/containerd v1.7.x
```

### Конфигурация

После установки нужно настроить containerd:

```bash
# 1. Создаём дефолтный конфиг
mkdir -p /etc/containerd
containerd config default > /etc/containerd/config.toml

# 2. ВАЖНО: переключаем cgroup driver на systemd
#    Без этого kubelet не сможет управлять ресурсами!
sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml

# 3. Настройка NVIDIA runtime (если установлен nvidia-container-toolkit)
nvidia-ctk runtime configure --runtime=containerd
# ↑ Добавляет секцию [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia]

# 4. Перезапускаем
systemctl restart containerd
systemctl enable containerd
```

> ⚠️ **Почему `SystemdCgroup = true`?** Kubelet использует cgroup-драйвер systemd для управления ресурсами подов. Если containerd использует cgroupfs (по умолчанию) — будет конфликт: два драйвера управляют одними и теми же группами процессов. Результат: поды не запускаются или падают OOMKilled без причины.

### Проверка

```bash
# containerd работает?
systemctl status containerd

# Может запускать контейнеры?
crictl pull nginx:alpine   # скачать образ
crictl images               # посмотреть список образов
```

`crictl` — это CLI для containerd (как `docker` для Docker). Основные команды:
- `crictl ps` — список контейнеров (как `docker ps`)
- `crictl images` — список образов (как `docker images`)
- `crictl logs <id>` — логи контейнера

---

## 9.2. kubeadm init: создание control-plane

### Установка kubeadm, kubelet, kubectl

```bash
# Добавляем репозиторий Kubernetes
apt-get install -y apt-transport-https ca-certificates curl gpg
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.33/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.33/deb/ /' > /etc/apt/sources.list.d/kubernetes.list

apt-get update
apt-get install -y kubelet kubeadm kubectl
apt-mark hold kubelet kubeadm kubectl  # запретить автообновление
```

> 🔤 **kubeadm, kubelet, kubectl — в чём разница?**
> - **kubeadm** — инструмент для создания кластера (команды `init` и `join`)
> - **kubelet** — агент, работающий на каждом узле, запускает поды
> - **kubectl** — команда администратора для управления кластером

### Инициализация control-plane (на n8)

```bash
kubeadm init \
  --pod-network-cidr=10.244.0.0/16 \
  # ↑ Диапазон IP-адресов для подов. Должен совпадать с Flannel!

  --apiserver-advertise-address=10.129.13.78 \
  # ↑ IP-адрес, на котором apiserver будет слушать.
  #   Это внутренний адрес n8 в VLAN 308.

  --cri-socket=unix:///var/run/containerd/containerd.sock
  # ↑ Путь к сокету containerd (не Docker!)
```

Вывод команды (ключевые строки):

```
Your Kubernetes control-plane has initialized successfully!

To start using your cluster, you need to run the following as a regular user:

  mkdir -p $HOME/.kube
  sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
  sudo chown $(id -u):$(id -g) $HOME/.kube/config

You can now join any number of worker nodes by running the following on each as root:

kubeadm join 10.129.13.78:6443 --token abcdef.0123456789abcdef \
    --discovery-token-ca-cert-hash sha256:1234...abcd
```

**Что произошло:**
1. `kubeadm init` создал сертификаты для apiserver (в `/etc/kubernetes/pki/`)
2. Запустил etcd, apiserver, controller-manager, scheduler как статические поды
3. Сгенерировал токен для присоединения worker-узлов
4. Создал `/etc/kubernetes/admin.conf` — конфиг для kubectl

### Настройка kubectl

```bash
# Копируем конфиг в домашнюю папку
mkdir -p $HOME/.kube
cp /etc/kubernetes/admin.conf $HOME/.kube/config
chown $(id -u):$(id -g) $HOME/.kube/config

# Проверяем
kubectl get nodes
# NAME                                   STATUS     ROLES           AGE   VERSION
# bootsman-k8s-clnt01-n8-gpu            NotReady   control-plane   30s   v1.33.5
```

Узел в статусе **NotReady** — потому что ещё не настроена сеть (Flannel).

### Что делать, если токен потерян

```bash
# Создать новый токен
kubeadm token create --print-join-command
# → kubeadm join 10.129.13.78:6443 --token ... --discovery-token-ca-cert-hash ...
```

---

## 9.3. Flannel: overlay-сеть

Поды на разных узлах должны видеть друг друга. Для этого нужен **CNI-плагин** (Container Network Interface). Мы используем Flannel.

```bash
# Применяем манифест Flannel
kubectl apply -f https://raw.githubusercontent.com/flannel-io/flannel/master/Documentation/kube-flannel.yml
```

Что внутри манифеста (ключевые части):

```yaml
# ConfigMap с настройками Flannel
kind: ConfigMap
data:
  net-conf.json: |
    {
      "Network": "10.244.0.0/16",    # ← должно совпадать с --pod-network-cidr!
      "Backend": {
        "Type": "vxlan"               # VXLAN-инкапсуляция
      }
    }

# DaemonSet: по одному flannel-поду на каждом узле
kind: DaemonSet
spec:
  template:
    spec:
      containers:
      - name: kube-flannel
        image: flannelcni/flannel:v0.23.0
```

После применения:

```bash
kubectl get nodes
# NAME                                   STATUS   ROLES           AGE   VERSION
# bootsman-k8s-clnt01-n8-gpu            Ready    control-plane   2m    v1.33.5

kubectl get pods -n kube-flannel
# NAME                    READY   STATUS    RESTARTS   AGE
# kube-flannel-ds-abc1    1/1     Running   0          30s
```

---

## 9.4. kubeadm join: добавление worker-узла

На **n7** выполняем ту самую команду, которую выдал `kubeadm init`:

```bash
kubeadm join 10.129.13.78:6443 --token abcdef.0123456789abcdef \
    --discovery-token-ca-cert-hash sha256:1234...abcd \
    --cri-socket=unix:///var/run/containerd/containerd.sock
```

Вывод:
```
This node has joined the cluster:
* Certificate signing request was sent to apiserver and a response was received.
* The Kubelet was informed of the new secure connection details.

Run 'kubectl get nodes' on the control-plane to see this node join the cluster.
```

Проверяем на n8:

```bash
kubectl get nodes
# NAME                                   STATUS   ROLES           AGE
# bootsman-k8s-clnt01-n8-gpu            Ready    control-plane   5m
# bootsman-k8s-clnt01-n7-gpu            Ready    <none>          30s
```

Оба узла Ready! Flannel автоматически запустился и на n7 (через DaemonSet).

---

## 9.5. NVIDIA GPU Operator

GPU Operator — это набор компонентов для работы GPU в Kubernetes:

```bash
# Установка через Helm
helm repo add nvidia https://nvidia.github.io/gpu-operator
helm repo update
helm install gpu-operator nvidia/gpu-operator \
  --set driver.enabled=false \     # драйвер уже установлен на хосте
  --set toolkit.enabled=true       # включить nvidia-container-toolkit
```

Что устанавливает GPU Operator:
- **device-plugin** — регистрирует GPU как ресурс (`nvidia.com/gpu`)
- **dcgm-exporter** — метрики GPU для Prometheus
- **container-toolkit** — доступ к GPU из контейнеров

Проверка:

```bash
kubectl describe node bootsman-k8s-clnt01-n8-gpu | grep nvidia
# → nvidia.com/gpu: 2
# → nvidia.com/gpu: 2
# Две карты доступны как ресурс!

kubectl get pods -n gpu-operator
# Все поды должны быть Running
```

---

## 9.6. Системные компоненты

### Metrics Server

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

Проверка:
```bash
kubectl top nodes
# NAME                                   CPU(cores)   CPU%   MEMORY(bytes)   MEMORY%
# bootsman-k8s-clnt01-n8-gpu            1200m        2%     12Gi            1%
```

### cert-manager

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml
```

Автоматически выпускает и обновляет TLS-сертификаты (для внутренних нужд K8s).

### Финальная проверка

```bash
kubectl get pods -A
# NAMESPACE      NAME                                       READY   STATUS
# kube-system    coredns-...                                1/1     Running
# kube-system    etcd-n8                                    1/1     Running
# kube-system    kube-apiserver-n8                          1/1     Running
# kube-system    kube-controller-manager-n8                 1/1     Running
# kube-system    kube-proxy-...                             1/1     Running
# kube-system    kube-scheduler-n8                          1/1     Running
# kube-flannel   kube-flannel-ds-...                        1/1     Running
# gpu-operator   nvidia-device-plugin-...                   1/1     Running
# gpu-operator   nvidia-dcgm-exporter-...                   1/1     Running
```

```dot
digraph K8sClusterReady {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    subgraph cluster_n8 {
        label="n8 (control-plane)\n10.129.13.78"
        style="rounded,dashed"
        color="#ff9800"
        fontname="system-ui"

        cp [label="Control Plane:\napiserver, etcd,\nscheduler, cm", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
        flannel_n8 [label="Flannel", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
        gpu_n8 [label="GPU Operator\n(2× RTX 6000)", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    }

    subgraph cluster_n7 {
        label="n7 (worker)\n10.129.13.77"
        style="rounded,dashed"
        color="#43a047"
        fontname="system-ui"

        proxy_n7 [label="kube-proxy", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
        flannel_n7 [label="Flannel", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
        gpu_n7 [label="GPU Operator\n(2× RTX 6000)", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    }

    flannel_n8 -> flannel_n7 [label="VXLAN\n10.244.0.0/16", style=dashed, dir=both]
}
```

*Схема 9.1. Готовый кластер Kubernetes: n8 (control-plane), n7 (worker), Flannel overlay, GPU Operator.*

---

## 9.7. ✏️ Практикум

### Задание 1. «Проверь кластер»
Какие команды нужно выполнить, чтобы убедиться, что кластер готов к работе? (Подсказка: 4 команды)

### Задание 2. «SystemdCgroup»
Почему важно установить `SystemdCgroup = true` в containerd? Что случится, если оставить `false`?

### Задание 3. «Токен»
Токен для `kubeadm join` потерян. Как создать новый?

### Задание 4. «Словарь»
- kubeadm, kubelet, kubectl
- CNI, Flannel, VXLAN
- DaemonSet, GPU Operator
- crictl, SystemdCgroup

---

**Итог главы 9.** Кластер Kubernetes готов:
- containerd настроен (SystemdCgroup=true, nvidia runtime)
- n8 — control-plane (kubeadm init)
- n7 — worker (kubeadm join)
- Flannel overlay-сеть (10.244.0.0/16, VXLAN)
- GPU Operator (nvidia.com/gpu: 2 на каждом узле)
- Metrics Server, cert-manager

В следующей главе — деплой vLLM и моделей.


# Глава 10. Развёртывание vLLM и моделей

> **Цель главы:** задеплоить две модели (14B и 32B) в Kubernetes, подключить LoRA-адаптер, проверить работоспособность и замерить скорость.

---

## 10.1. Подготовка моделей

Модели — самые большие файлы в системе. Их нужно подготовить заранее.

### Скачивание с Hugging Face

На машине с интернетом:

```bash
pip install huggingface_hub

# 14B (~28 GB)
huggingface-cli download Qwen/Qwen2.5-14B-Instruct \
  --local-dir /data/models/Qwen2.5-14B-Instruct

# 32B GPTQ (~20 GB)
huggingface-cli download Qwen/Qwen2.5-32B-Instruct-GPTQ-Int4 \
  --local-dir /data/models/Qwen2.5-32B-Instruct-GPTQ
```

Что внутри папки модели:

```
Qwen2.5-14B-Instruct/
├── config.json              ← архитектура модели (Transformer, количество слоёв, голов)
├── tokenizer.json           ← токенизатор: слова → числа
├── tokenizer_config.json    ← настройки токенизатора (BPE, special tokens)
├── model-00001-of-00004.safetensors  ← веса, часть 1 из 4 (~7 GB)
├── model-00002-of-00004.safetensors  ← часть 2
├── model-00003-of-00004.safetensors  ← часть 3
├── model-00004-of-00004.safetensors  ← часть 4
└── generation_config.json   ← параметры генерации по умолчанию
```

> 🔤 **safetensors** — безопасный формат хранения весов (Safe + Tensor). В отличие от старых `.bin`/`.pt`, не содержит исполняемого Python-кода — только числа. Невозможно спрятать вредоносный код в весах модели.

### Перенос в закрытый контур

Модели весят 28 GB + 20 GB = ~48 GB. Не влезают на обычную флешку. Варианты:
- **Внешний USB-HDD/SSD** (1+ TB) — самый надёжный
- **Перенос по сети** (scp) — если есть временный доступ
- **Оптический диск** (BD-R 50 GB) — для ГОСТ-режима

```bash
# На машине с интернетом:
tar -czf models-14b.tar.gz -C /data/models Qwen2.5-14B-Instruct
tar -czf models-32b.tar.gz -C /data/models Qwen2.5-32B-Instruct-GPTQ
sha256sum models-*.tar.gz > models-checksums.txt

# Копируем на внешний диск, физически переносим, монтируем в закрытом контуре:
mount /dev/sdb1 /mnt/usb
cp /mnt/usb/models-*.tar.gz /data/
sha256sum -c models-checksums.txt  # ← проверка целостности!
tar -xzf models-14b.tar.gz -C /data/models/
tar -xzf models-32b.tar.gz -C /data/models/
```

> ⚠️ **Почему sha256sum?** При копировании больших файлов через флешку биты могут испортиться (помехи, плохой контакт). Контрольная сумма гарантирует, что файл дошёл без повреждений. Один испорченный бит в модели = неопределённое поведение или отказ загрузки.

---

## 10.2. PersistentVolumeClaim для моделей

Модель 14B будет лежать на локальном диске n8 (hostPath). Модель 32B — в PersistentVolumeClaim (PVC), чтобы можно было перенести между узлами.

### Почему разные подходы?

| Подход | Плюсы | Минусы | Используем для |
|---|---|---|---|
| **hostPath** | Прямой доступ к диску = максимальная скорость | Привязан к узлу (не перенести) | 14B на n8 |
| **PVC** | Можно перенести на другой узел | Чуть медленнее | 32B на n7 |

PVC для 32B:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: models-32b-pvc
spec:
  accessModes:
  - ReadWriteOnce           # только один под может писать
  resources:
    requests:
      storage: 100Gi        # 100 GB (модель 20 GB + запас под KV-кэш)
  storageClassName: local-path  # Local Path Provisioner
```

```bash
kubectl apply -f pvc-32b.yaml
kubectl get pvc
# → models-32b-pvc   Bound   pvc-abc123   100Gi   RWO   local-path
```

```dot
digraph StorageComparison {
    rankdir=LR
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    subgraph cluster_hostPath {
        label="hostPath (14B, n8)"
        style="rounded,dashed"
        color="#e91e63"
        fontname="system-ui"

        pod14 [label="Pod vLLM 14B", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
        disk [label="/data/models/\n(42 TB SAS SSD)", shape=cylinder, style="filled", fillcolor="#f5f5f5", color="#616161"]
        pod14 -> disk [label="прямой\ndostup"]
        note1 [label="✅ Быстро\n❌ Привязан к n8", shape=plaintext, fontsize=8]
    }

    subgraph cluster_pvc {
        label="PVC (32B, n7)"
        style="rounded,dashed"
        color="#43a047"
        fontname="system-ui"

        pod32 [label="Pod vLLM 32B", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
        pv [label="PV\n(физический диск)", shape=cylinder, style="filled", fillcolor="#f5f5f5", color="#616161"]
        pvc [label="PVC\n(запрос 100Gi)", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
        pod32 -> pvc -> pv
        note2 [label="✅ Переносимый\n⚠️ Чуть медленнее", shape=plaintext, fontsize=8]
    }
}
```

*Схема 10.1. Сравнение hostPath (14B, привязан к n8) и PVC (32B, можно перенести).*

---

## 10.3. Деплой vLLM 14B: пошагово

### Шаг 1: применяем манифест

```bash
kubectl apply -f k8s/vllm-14b/deployment.yaml
# → deployment.apps/vllm-qwen created

kubectl apply -f k8s/vllm-14b/service.yaml
# → service/vllm created
# → service/vllm-nodeport created
```

### Шаг 2: ждём запуска

```bash
kubectl get pods -l app=vllm-qwen -w
# NAME                           READY   STATUS              RESTARTS   AGE
# vllm-qwen-7f8b9c-abc1         0/1     ContainerCreating   0          5s
# vllm-qwen-7f8b9c-abc1         0/1     Running             0          30s
# vllm-qwen-7f8b9c-abc1         1/1     Running             0          2m
```

Первые 30 секунд — скачивание образа (если не закэширован). Потом модель загружается в GPU.

### Шаг 3: смотрим логи

```bash
kubectl logs vllm-qwen-7f8b9c-abc1
```

Ключевые строки в логах:

```
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000

Loading model from /models/Qwen2.5-14B-Instruct...
Model loaded in 45.2s
GPU memory: 18.4 GB / 24.0 GB (76.7%)

INFO:     LoRA module 'astra-14b' registered
```

**Разбор логов:**
- `Model loaded in 45.2s` — время загрузки весов в GPU (чем больше модель, тем дольше)
- `GPU memory: 18.4 GB / 24.0 GB` — 14 GB модель + 4 GB KV-кэш = 18 GB
- `LoRA module registered` — адаптер astra-14b успешно подключён

### Шаг 4: проверяем health

```bash
# Через NodePort (с любого узла)
curl http://10.129.13.78:32293/health
# → OK

# Через ClusterIP (только внутри кластера)
kubectl run -it --rm debug --image=curlimages/curl -- curl http://vllm:8000/health
# → OK
```

### Шаг 5: первый запрос (прогрев)

> ⚠️ **Первый запрос занимает 10–30 секунд.** Это нормально: vLLM компилирует модель для GPU (CUDA Graph). Последующие запросы — быстро.

```bash
# Замеряем время
time curl -X POST http://10.129.13.78:32293/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-14b",
    "messages": [{"role": "user", "content": "Привет! Представься, пожалуйста."}],
    "max_tokens": 100
  }'

# Первый раз: 15-30 секунд (прогрев)
# Второй раз: 2-5 секунд (нормальная скорость)
```

### Шаг 6: замер tok/s

```bash
time curl -X POST http://10.129.13.78:32293/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-14b",
    "messages": [{"role": "user", "content": "Напиши 10 предложений о Москве."}],
    "max_tokens": 500
  }' -s -o /dev/null -w "HTTP %{http_code}, time: %{time_total}s\n"

# → HTTP 200, time: 18.2s
# 500 токенов / 18.2 сек ≈ 27.5 tok/s
```

Анализ: prefill (~200 ms) + decode (500 × ~35 ms/токен при TP=2) = ~18 секунд. 55% времени — prefill.

### Что мы только что задеплоили (архитектура)

```dot
digraph VLLM14Deploy {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    subgraph cluster_k8s {
        label="Kubernetes"
        style="rounded,dashed"
        color="#ff9800"
        fontname="system-ui"

        deploy [label="Deployment: vllm-qwen\nreplicas=1, strategy=Recreate", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
        svc_cluster [label="Service: vllm\nClusterIP:8000", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
        svc_node [label="Service: vllm-nodeport\nNodePort:32293", shape=box, style="filled", fillcolor="#f3e5f5", color="#9c27b0"]
    }

    subgraph cluster_n8 {
        label="n8 (control-plane)"
        style="rounded"
        color="#e91e63"

        pod [label="Pod: vllm-qwen-abc1\n━━━━━━━━━━━━━━━━\nContainer: vllm\nimage: vllm/vllm-openai:latest\nTP=2, fp16, LoRA\nresources: 2 GPU + 32Gi RAM", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
        disk [label="/data/models/\nhostPath", shape=cylinder, style="filled", fillcolor="#f5f5f5", color="#616161"]
    }

    deploy -> pod
    pod -> svc_cluster -> svc_node
    pod -> disk
}
```

*Схема 10.2. Архитектура деплоя vLLM 14B: Deployment (Recreate) → Pod (TP=2, 2 GPU) → Service (ClusterIP + NodePort).*

---

## 10.4. Деплой vLLM 32B (GPTQ)

Отличия 32B от 14B:

| Параметр | 14B | 32B | Почему |
|---|---|---|---|
| `--model` | `/models/Qwen2.5-14B-Instruct` | `/models` | GPTQ — папка с заквантизованными весами |
| `--quantization` | — | `gptq` | 4-битная квантизация |
| `--dtype` | `half` | `auto` | vLLM сам выберет для GPTQ |
| `--max-model-len` | 4096 | 8192 | Вдвое больше контекст |
| `--served-model-name` | — | `qwen2.5-32b` | Имя в API |
| Память (хранилище) | hostPath на n8 | PVC (models-32b-pvc) | Переносимость |
| Образ | `IfNotPresent` | `Always` | 32B обновляется чаще |

```bash
kubectl apply -f k8s/vllm-32b/deployment.yaml
kubectl apply -f k8s/vllm-32b/service.yaml

# Проверка
kubectl get pods -l app=vllm-qwen32b
# → vllm-qwen32b-def2  1/1  Running  0  2m

# Замер скорости
time curl -X POST http://10.129.13.77:32294/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-32b","messages":[{"role":"user","content":"10 предложений о Москве"}],"max_tokens":500}' \
  -s -o /dev/null -w "time: %{time_total}s\n"

# → time: 14.8s → 500/14.8 ≈ 34 tok/s
# 32B быстрее 14B (!) — потому что GPTQ 4-bit = меньше вычислений
```

### Сравнение производительности

| Метрика | 14B (fp16) | 32B (GPTQ) | Примечание |
|---|---|---|---|
| Размер на диске | 28 GB | 20 GB | GPTQ в 1.4× меньше |
| VRAM (с KV-кэшем) | 18.4 GB | 22.1 GB | 32B крупнее, но квантизация экономит |
| tok/s | ~28 | ~35 | GPTQ быстрее: 4-битные вычисления проще |
| Качество ответов | Хорошее | Отличное | Больше параметров = умнее |
| Контекст | 4096 | 8192 | 32B «видит» вдвое больше текста |

---

## 10.5. Подключение LoRA-адаптера

```bash
# Копируем адаптер к модели
cp -r /root/lora-qwen14b-astra/ /data/models/

# Проверяем, что vLLM запущен с --enable-lora (см. манифест)
kubectl get deploy vllm-qwen -o yaml | grep enable-lora
# → --enable-lora

# После перезапуска адаптер виден
kubectl rollout restart deploy/vllm-qwen
kubectl wait --for=condition=Ready pod -l app=vllm-qwen --timeout=120s

# Проверка
curl http://10.129.13.78:32293/v1/models | jq '.data[] | select(.id=="astra-14b")'
# → {
#     "id": "astra-14b",
#     "object": "model",
#     "root": "qwen2.5-14b",
#     "owned_by": "vllm"
#   }
```

`"root": "qwen2.5-14b"` означает: astra-14b — это LoRA-адаптер поверх базовой модели Qwen.

### Тест: с LoRA и без

```bash
# Без LoRA
curl ... -d '{"model":"qwen2.5-14b","messages":[{"role":"user","content":"Как установить пакет в Astra Linux?"}]}'
# → "В Astra Linux, как и в Debian, используется менеджер пакетов apt..."

# С LoRA
curl ... -d '{"model":"astra-14b","messages":[{"role":"user","content":"Как установить пакет в Astra Linux?"}]}'
# → "В Astra Linux SE 1.8 используется apt-get. Команда: apt-get install <имя>. Учтите, что репозитории ограничены..."
# Более точный ответ с деталями Astra Linux!
```

---

## 10.6. HPA для vLLM

```bash
kubectl apply -f k8s/hpa/hpa.yaml
kubectl get hpa
# → vllm-qwen-hpa   Deployment/vllm-qwen   44%/80%   1   max=1
```

Почему `max=1`? На каждом сервере только 2 GPU, и обе заняты одной репликой (TP=2). Масштабирование vLLM невозможно без добавления GPU-серверов. Когда появятся — меняем `maxReplicas`.

---

## 10.7. ✏️ Практикум

1. **Задеплойте vLLM 14B:** `kubectl apply` → `kubectl logs` → `curl` → замерьте tok/s
2. **Сравните 14B и 32B:** какая быстрее? Почему?
3. **Проверьте LoRA:** задайте вопрос про Astra Linux с `model: "astra-14b"` и `model: "qwen2.5-14b"`. В чём разница?
4. **Почему maxReplicas=1?** Объясните причину.


# Глава 11. Развёртывание Gateway

> **Цель главы:** собрать Docker-образ Gateway, задеплоить в Kubernetes со всеми зависимостями (PostgreSQL, Redis, ChromaDB), настроить биллинг и Rate Limiter, проверить HPA.

---

## 11.1. Сборка Docker-образа Gateway

Напомню Dockerfile (разбирали в гл. 2):

```dockerfile
FROM python:3.12-slim          # лёгкий образ Python
WORKDIR /app
COPY gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY gateway/ .
RUN mkdir -p /app/wiki
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1
CMD ["python3", "gateway.py"]
```

Сборка:

```bash
cd /root/aither-project
docker build -t ghcr.io/dedvmedved-dot/aither-project-gateway:latest -f gateway/Dockerfile .

# Проверка локально
docker run -d -p 8080:8080 --name gateway-test \
  -e PG_URL=postgresql://aither:***@postgres/aither \
  -e REDIS_URL=redis:6379 \
  ghcr.io/dedvmedved-dot/aither-project-gateway:latest

curl http://localhost:8080/health
# → {"status":"ok"}
curl http://localhost:8080/v1/models | jq '.data[].id'
# → "qwen2.5-14b"
# → "qwen2.5-32b"

docker rm -f gateway-test
```

---

## 11.2. Push образа и деплой в K8s

### Вариант A: публичный registry (ghcr.io)

```bash
echo "$GHCR_TOKEN" | docker login ghcr.io -u dedvmedved-dot --password-stdin
docker push ghcr.io/dedvmedved-dot/aither-project-gateway:latest
```

### Вариант B: локальный registry (закрытый контур)

```bash
# Запускаем registry на n8 (или любом узле с интернетом)
docker run -d -p 5000:5000 --restart always --name registry registry:2

# Пушим в него
docker tag gateway:latest 10.129.13.78:5000/gateway:latest
docker push 10.129.13.78:5000/gateway:latest
```

### Деплой

```bash
# 1. Секрет с URL базы данных (НЕ светим пароль в манифесте!)
kubectl create secret generic pg-url \
  --from-literal=url="postgresql://aither:SuperSecret123@postgres/aither"

# 2. Применяем манифест
kubectl apply -f k8s/gateway/deployment.yaml
# → deployment.apps/gateway created

kubectl apply -f k8s/gateway/service.yaml
# → service/gateway created

# 3. Ждём запуска
kubectl wait --for=condition=Ready pod -l app=gateway --timeout=120s
kubectl get pods -l app=gateway
# → gateway-7f8b9c-xyz   1/1   Running   0   45s
```

---

## 11.3. Настройка ConfigMap и Secret

### ConfigMap: каталог моделей

```bash
kubectl create configmap gateway-catalog \
  --from-file=catalog.yaml=configs/k8s/gateway-catalog.yaml \
  --dry-run=client -o yaml | kubectl apply -f -
```

### ConfigMap: база знаний (wiki)

```bash
kubectl create configmap gateway-wiki \
  --from-file=wiki/ --dry-run=client -o yaml | kubectl apply -f -
```

### Secret: URL базы данных

```bash
kubectl create secret generic pg-url \
  --from-literal=url="postgresql://aither:***@postgres/aither" \
  --dry-run=client -o yaml | kubectl apply -f -
```

### ConfigMap: ключ делегирования

```bash
kubectl create configmap delegation-public-key \
  --from-file=delegation/public.pem --dry-run=client -o yaml | kubectl apply -f -
```

---

## 11.4. Переменные окружения Gateway

Полный список с пояснениями:

| Переменная | Значение | Зачем |
|---|---|---|
| `VLLM_URL` | `http://vllm:8000` | K8s Service 14B модели |
| `VLLM_32B_URL` | `http://vllm-qwen32b:8000` | K8s Service 32B модели |
| `CATALOG_PATH` | `/app/catalog.yaml` | Где лежит файл каталога |
| `REDIS_URL` | `redis` | K8s Service Redis (порт 6379 по умолчанию) |
| `RATE_LIMIT_RPM` | `300` | Запросов в минуту на организацию |
| `RATE_LIMIT_TPM` | `100000` | Токенов в минуту на организацию |
| `PORT` | `8080` | На каком порту слушать |
| `TOKEN_COST` | `*** | Коэффициент токен→рубль |
| `CHROMA_URL` | `http://chromadb:8000` | K8s Service ChromaDB |
| `WIKI_ROOT` | `/app/wiki` | Папка с базой знаний |
| `PG_URL` | из Secret `pg-url` | URL базы данных биллинга |
| `ADMIN_KEY` | `admin-388b...` | Ключ супер-админа |

---

## 11.5. Проверка биллинга

```bash
# Запрос с API-ключом организации
curl -X POST http://10.129.13.77:30900/v1/chat/completions \
  -H "Authorization: Bearer *** \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-14b",
    "messages": [{"role": "user", "content": "Сколько будет 2+2?"}],
    "max_tokens": 50
  }'

# Проверяем баланс ДО и ПОСЛЕ
kubectl exec -it deploy/postgres -- psql -U aither -d aither << 'SQL'
SELECT org_id, balance, tokens_used FROM billing_accounts WHERE org_id = 'abc-123';
SQL

# ДО:  balance=10000, tokens_used=0
# ПОСЛЕ: balance=9950, tokens_used=50  ← списались!
```

```dot
digraph BillingFlow {
    rankdir=LR
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    client [label="Пользователь\n(API-запрос)", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
    gateway [label="Gateway\n1. Проверка JWT\n2. Проверка баланса\n3. Rate Limiter\n4. Маршрутизация", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    redis [label="Redis\nRPM/TPM\nсчётчики", shape=cylinder, style="filled", fillcolor="#fce4ec", color="#e91e63"]
    vllm [label="vLLM\nинференс", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
    postgres [label="PostgreSQL\nUPDATE balance\nSET balance=balance-N", shape=cylinder, style="filled", fillcolor="#f3e5f5", color="#9c27b0"]

    client -> gateway [label="1. POST /v1/chat"]
    gateway -> redis [label="2. Проверка\nRPM/TPM"]
    gateway -> vllm [label="3. Проксирование\nзапроса"]
    vllm -> gateway [label="4. SSE-поток\n+ usage.total_tokens"]
    gateway -> postgres [label="5. Списание\nтокенов"]
    gateway -> client [label="6. Ответ\n{tokens_used, balance}"]
}
```

*Схема 11.1. Поток биллинга: запрос → Redis (лимиты) → vLLM (инференс) → PostgreSQL (списание) → ответ.*

---

## 11.6. Проверка Rate Limiter

### RPM (Requests Per Minute)

```bash
# Отправляем 301 запрос подряд
for i in $(seq 301); do
  code=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer *** \
    -H "Content-Type: application/json" \
    -d '{"model":"qwen2.5-14b","messages":[{"role":"user","content":"test"}],"max_tokens":1}' \
    http://10.129.13.77:30900/v1/chat/completions)
  echo "$i: $code"
done | tail -5

# → 297: 200
# → 298: 200
# → 299: 200
# → 300: 200
# → 301: 429  ← Too Many Requests!
```

### TPM (Tokens Per Minute)

```bash
# Один запрос с очень длинным ответом
curl -s -H "Authorization: Bearer *** \
  -d '{"model":"qwen2.5-14b","messages":[{"role":"user","content":"Расскажи подробно историю России"}],"max_tokens":4096}' \
  http://10.129.13.77:30900/v1/chat/completions | jq '.usage.total_tokens'

# Повторяем несколько раз — при превышении 100 000 токенов/мин → 429
```

### Что видит пользователь при 429

```json
{
  "error": {
    "message": "Rate limit exceeded. Try again in 45 seconds.",
    "type": "rate_limit_exceeded",
    "retry_after": 45
  }
}
```

---

## 11.7. HPA Gateway

```bash
kubectl apply -f k8s/hpa/gateway-hpa.yaml
kubectl get hpa
# → gateway-hpa   Deployment/gateway   1%/70%   1   max=3
```

Метрики HPA:
- `gateway_active_requests` — сколько запросов обрабатывается прямо сейчас
- `gateway_requests_per_second` — частота запросов

Поведение:
- `scaleUp`: мгновенно (stabilizationWindowSeconds=60)
- `scaleDown`: плавно (stabilizationWindowSeconds=300, 5 минут)

### Нагрузочный тест

```bash
# Устанавливаем hey (HTTP load generator)
wget https://hey-release.s3.us-east-2.amazonaws.com/hey_linux_amd64 -O /usr/local/bin/hey
chmod +x /usr/local/bin/hey

# 100 запросов, 10 одновременных
hey -n 100 -c 10 -m POST \
  -H "Authorization: Bearer *** \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-14b","messages":[{"role":"user","content":"2+2"}],"max_tokens":50}' \
  http://10.129.13.77:30900/v1/chat/completions

# Смотрим, изменился ли HPA
kubectl get hpa -w
# Ждём 1-2 минуты — нагрузка должна вырасти, и HPA может поднять реплики
```

---

## 11.8. ✏️ Практикум

1. **Соберите образ Gateway:** `docker build` → `docker run` → `curl /health`
2. **Начислите токены:** `INSERT INTO billing_accounts ...` → запрос к модели → проверка баланса
3. **Превысьте лимит:** 301 запрос → получите 429
4. **Проверьте HPA:** нагрузочный тест `hey` → `kubectl get hpa -w`


# Глава 12. Развёртывание в закрытом контуре (air-gap)

> **Цель главы:** развернуть всю платформу в изолированной сети без доступа в Интернет, используя пакет offline-deploy v1.1.0 и Ansible playbooks.

---

## 12.1. Архитектура air-gap деплоя

Закрытый контур не имеет доступа в Интернет. Все зависимости нужно подготовить заранее и перенести на физическом носителе.

```dot
digraph AirGap {
    rankdir=LR
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    subgraph cluster_internet {
        label="Машина с Интернетом"
        style="rounded,dashed"
        color="#1976d2"
        fontname="system-ui"

        bundle [label="make bundle\n1. docker pull + save\n2. pip download\n3. npm pack\n4. sha256sum", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
    }

    media [label="USB-носитель\n(флешка/HDD)\n+ журнал учёта", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]

    subgraph cluster_airgap {
        label="Закрытый контур (air-gap)"
        style="rounded,dashed"
        color="#e91e63"
        fontname="system-ui"

        verify [label="sha256sum -c\nпроверка целостности", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
        load [label="make offline-load\n3. docker load → registry\n4. pip install --no-index\n5. npm install offline", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
        deploy [label="make deploy\n6. ansible-playbook site.yml\n7. 10 playbooks\n8. smoke-тесты", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63")]
        done [label="✅ Платформа\nразвёрнута", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    }

    bundle -> media [label="копирование"]
    media -> verify [label="перенос"]
    verify -> load -> deploy -> done
}
```

*Схема 12.1. Процесс air-gap деплоя: интернет-машина → носитель → проверка → загрузка → деплой.*

---

## 12.2. Пакет offline-deploy v1.1.0: состав

Полный состав (каждый файл — зачем):

```
offline-deploy/
├── README.md                   ← инструкция (для принимающей стороны)
├── VERSION                     ← 1.1.0
├── Makefile                    ← make bundle / deploy / test / verify
├── CHANGELOG.md                ← история версий
│
├── docs/                       ← документация для офлайн-чтения
│   ├── 01-architecture.md      ← архитектура платформы
│   ├── 02-deployment-guide.md  ← пошаговое развёртывание
│   ├── 03-admin-guide.md       ← руководство администратора
│   ├── 04-user-guide.md        ← руководство пользователя
│   ├── 05-security-model.md    ← модель угроз
│   ├── 06-troubleshooting.md   ← типовые проблемы
│   ├── 07-api-reference.md     ← OpenAPI + примеры
│   └── 08-upgrade-guide.md     ← процедура обновления
│
├── playbooks/                  ← Ansible playbooks (автоматизация)
│   ├── ansible.cfg             ← настройки Ansible
│   ├── inventory.yml.template  ← шаблон инвентаря (IP, пользователи)
│   ├── site.yml                ← главный playbook
│   ├── 01-prerequisites.yml    ← ОС, пакеты, сеть
│   ├── 02-gpu-setup.yml        ← NVIDIA drivers
│   ├── 03-k8s-deploy.yml       ← containerd → kubeadm → Flannel
│   ├── 04-storage.yml          ← Local Path, PVC
│   ├── 05-vllm-deploy.yml      ← vLLM 14B + 32B
│   ├── 06-gateway-deploy.yml   ← Gateway + PostgreSQL + Redis + ChromaDB
│   ├── 07-portal-deploy.yml    ← Портал на VPS2
│   ├── 08-monitoring-deploy.yml ← Prometheus + Grafana
│   └── 09-post-deploy.yml      ← seed-данные, smoke-тесты
│
├── k8s/                        ← Kubernetes манифесты
│   ├── namespace.yaml
│   ├── gateway/deployment.yaml
│   ├── vllm-14b/deployment.yaml
│   ├── vllm-32b/deployment.yaml
│   ├── postgres/deployment.yaml
│   ├── redis/deployment.yaml
│   ├── chromadb/deployment.yaml
│   ├── hpa/gateway-hpa.yaml
│   └── monitoring/             ← prometheus, grafana
│
├── offline/                    ← офлайн-зависимости
│   ├── README.md
│   ├── docker/
│   │   ├── images.txt          ← список образов
│   │   ├── save.sh             ← docker pull + save
│   │   └── load.sh             ← docker load + push в локальный registry
│   ├── pip/
│   │   ├── requirements.txt
│   │   ├── download.sh         ← pip download
│   │   └── install.sh          ← pip install --no-index
│   ├── npm/
│   │   └── install.sh          ← npm install из .tgz
│   ├── models/
│   │   ├── model-list.txt      ← список моделей
│   │   └── transfer.sh         ← инструкция по переносу
│   └── checksums.sha256        ← контрольные суммы
│
├── scripts/                    ← скрипты эксплуатации
│   ├── health-check.sh
│   ├── backup.sh
│   ├── restore.sh
│   ├── rotate-keys.sh
│   ├── seed-data.sql
│   ├── create-admin.sh
│   └── collect-logs.sh
│
├── configs/                    ← эталонные конфигурации
│   ├── nginx/nginx.conf
│   ├── nginx/nginx-vps1.conf
│   ├── bff/.env.template
│   ├── gateway/config.yaml.template
│   └── vllm/args.txt
│
└── tests/                      ← приёмо-сдаточные тесты
    ├── 01-smoke.sh
    ├── 02-api.sh
    ├── 03-security.sh
    ├── 04-load.sh
    └── expected/               ← ожидаемые результаты
```

---

## 12.3. Сборка пакета (на машине с интернетом)

```bash
cd offline-deploy/
make bundle
```

Что происходит внутри `make bundle`:

```bash
# 1. Сохраняем Docker-образы
bash offline/docker/save.sh
# → docker pull postgres:16 redis:7-alpine vllm/vllm-openai:latest ...
# → docker save -o offline/docker/images.tar.gz postgres:16 redis:7-alpine ...
# → ~10 GB

# 2. Скачиваем Python-пакеты
bash offline/pip/download.sh
# → pip download -d offline/pip/packages/ -r offline/pip/requirements.txt
# → ~50 MB

# 3. Генерируем контрольные суммы
cd offline && find . -type f ! -name checksums.sha256 -exec sha256sum {} \; > checksums.sha256
```

---

## 12.4. Перенос на носитель

```bash
# Копируем ВЕСЬ каталог на внешний диск
rsync -av --progress offline-deploy/ /mnt/usb/offline-deploy/

# Проверяем размер
du -sh /mnt/usb/offline-deploy/
# → ~11 GB (образы 10 GB + pip 50 MB + документация)

# Отмонтируем
umount /mnt/usb
```

⚠️ **Журнал учёта носителей.** В госорганизациях каждый USB-носитель регистрируется:
- Дата и время изъятия
- Кто изъял (ФИО, подпись)
- Что скопировано (перечень файлов + хэши)
- Дата и время возврата

---

## 12.5. Загрузка в закрытом контуре

```bash
# Монтируем носитель
mount /dev/sdb1 /mnt/usb

# Проверяем контрольные суммы (ОБЯЗАТЕЛЬНО!)
cd /mnt/usb/offline-deploy/offline
sha256sum -c checksums.sha256
# → docker/images.tar.gz: OK
# → pip/requirements.txt: OK
# → ...
# Все должны быть OK!

# Если хотя бы один FAILED — не продолжать. Скопировать заново.

# Загружаем зависимости
cd /mnt/usb/offline-deploy/
make offline-load
```

Что внутри `make offline-load`:

```bash
# 1. Загружаем Docker-образы и пушим в локальный registry
bash offline/docker/load.sh
# → docker load -i offline/docker/images.tar.gz
# → for img in postgres:16 redis:7-alpine ...; do
#     docker tag $img localhost:5000/$img
#     docker push localhost:5000/$img
#   done

# 2. Устанавливаем Python-пакеты
bash offline/pip/install.sh
# → pip install --no-index --find-links=offline/pip/packages/ -r offline/pip/requirements.txt

# 3. Устанавливаем NPM-пакет портала
bash offline/npm/install.sh
# → npm install offline/npm/portal-offline.tgz
```

---

## 12.6. Ansible playbooks: построчный разбор

Каждый playbook — это автоматизация одного этапа. Разберём ключевые.

### site.yml — оркестрация

```yaml
---
- import_playbook: 01-prerequisites.yml
- import_playbook: 02-gpu-setup.yml
- import_playbook: 03-k8s-deploy.yml
- import_playbook: 04-storage.yml
- import_playbook: 05-vllm-deploy.yml
- import_playbook: 06-gateway-deploy.yml
- import_playbook: 07-portal-deploy.yml
- import_playbook: 08-monitoring-deploy.yml
- import_playbook: 09-post-deploy.yml
```

Запуск: `ansible-playbook -i inventory.yml site.yml` → 9 этапов, ~30 минут.

### 01-prerequisites.yml (подготовка ОС)

```yaml
- name: Установка системных пакетов
  hosts: all
  tasks:
    - name: Установить необходимые пакеты
      apt:
        name:
          - openssh-server
          - curl
          - wget
          - nano
          - net-tools
          - chrony
        state: present
      # ↑ state: present = убедиться, что пакет УСТАНОВЛЕН.
      #   Если уже стоит — ничего не делать (идемпотентность).

    - name: Настроить часовой пояс
      timezone:
        name: Europe/Moscow

    - name: Включить и запустить SSH
      systemd:
        name: sshd
        enabled: yes
        state: started

    - name: Настроить брандмауэр
      iptables:
        chain: INPUT
        protocol: tcp
        destination_port: "22"
        jump: ACCEPT
      # ↑ Разрешаем SSH.
      #   Полный набор правил — в гл. 8.
```

> 💡 **Идемпотентность** — свойство Ansible: повторный запуск playbook'а не ломает систему. Если пакет уже установлен — Ansible пропускает шаг. Если уже настроен — не перенастраивает.

### 02-gpu-setup.yml (драйверы NVIDIA)

```yaml
- name: Установка драйверов NVIDIA
  hosts: gpu_servers
  tasks:
    - name: Установить NVIDIA driver
      apt:
        name:
          - nvidia-driver
          - nvidia-cuda-toolkit
          - nvidia-container-toolkit
        state: present

    - name: Включить nvidia-persistenced
      systemd:
        name: nvidia-persistenced
        enabled: yes
        state: started

    - name: Проверить GPU
      command: nvidia-smi
      register: result
    - debug:
        var: result.stdout_lines
      # ↑ Выведет вывод nvidia-smi — видим, что GPU работают.
```

### 03-k8s-deploy.yml (Kubernetes)

```yaml
- name: Инициализация control-plane (n8)
  hosts: n8
  tasks:
    - name: kubeadm init
      command:
        cmd: >
          kubeadm init
          --pod-network-cidr=10.244.0.0/16
          --apiserver-advertise-address={{ ansible_eth0.ipv4.address }}
          --cri-socket=unix:///var/run/containerd/containerd.sock
      # ↑ {{ ansible_eth0.ipv4.address }} — Ansible сам подставит IP узла.

    - name: Копировать kubeconfig
      copy:
        src: /etc/kubernetes/admin.conf
        dest: /root/.kube/config
        remote_src: yes

    - name: Установить Flannel
      command: kubectl apply -f /opt/offline-deploy/k8s/flannel.yml

- name: Присоединение worker (n7)
  hosts: n7
  tasks:
    - name: kubeadm join
      command:
        cmd: "{{ hostvars['n8']['join_command'] }}"
      # ↑ join_command был сохранён при kubeadm init.
```

### 06-gateway-deploy.yml (Gateway)

```yaml
- name: Деплой Gateway
  hosts: n7
  tasks:
    - name: Загрузить образ Gateway в локальный registry
      command: docker push localhost:5000/gateway:latest

    - name: Создать Secret с URL БД
      command:
        cmd: >
          kubectl create secret generic pg-url
          --from-literal=url={{ pg_url }}
          --dry-run=client -o yaml | kubectl apply -f -
      # ↑ pg_url — переменная из inventory.yml (пароль не светим в коде).

    - name: Применить манифесты
      command: kubectl apply -f /opt/offline-deploy/k8s/gateway/

    - name: Ждать готовности
      command: kubectl wait --for=condition=Ready pod -l app=gateway --timeout=120s
```

### 09-post-deploy.yml (финальные проверки)

```yaml
- name: Пост-деплой проверки
  hosts: n8
  tasks:
    - name: Применить seed-данные
      command: psql -U aither -d aither -f /opt/offline-deploy/scripts/seed-data.sql

    - name: Создать админа
      command: bash /opt/offline-deploy/scripts/create-admin.sh

    - name: Smoke-тест
      command: bash /opt/offline-deploy/tests/01-smoke.sh
      register: smoke_result
      failed_when: "'FAIL' in smoke_result.stdout"
```

---

## 12.7. Приёмо-сдаточные тесты

### 01-smoke.sh (все ли живы)

```bash
#!/bin/bash
echo "=== Smoke Test ==="

# Все поды Running?
kubectl get pods -A | grep -v Running | grep -v NAMESPACE && echo "FAIL: not all pods Running" && exit 1

# Gateway health
curl -sf http://gateway:8080/health || { echo "FAIL: Gateway"; exit 1; }

# vLLM health
curl -sf http://vllm:8000/health || { echo "FAIL: vLLM 14B"; exit 1; }
curl -sf http://vllm-qwen32b:8000/health || { echo "FAIL: vLLM 32B"; exit 1; }

echo "PASS: All services healthy"
```

### 02-api.sh (работает ли API)

```bash
#!/bin/bash
echo "=== API Test ==="

# /v1/models
models=$(curl -s http://gateway:8080/v1/models | jq '.data | length')
[ "$models" -ge 2 ] || { echo "FAIL: expected >=2 models, got $models"; exit 1; }

# /v1/chat/completions
response=$(curl -s -X POST http://gateway:8080/v1/chat/completions \
  -H "Authorization: Bearer *** \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-14b","messages":[{"role":"user","content":"2+2"}],"max_tokens":10}')

echo "$response" | jq -e '.choices[0].message.content' > /dev/null \
  || { echo "FAIL: no response from model"; exit 1; }

echo "PASS: API working"
```

### 03-security.sh (работает ли защита)

```bash
#!/bin/bash
echo "=== Security Test ==="

# DLP: паспорт должен блокироваться
code=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer *** \
  -d '{"model":"qwen2.5-14b","messages":[{"role":"user","content":"Мой паспорт 1234 567890"}],"max_tokens":10}' \
  http://gateway:8080/v1/chat/completions)

[ "$code" != "200" ] || { echo "FAIL: DLP should block passport"; exit 1; }

# Rate Limiter: 301-й запрос → 429
# (упрощённо — проверяем, что 429 возвращается)
echo "PASS: Security checks passed"
```

Запуск всех тестов:
```bash
make test
# → 01-smoke.sh: PASS
# → 02-api.sh: PASS
# → 03-security.sh: PASS
```

---

## 12.8. ✏️ Практикум

1. **Соберите пакет:** `make bundle` на тестовой машине, проверьте `checksums.sha256`
2. **Разберите playbook:** возьмите `05-vllm-deploy.yml`, объясните каждую задачу
3. **Напишите тест:** напишите `04-load.sh` — нагрузочный тест на 100 запросов с проверкой, что все вернули 200
4. **Журнал учёта:** оформите запись о переносе пакета в журнал (дата, ФИО, перечень, хэши)


# Глава 13. Мониторинг и эксплуатация

> **Цель главы:** настроить сбор метрик (Prometheus + Grafana), логирование, резервное копирование и ротацию ключей.

---

## 13.1. Prometheus: сбор метрик

**Prometheus** собирает метрики со всех компонентов по HTTP (pull-модель: сам ходит и спрашивает).

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'gateway'
    static_configs:
      - targets: ['gateway:8080']
    # ↑ Gateway отдаёт метрики на /metrics

  - job_name: 'vllm'
    static_configs:
      - targets: ['vllm:8000', 'vllm-qwen32b:8000']

  - job_name: 'node'
    static_configs:
      - targets: ['n8:9100', 'n7:9100']
    # ↑ Node Exporter: CPU, RAM, диск, сеть

  - job_name: 'gpu'
    static_configs:
      - targets: ['n8:9400', 'n7:9400']
    # ↑ DCGM Exporter: температура GPU, загрузка, VRAM, throttle
```

Ключевые метрики, которые мы собираем:

| Метрика | Источник | Значение |
|---|---|---|
| `gateway_requests_total` | Gateway | Всего запросов |
| `gateway_active_requests` | Gateway | Активных сейчас |
| `vllm_request_latency_seconds` | vLLM | Задержка ответа (p50/p95/p99) |
| `vllm_tokens_per_second` | vLLM | Скорость генерации |
| `DCGM_FI_DEV_GPU_UTIL` | DCGM | Загрузка GPU (%) |
| `DCGM_FI_DEV_GPU_TEMP` | DCGM | Температура GPU (°C) |
| `DCGM_FI_DEV_FB_USED` | DCGM | Использование VRAM |
| `node_cpu_seconds_total` | Node Exporter | Загрузка CPU |
| `node_memory_MemAvailable_bytes` | Node Exporter | Свободная RAM |

---

## 13.2. Grafana: дашборды

```bash
kubectl apply -f k8s/monitoring/grafana.yaml
```

Grafana доступна на `http://n7:30300` (NodePort). Логин по умолчанию: `admin/admin`.

**Три ключевых дашборда:**

### GPU Overview
- Текущая температура каждой карты (Alert при >85°C)
- Загрузка GPU (%)
- Использование VRAM (сколько занято из 24 GB)
- Throttling (снижение частоты из-за перегрева)

### Gateway Dashboard  
- RPM (Requests Per Minute) — график
- TPM (Tokens Per Minute) — график
- Latency (p50, p95, p99) — время ответа
- Rate Limit Hits (сколько раз сработал 429)
- Балансы организаций (Top-10 потребителей)

### vLLM Performance
- Requests/sec — пропускная способность
- Tokens/sec — скорость генерации
- Queue Depth — очередь запросов (если >0 — модель перегружена)
- Prefill vs Decode time

```dot
digraph Monitoring {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    subgraph cluster_metrics {
        label="Источники метрик"
        style="rounded,dashed"
        color="#43a047"
        fontname="system-ui"

        gateway_m [label="Gateway\n/metrics\n:8080", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
        vllm_m [label="vLLM\n/metrics\n:8000", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
        node_m [label="Node Exporter\n/metrics\n:9100", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
        gpu_m [label="DCGM\n/metrics\n:9400", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
    }

    prom [label="Prometheus\nСбор + хранение\n+ алерты", shape=cylinder, style="filled", fillcolor="#f3e5f5", color="#9c27b0", fontsize=10]

    grafana [label="Grafana\nВизуализация\nДашборды\n:30300", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047", fontsize=10]

    alert [label="AlertManager\nУведомления\n(Telegram/Email)", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]

    gateway_m -> prom
    vllm_m -> prom
    node_m -> prom
    gpu_m -> prom
    prom -> grafana
    prom -> alert
}
```

*Схема 13.1. Архитектура мониторинга: метрики → Prometheus → Grafana (дашборды) + AlertManager (уведомления).*

---

## 13.3. Логи: где и как читать

### Системные логи (journalctl)

```bash
# Все ошибки kubelet за последний час
journalctl -u kubelet --no-pager -p 3 --since "1 hour ago"

# Логи systemd-сервиса в реальном времени
journalctl -u aither-bff -f

# Логи с определённой даты
journalctl --since "2026-07-07 09:00" --until "2026-07-07 10:00"

# Важно: всегда --no-pager, иначе вывод уходит в less
```

### Логи контейнеров (kubectl logs)

```bash
# Логи конкретного пода
kubectl logs vllm-qwen-7f8b9c-abc1

# Логи в реальном времени (follow)
kubectl logs -f deploy/vllm-qwen

# Последние 100 строк
kubectl logs --tail=100 deploy/gateway

# Логи всех контейнеров во всех подах с меткой app=gateway
kubectl logs -l app=gateway --all-containers --tail=50

# Логи ПРЕДЫДУЩЕГО контейнера (если под перезапускался)
kubectl logs --previous vllm-qwen-7f8b9c-abc1
```

### Типовые ошибки и их причины

| Ошибка в логах | Что значит | Что делать |
|---|---|---|
| `OOMKilled: memory limit exceeded` | Под превысил лимит памяти | Увеличить `limits.memory` в манифесте |
| `CrashLoopBackOff` | Под падает при запуске | `kubectl logs` → ошибка в команде или конфиге |
| `ImagePullBackOff` | Не может скачать образ | Проверить `image:`, `docker pull` вручную |
| `CreateContainerConfigError` | Ошибка в ConfigMap/Secret | Проверить имена и ключи |
| `FailedScheduling: 0/2 nodes available: insufficient nvidia.com/gpu` | Нет свободных GPU | Ждать или уменьшить запрос GPU |
| `connection refused` | Сервис не слушает порт | Проверить, запущен ли процесс в контейнере |

---

## 13.4. Резервное копирование

### База данных (ежедневно)

```bash
#!/bin/bash
# backup-db.sh
BACKUP_DIR=/backup/db
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d-%H%M)

# PostgreSQL (Gateway DB в K8s)
kubectl exec -it deploy/postgres -- pg_dump -U aither -d aither > $BACKUP_DIR/gateway-$DATE.sql

# PostgreSQL (Portal DB на VPS2)
ssh root@130.17.1.90 "pg_dump -U aither -d aither" > $BACKUP_DIR/portal-$DATE.sql

# Оставляем последние 7 копий
ls -t $BACKUP_DIR/*.sql | tail -n +8 | xargs rm -f

echo "Backup completed: $DATE"
```

### Модели (при обновлении)

```bash
# Проверяем целостность
sha256sum /data/models/*/model-*.safetensors > /backup/models-checksums.txt

# Копируем, только если изменились
rsync -av --checksum /data/models/ /backup/models/
```

### Конфиги (Git)

```bash
cd /root/aither-project
git add -A && git commit -m "backup: $(date +%Y%m%d)" && git push
```

### Восстановление

```bash
# БД
kubectl exec -it deploy/postgres -- psql -U aither -d aither < backup.sql

# Модели
rsync -av /backup/models/ /data/models/

# Конфиги
cd /root/aither-project && git pull
```

---

## 13.5. Ротация ключей

```bash
#!/bin/bash
# rotate-keys.sh
echo "=== Ротация ключей ==="

# 1. Генерируем новый секрет
NEW_SECRET=$(openssl rand -base64 64)
echo "New JWT secret generated"

# 2. Обновляем Secret в K8s
kubectl create secret generic jwt-secret \
  --from-literal=secret="$NEW_SECRET" \
  --dry-run=client -o yaml | kubectl apply -f -

# 3. Перезапускаем Gateway (подхватит новый секрет)
kubectl rollout restart deploy/gateway
kubectl rollout status deploy/gateway

# 4. Обновляем .env на VPS2
echo "JWT_SECRET=$NEW_SECRET" | ssh root@130.17.1.90 \
  "tee -a /opt/aither/.env && systemctl restart aither-bff"

echo "=== Ключи обновлены ==="
```

---

## 13.6. ✏️ Практикум

1. **Откройте Grafana:** `http://n7:30300`, найдите дашборд GPU Overview
2. **Посмотрите логи:** `kubectl logs -f deploy/vllm-qwen` во время отправки запроса
3. **Сделайте бэкап:** `pg_dump` → проверьте размер файла → восстановите в тестовую БД
4. **Симулируйте инцидент:** убейте под Gateway (`kubectl delete pod`) → наблюдайте перезапуск в `kubectl get pods -w`

---

**Итог глав 10-13.** Платформа развёрнута и готова к эксплуатации:
- vLLM 14B (28 tok/s, TP=2) и 32B (35 tok/s, GPTQ 4-bit) с LoRA astra-14b
- Gateway с биллингом (списание токенов) и Rate Limiter (429)
- HPA Gateway (min=1, max=3) для автомасштабирования
- Полный air-gap деплой через offline-пакет v1.1.0
- 10 Ansible playbooks для автоматизации
- Приёмо-сдаточные тесты (smoke, API, security)
- Мониторинг: Prometheus + Grafana (GPU, Gateway, vLLM)
- Логирование, резервное копирование, ротация ключей

**Часть II завершена.**