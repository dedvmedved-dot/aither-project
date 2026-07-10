# Часть I. Теоретические основы

---

# Глава 1. Фундамент: компьютер, Linux, сеть

> **Цель главы:** понять, из чего состоит сервер, как работает операционная система Linux и как компьютеры общаются друг с другом по сети. После этой главы вы сможете осмысленно смотреть на сервер YADRO VEGMAN S320 и понимать, что к чему.

---

## 1.1. Что такое сервер и чем он отличается от ноутбука

Представьте, что вы зашли в серверную — комнату с кондиционером, где гудит множество железных ящиков. Это **серверы** (server — «обслуживающий»). Внешне они похожи на большие плоские ящики, которые вставляются в стойку (rack). Но внутри у них те же компоненты, что и в ноутбуке — просто гораздо мощнее, надёжнее и... без экрана.

Давайте разберём каждый компонент по порядку.

### Процессор (CPU — Central Processing Unit)

**Процессор** — это «мозг» компьютера. Он выполняет инструкции программ: складывает числа, сравнивает строки, пересылает данные. Каждую секунду процессор выполняет миллиарды операций.

У процессора есть **ядра** (cores). Раньше процессор мог делать только одно дело за раз. Потом научились делать вид, что несколько — быстро переключаясь (hyper-threading). А потом стали размещать несколько полноценных ядер на одном кристалле.

**Поток** (thread) — это одна «линия выполнения». Одно физическое ядро может выполнять 2 потока (технология Hyper-Threading у Intel, SMT у AMD). Поэтому в характеристиках пишут «28C/56T»:

> **28C/56T** = 28 физических ядер (Cores) / 56 логических потоков (Threads). Каждое ядро тянет 2 потока.

⚠️ **Важное примечание про наш сервер.** В YADRO VEGMAN S320 стоят 2 процессора Xeon 6258R. Каждый — 28 ядер / 56 потоков. В сумме сервер имеет 56 физических ядер и 112 потоков. Однако в документации мы всегда пишем **«28C/56T на сокет»** (на один процессорный разъём), а не складываем. Это стандартная практика в серверной документации.

**Тактовая частота** измеряется в гигагерцах (GHz) — сколько операций ядро делает за секунду. Xeon 6258R работает на частоте 2.7 GHz (базовая) и до 4.0 GHz (турбо-режим).

> 🏭 **Аналогия.** Процессор — это завод. Ядра — цеха завода. Потоки — конвейерные линии в цехах. Тактовая частота — скорость конвейера. Чем больше ядер и выше частота — тем больше продукции в секунду.

```dot
digraph CPU {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=11]

    subgraph cluster_socket {
        label="Процессорный разъём (Socket LGA 3647)"
        style="rounded,dashed"
        color="#1976d2"
        fontname="system-ui"
        fontsize=12

        cpu [label="Xeon 6258R\n2.7–4.0 GHz\n28 ядер / 56 потоков", shape=box, style="rounded,filled", fillcolor="#e3f2fd", color="#1976d2"]
    }

    subgraph cluster_cores {
        label="28 физических ядер"
        style=rounded
        color="#43a047"
        fontname="system-ui"
        fontsize=10

        c1 [label="Ядро 1", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047", width=1]
        c2 [label="Ядро 2", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047", width=1]
        cdots [label="...", shape=plaintext]
        c28 [label="Ядро 28", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047", width=1]
    }

    subgraph cluster_threads {
        label="56 логических потоков (Hyper-Threading)"
        style=rounded
        color="#ff9800"
        fontname="system-ui"
        fontsize=10

        t1a [label="Поток 1", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800", width=0.7, fontsize=9]
        t1b [label="Поток 2", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800", width=0.7, fontsize=9]
    }

    cpu -> c1 -> t1a
    c1 -> t1b
}
```

*Схема 1.1. Устройство процессора: от разъёма до потоков.*

### Оперативная память (RAM — Random Access Memory)

**Оперативная память** — это «рабочий стол» компьютера. Пока компьютер работает, все программы и данные лежат в оперативной памяти. Когда компьютер выключается — содержимое RAM исчезает (поэтому она и называется «оперативной» — только для операций).

Память измеряется в гигабайтах (GB). Современный ноутбук имеет 8–16 GB. Сервер YADRO VEGMAN S320 имеет **754 GB** — почти в 50 раз больше. Зачем столько?

Потому что модели искусственного интеллекта загружаются в оперативную память и видеопамять целиком. Модель Qwen 2.5 32B в полном качестве занимает около 64 GB — и это только одна программа.

> 📋 **Аналогия.** RAM — это размер вашего рабочего стола. Чем больше стол, тем больше документов вы можете разложить перед собой одновременно. Жёсткий диск — это шкаф с папками: там всё хранится постоянно, но доставать оттуда дольше.

### Диск (SSD, HDD, NVMe)

**Диск** — это «шкаф» для постоянного хранения данных. В отличие от RAM, данные на диске сохраняются после выключения.

| Тип | Скорость | Объём | Цена | Применение |
|---|---|---|---|---|
| **HDD** (жёсткий диск) | ~150 MB/s | до 20 TB | дёшево | Архивы, бэкапы |
| **SATA SSD** | ~550 MB/s | до 8 TB | средне | Система, базы данных |
| **NVMe SSD** | ~3500 MB/s | до 4 TB | дорого | Модели ИИ, активные БД |
| **SAS SSD** | ~1200 MB/s | до 4 TB | дорого | Серверное (надёжность) |

В YADRO VEGMAN S320 стоит **42 TB SAS SSD** — это 42 000 гигабайт на быстрых серверных дисках. Здесь хранятся модели ИИ (каждая по 20–30 GB), базы данных, логи.

> 💡 **SAS** (Serial Attached SCSI) — серверный интерфейс подключения дисков. Отличается от обычного SATA повышенной надёжностью и скоростью. **SCSI** расшифровывается как Small Computer System Interface.

### Видеокарта (GPU — Graphics Processing Unit)

**Видеокарта** изначально создавалась для игр — чтобы быстро рисовать 3D-графику. Но оказалось, что её архитектура идеально подходит для вычислений, нужных искусственному интеллекту.

| | CPU (процессор) | GPU (видеокарта) |
|---|---|---|
| **Ядер** | 28–56 мощных | 4 000–16 000 простых |
| **Задача ядра** | Сложные вычисления | Много простых операций параллельно |
| **Аналогия** | 28 профессоров | 10 000 школьников |
| **Для ИИ** | Обучение (медленно) | Инференс (быстро) |

GPU от NVIDIA называется по схеме: **RTX 6000** = поколение RTX, модель 6000 (профессиональная серия). У него **24 GB** собственной памяти — **VRAM** (Video RAM). Модели ИИ загружаются в VRAM, потому что GPU имеет к ней очень быстрый доступ (~1 TB/s).

В сервере YADRO установлены **2 видеокарты RTX 6000**. Суммарно это 48 GB VRAM — достаточно для модели 32B в сжатом виде (GPTQ 4-bit, ~20 GB) или 14B в полном (28 GB).

> 🎮 **Почему именно NVIDIA?** У NVIDIA есть технология **CUDA** (Compute Unified Device Architecture) — язык программирования для видеокарт. Все библиотеки для ИИ (PyTorch, vLLM) написаны под CUDA. AMD и Intel пытаются догнать, но пока NVIDIA — стандарт.

```dot
digraph GPU {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=10]

    gpu [label="NVIDIA RTX 6000", shape=box, style="rounded,filled", fillcolor="#fce4ec", color="#e91e63", fontsize=12]

    subgraph cluster_vram {
        label="VRAM: 24 GB"
        style="rounded,dashed"
        color="#9c27b0"
        fontname="system-ui"

        v1 [label="Модель ИИ\n14B: ~28 GB\n(не влезает!)", shape=box, style="filled", fillcolor="#f3e5f5", color="#9c27b0"]
        v2 [label="Модель ИИ\n14B (half): ~14 GB ✅", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
        v3 [label="KV-кэш\n~4 GB", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
        v4 [label="Свободно\n~6 GB", shape=box, style="filled", fillcolor="#f5f5f5", color="#bdbdbd"]
    }

    subgraph cluster_cores {
        label="CUDA-ядра: 4 608 шт."
        style=rounded
        color="#ff9800"
        fontname="system-ui"

        c [label="Параллельные вычисления\n1 операция на ядро\nза 1 такт", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    }

    gpu -> v1
    gpu -> c
}
```

*Схема 1.2. Устройство GPU NVIDIA RTX 6000. Модель 14B в полном качестве (bf16) занимает 28 GB и не влезает в 24 GB VRAM — поэтому используют половинную точность (half / fp16), что даёт ~14 GB.*

### Блок питания, охлаждение, BMC

**Блок питания** — преобразует 220V из розетки в 12V/5V/3.3V для компонентов. В серверах их обычно два (дублирование): если один выйдет из строя, второй продолжит питать сервер.

**Охлаждение** — серверные процессоры и видеокарты выделяют много тепла (сотни ватт). Охлаждение — это вентиляторы, которые прогоняют воздух через сервер. В серверной всегда шумно и холодно (кондиционеры работают круглосуточно).

**BMC** (Baseboard Management Controller) — это маленький отдельный компьютер внутри сервера. Он работает даже когда сам сервер выключен. Через BMC можно:
- Включить/выключить сервер удалённо
- Увидеть экран сервера (как будто вы подключили монитор)
- Загрузить ISO-образ операционной системы
- Смотреть температуру, напряжение, логи

BMC имеет свой IP-адрес и веб-интерфейс (обычно порт 443 или 9443). В нашем кластере BMC сервера n7 доступен через цепочку пробросов: `n7:9443 → socat → VPS2:19443 → VPS1:443`.

---

## 1.2. Операционная система Linux

### Что такое ОС

**Операционная система** — это программа, которая управляет всем компьютером. Без ОС компьютер — просто груда железа. ОС даёт программам доступ к процессору, памяти, диску и сети.

ОС состоит из двух частей:

1. **Ядро** (kernel) — самая главная часть. Работает в привилегированном режиме. Управляет процессами, памятью, драйверами устройств.
2. **Пользовательское пространство** (userspace) — все остальные программы: командная оболочка (shell), текстовые редакторы, веб-серверы, базы данных.

```dot
digraph OS {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=10]

    subgraph cluster_userspace {
        label="Пользовательское пространство (Userspace)"
        style="rounded,dashed"
        color="#1976d2"
        fontname="system-ui"
        fontsize=11

        app [label="Программы\n(BFF, Gateway, nginx)", shape=box, style="rounded,filled", fillcolor="#e3f2fd", color="#1976d2"]
        shell [label="Командная оболочка\n(bash)", shape=box, style="rounded,filled", fillcolor="#e3f2fd", color="#1976d2"]
        libc [label="Библиотеки\n(glibc)", shape=box, style="rounded,filled", fillcolor="#e3f2fd", color="#1976d2"]
    }

    kernel [label="Ядро Linux\n— управление процессами\n— управление памятью\n— драйверы устройств\n— сетевой стек", shape=box, style="rounded,filled", fillcolor="#fce4ec", color="#e91e63", fontsize=11]

    subgraph cluster_hardware {
        label="Аппаратура (Hardware)"
        style="rounded"
        color="#616161"
        fontname="system-ui"
        fontsize=11

        cpu [label="CPU", shape=box, style="filled", fillcolor="#f5f5f5", color="#616161"]
        ram [label="RAM", shape=box, style="filled", fillcolor="#f5f5f5", color="#616161"]
        disk [label="Диск", shape=box, style="filled", fillcolor="#f5f5f5", color="#616161"]
        net [label="Сеть", shape=box, style="filled", fillcolor="#f5f5f5", color="#616161"]
    }

    app -> libc -> kernel
    shell -> libc
    kernel -> cpu
    kernel -> ram
    kernel -> disk
    kernel -> net
}
```

*Схема 1.3. Архитектура операционной системы. Программы не общаются с железом напрямую — только через ядро.*

### Linux: история и дистрибутивы

**Linux** — это ядро операционной системы, созданное Линусом Торвальдсом в 1991 году. В отличие от Windows (проприетарная, исходный код закрыт), Linux — **свободное программное обеспечение** (open source). Любой может посмотреть, как он устроен, изменить и распространять.

Но ядро само по себе бесполезно — нужны программы. Поэтому существуют **дистрибутивы** — готовые наборы: ядро Linux + программы + установщик.

| Дистрибутив | Основан на | Для чего | Используется в Aither? |
|---|---|---|---|
| **Astra Linux SE** | Debian | Госсектор РФ, защита информации | ✅ На n7 и n8 |
| Ubuntu | Debian | Серверы, рабочие станции | ✅ На VPS1 |
| Debian | — | Стабильность, серверы | База для многих |
| CentOS / RED OS | RHEL | Серверы | Нет |

**Astra Linux Special Edition (SE) 1.8 «Смоленск»** — российский дистрибутив, сертифицированный для работы с государственной тайной. В нём есть:

- **Parsec** — модуль мандатного контроля доступа (каждому документу присваивается гриф секретности, и ОС следит, чтобы пользователь без допуска не мог прочитать секретный документ)
- Собственный репозиторий пакетов (защищён от внешних атак на цепочку поставок)
- Сертификаты ФСТЭК и ФСБ

⚠️ **Почему мы отключаем Parsec** (параметр `parsec=0`): он блокирует некоторые операции, которые нужны для работы Kubernetes и драйверов NVIDIA. В промышленной эксплуатации это решается настройкой политик Parsec, но для разработки проще его отключить.

### Терминал: командная строка

Серверы Linux не имеют графического интерфейса (окон, мыши). Всё управление — через **терминал** (командную строку). Это чёрное окно, в которое вы пишете команды.

Почему не мышкой?
- Автоматизация: можно написать скрипт (сценарий) из команд и выполнять его одной кнопкой
- Удалённое управление: командная строка передаётся по сети легко, а графика — тяжело
- Скорость: опытный администратор печатает команды быстрее, чем кликает мышью

**Первые команды:**

| Команда | Что делает | Пример |
|---|---|---|
| `ls` | **l**i**s**t — показать файлы в папке | `ls /root` |
| `cd` | **c**hange **d**irectory — перейти в папку | `cd /var/log` |
| `pwd` | **p**rint **w**orking **d**irectory — где я сейчас | `pwd` → `/root` |
| `cat` | con**cat**enate — показать содержимое файла | `cat /etc/hostname` |
| `less` | просмотр длинного файла с прокруткой | `less /var/log/syslog` |
| `grep` | **g**lobal **r**egular **e**xpression **p**rint — найти строку | `grep "error" log.txt` |
| `man` | **man**ual — справка по команде | `man ls` |
| `whoami` | показать текущего пользователя | `whoami` → `root` |

### Файловая система Linux

В Linux всё — файл. Жёсткий диск — файл (`/dev/sda`). Оперативная память — файл (`/dev/mem`). Настройки — файлы в `/etc`. Запущенные программы — файлы в `/proc`.

Файловая система — это **единое дерево**, начинающееся с корня `/`. Нет «диска C:» и «диска D:» как в Windows — все диски монтируются (подключаются) в какие-то папки этого дерева.

```dot
digraph FS {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    root [label="/\n(корень)", shape=folder, style="filled", fillcolor="#fce4ec", color="#e91e63", fontsize=11]

    bin [label="/bin\nбазовые команды", shape=folder, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
    etc [label="/etc\nконфигурация", shape=folder, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
    var [label="/var\nпеременные данные\n(логи, БД)", shape=folder, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
    root_home [label="/root\nдомашняя папка\nадминистратора", shape=folder, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
    mnt [label="/mnt\nточки монтирования\n(внешние диски)", shape=folder, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    proc [label="/proc\nинформация о процессах\n(виртуальная)", shape=folder, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    dev [label="/dev\nфайлы устройств", shape=folder, style="filled", fillcolor="#f3e5f5", color="#9c27b0"]

    root -> bin
    root -> etc
    root -> var
    root -> root_home
    root -> mnt
    root -> proc
    root -> dev

    etc_hostname [label="hostname", shape=note, style="filled", fillcolor="#f5f5f5"]
    etc_ssh [label="ssh/\nsshd_config", shape=note, style="filled", fillcolor="#f5f5f5"]
    etc -> etc_hostname
    etc -> etc_ssh

    var_log [label="log/\nsyslog", shape=note, style="filled", fillcolor="#f5f5f5"]
    var -> var_log

    mnt_models [label="models/\n(3.5 TB)\nмодели ИИ", shape=note, style="filled", fillcolor="#e8f5e9"]
    mnt -> mnt_models
}
```

*Схема 1.4. Файловая система Linux (основные каталоги). Папки отмечены как «folder», файлы — как «note».*

Ключевые каталоги:
- **`/etc`** — все настройки системы и программ. Хотите изменить имя компьютера? Файл `/etc/hostname`. Настроить сеть? `/etc/network/interfaces`.
- **`/var/log`** — все логи (журналы событий). Если что-то сломалось — смотрите сюда.
- **`/root`** — домашняя папка суперпользователя (администратора). Обычные пользователи живут в `/home/username`.
- **`/mnt`** — сюда подключают (монтируют) внешние диски. У нас там `/mnt/models` (3.5 TB) с моделями ИИ.
- **`/proc`** — виртуальная файловая система. Не занимает места на диске. Показывает информацию о запущенных процессах. `cat /proc/cpuinfo` — информация о процессоре.

### Процессы и systemd

**Процесс** — это запущенная программа. У каждого процесса есть:

- **PID** (Process ID) — уникальный номер
- **PPID** (Parent PID) — PID родительского процесса (того, кто запустил)
- Пользователь, от имени которого процесс работает
- Состояние: Running (работает), Sleeping (ждёт), Zombie (завершился, но не убран)

Команда `ps aux` показывает все процессы. `top` — процессы в реальном времени (как «Диспетчер задач»).

**systemd** — это «менеджер процессов». Он запускается самым первым (PID 1) и запускает всё остальное. Программы, которые должны работать всегда (веб-сервер, база данных), оформляются как **сервисы** (services) systemd.

| Команда | Что делает |
|---|---|
| `systemctl start nginx` | Запустить сервис nginx |
| `systemctl stop nginx` | Остановить |
| `systemctl restart nginx` | Перезапустить |
| `systemctl status nginx` | Состояние (работает/остановлен/ошибка) |
| `systemctl enable nginx` | Автозапуск при старте системы |
| `journalctl -u nginx` | Логи сервиса nginx |

⚠️ **Различие `ssh.service` и `sshd.service`:** `ssh` — это клиент (подключиться к другому серверу), `sshd` — демон (сервер, принимающий подключения). Буква «d» в конце означает **d**aemon (демон — фоновая служба).

### Пользователи и права

В Linux каждый файл и процесс принадлежит какому-то пользователю. Есть три уровня прав:

- **Владелец** (user) — тот, кто создал файл
- **Группа** (group) — несколько пользователей с общими правами
- **Остальные** (others) — все, кто не владелец и не в группе

Для каждого уровня можно разрешить: читать (r), записывать (w), исполнять (x).

```
-rwxr-xr--  1 root  root  1234  Jul 7 10:00  script.sh
 ─┬─ ─┬─ ─┬─
  │   │   └── права остальных (r— только чтение)
  │   └────── права группы (r-x читать и исполнять)
  └────────── права владельца (rwx всё можно)
```

- `root` — суперпользователь. Может всё. Неограниченный доступ.
- `sudo` (superuser do) — выполнить команду от имени root. Обычные пользователи используют `sudo` для администрирования, не входя под root.

> ⚠️ **Правило безопасности:** не работайте постоянно под root. Если ошибётесь командой — можете удалить систему. Используйте обычного пользователя и `sudo` для конкретных команд.

### ✏️ Практикум: первые шаги в Linux

Если у вас есть доступ к Linux-серверу (или виртуальной машине), выполните:

```bash
# Кто я?
whoami

# Какая система?
uname -a

# Сколько места на дисках?
df -h

# Сколько оперативной памяти?
free -h

# Какие сетевые интерфейсы?
ip a

# Создайте папку и файл
mkdir ~/test
echo "Привет, Aither!" > ~/test/hello.txt
cat ~/test/hello.txt
```

---

## 1.3. Компьютерные сети — от IP до HTTP

### IP-адрес: «домашний адрес» компьютера

Каждое устройство в сети имеет **IP-адрес** (Internet Protocol address). Это как почтовый адрес: чтобы отправить письмо, нужно знать адрес получателя.

IP-адрес версии 4 (IPv4) — это четыре числа от 0 до 255, разделённых точками:

```
10.129.13.78  —  IP-адрес сервера n8
 ┬   ┬   ┬  ┬
 │   │   │  └── хост (конкретный компьютер)
 │   │   └───── подсеть
 │   └───────── сеть
 └───────────── класс сети (10.x.x.x — частная)
```

**Маска подсети** определяет, какая часть адреса относится к сети, а какая — к хосту. Например, маска `255.255.255.0` (или `/24`) означает: первые три числа — сеть, последнее — хост.

**CIDR-нотация** (Classless Inter-Domain Routing): `10.129.13.0/24` = сеть 10.129.13.0, маска 255.255.255.0, доступно 254 хоста (.1 — .254).

| Сеть | Описание |
|---|---|
| `10.129.11.0/24` | Cisco 815, VLAN 308 |
| `10.129.13.0/24` | GPU-серверы (n7, n8) |
| `10.129.100.0/24` | WireGuard-туннель (VPS1—VPS2) |
| `10.244.0.0/16` | Flannel VXLAN (Kubernetes overlay) |

**Публичные vs частные адреса:**

- **Публичные** (белые) — видны в Интернете. `170.168.91.95` (VPS1), `130.17.1.90` (VPS2).
- **Частные** (серые) — только внутри локальной сети. `10.x.x.x`, `192.168.x.x`, `172.16–31.x.x`. Не маршрутизируются в Интернете.

### DNS: как `fb1.spb.ru` превращается в IP

Люди запоминают имена (`fb1.spb.ru`), а компьютеры — числа (`170.168.91.95`). **DNS** (Domain Name System) — это «телефонный справочник» интернета.

Процесс разрешения имени:
1. Вы вводите в браузере `fb1.spb.ru`
2. Браузер спрашивает DNS-сервер: «какой IP у fb1.spb.ru?»
3. DNS-сервер отвечает: `170.168.91.95`
4. Браузер подключается к `170.168.91.95`

Типы DNS-записей:
- **A** (Address) — имя → IPv4 адрес
- **AAAA** — имя → IPv6 адрес
- **CNAME** (Canonical Name) — псевдоним (одно имя → другое имя)
- **MX** (Mail eXchange) — почтовый сервер

### Порты: «квартиры» в доме

IP-адрес — это адрес дома. **Порт** — это номер квартиры. Одно устройство может обслуживать множество сервисов, каждый на своём порту.

| Порт | Сервис | Где |
|---|---|---|
| 10443 | nginx (HTTPS) | VPS1 |
| 80 | nginx (портал) | VPS2 |
| 3000 | BFF (Node.js) | VPS2 |
| 5432 | PostgreSQL | VPS2 |
| 30900 | Gateway (NodePort) | K8s → n7 |
| 32293 | vLLM 14B (NodePort) | n8 |
| 32294 | vLLM 32B (NodePort) | n7 |
| 30300 | Grafana (NodePort) | n7 |
| 8000 | vLLM (ClusterIP) | K8s |
| 6379 | Redis | K8s |

Порты до 1024 — привилегированные (только root может открыть). Порты выше 1024 — непривилегированные.

### Протоколы: TCP/IP и HTTP

**TCP** (Transmission Control Protocol) — гарантирует доставку данных в правильном порядке. Как заказное письмо с уведомлением. Используется для всего важного: веб, почта, базы данных.

**UDP** (User Datagram Protocol) — быстрый, но без гарантий. Как обычная открытка. Используется для видео, игр, DNS, VPN (WireGuard).

**HTTP** (HyperText Transfer Protocol) — протокол передачи веб-страниц. Работает поверх TCP.

Структура HTTP-запроса:
```
GET /api/health HTTP/1.1          ← метод, путь, версия
Host: fb1.spb.ru:10443            ← заголовки
Authorization: Bearer eyJh...     ←
Content-Type: application/json    ←
                                  ← пустая строка
{"model": "qwen2.5-14b"}          ← тело (опционально)
```

Структура HTTP-ответа:
```
HTTP/1.1 200 OK                   ← версия, код, сообщение
Content-Type: application/json    ← заголовки
Content-Length: 45                ←
                                  ← пустая строка
{"status": "healthy"}             ← тело
```

Коды ответа, которые нужно знать:

| Код | Значение | Когда видим |
|---|---|---|
| **200** | OK — успех | Нормальный ответ |
| **400** | Bad Request — ошибка в запросе | Неправильный JSON |
| **401** | Unauthorized — не авторизован | Без токена |
| **403** | Forbidden — нет прав | Чужой org_id |
| **404** | Not Found — не найдено | Нет такой модели |
| **429** | Too Many Requests — превышен лимит | Rate Limiter |
| **500** | Internal Server Error — ошибка сервера | Gateway упал |
| **502** | Bad Gateway — шлюз недоступен | BFF не видит Gateway |

**HTTPS** — HTTP + шифрование (TLS 1.3). Весь трафик между браузером и сервером зашифрован. Определяется по порту 443 (или 10443 у нас) и замочку в браузере.

### VPN: виртуальная частная сеть

**VPN** (Virtual Private Network) создаёт зашифрованный туннель между двумя компьютерами через интернет. Как будто вы протянули личный сетевой кабель между VPS1 и VPS2, хотя на самом деле трафик идёт через интернет.

**WireGuard** — современный VPN-протокол, встроенный в ядро Linux. Быстрый, простой в настройке, надёжный.

Как работает:
1. На каждом конце генерируется пара ключей: приватный (секретный) и публичный (открытый)
2. В конфигурации указывается: «мой приватный ключ, публичный ключ собеседника, IP-адрес для туннеля»
3. При поднятии туннеля появляется виртуальный сетевой интерфейс (например, `wg0`)
4. Весь трафик через этот интерфейс автоматически шифруется

В нашей сети:
- **wg0** (VPS1): `10.129.100.234` ←→ **wg1** (VPS2): `10.99.0.2`

**Cisco VPN** — аппаратный VPN-терминатор. Cisco 815 — это физическое устройство, которое терминирует (заканчивает) VPN-туннель со стороны закрытого контура. На VPS2 создаётся туннель `tun1` до Cisco 815.

### Физическая сеть Aither — полная карта

```dot
digraph AitherNetwork {
    rankdir=LR
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=10]

    // Internet cloud
    internet [label="Интернет", shape=cloud, style="filled", fillcolor="#e3f2fd", color="#1976d2", fontsize=11]

    subgraph cluster_vps1 {
        label="VPS1: 170.168.91.95\nUbuntu 24.04"
        style="rounded"
        color="#1976d2"
        fontname="system-ui"
        fontsize=10

        nginx_vps1 [label="nginx\n:10443 HTTPS\n:30900 → K8s", shape=box, style="rounded,filled", fillcolor="#e3f2fd", color="#1976d2"]
        wg0 [label="wg0\n10.129.100.234", shape=box, style="rounded,filled", fillcolor="#e8f5e9", color="#43a047"]
    }

    subgraph cluster_vps2 {
        label="VPS2: 130.17.1.90\nUbuntu"
        style="rounded"
        color="#7b1fa2"
        fontname="system-ui"
        fontsize=10

        nginx_vps2 [label="nginx :80\n(портал)", shape=box, style="rounded,filled", fillcolor="#f3e5f5", color="#7b1fa2"]
        bff [label="BFF :3000\nNode.js", shape=box, style="rounded,filled", fillcolor="#fce4ec", color="#e91e63"]
        pgsql [label="PostgreSQL\n:5432", shape=box, style="rounded,filled", fillcolor="#f3e5f5", color="#9c27b0"]
        wg1 [label="wg1\n10.99.0.2", shape=box, style="rounded,filled", fillcolor="#e8f5e9", color="#43a047"]
        tun1 [label="tun1\nCisco VPN", shape=box, style="rounded,filled", fillcolor="#e0f7fa", color="#00838f"]
    }

    subgraph cluster_cisco {
        label="Cisco 815\n10.129.11.0/24"
        style="rounded"
        color="#43a047"
        fontname="system-ui"
        fontsize=10

        cisco [label="VPN-терминатор\nVLAN 308", shape=box, style="rounded,filled", fillcolor="#e8f5e9", color="#43a047"]
    }

    subgraph cluster_gpu {
        label="Закрытый контур\n10.129.13.0/24 (VLAN 308)"
        style="rounded,dashed"
        color="#ff9800"
        fontname="system-ui"
        fontsize=10

        n8 [label="n8: 40.51\ncontrol-plane\n2× RTX 6000", shape=box, style="rounded,filled", fillcolor="#fff3e0", color="#ff9800"]
        n7 [label="n7: 40.50\nworker\n2× RTX 6000", shape=box, style="rounded,filled", fillcolor="#fff3e0", color="#ff9800"]
    }

    // Connections
    internet -> nginx_vps1 [label="HTTPS\n:10443", color="#1976d2"]
    nginx_vps1 -> wg0 [dir=none, color="#43a047", style=dashed]
    wg0 -> wg1 [label="WireGuard\nшифрованный туннель", color="#43a047", style=dashed]
    wg1 -> nginx_vps2 [dir=none, color="#43a047", style=dashed]
    nginx_vps2 -> bff [label=":3000", color="#7b1fa2"]
    bff -> nginx_vps1 [label="CORE_API\n:30900", color="#e91e63", style=dashed]
    nginx_vps1 -> n7 [label=":30900\nNodePort", color="#1976d2", style=dotted]

    wg1 -> tun1 [dir=none, color="#00838f"]
    tun1 -> cisco [label="Cisco VPN\ntun1", color="#00838f", style=dashed]
    cisco -> n8 [label="VLAN 308", color="#43a047"]
    cisco -> n7 [label="VLAN 308", color="#43a047"]

    n8 -> n7 [label="Flannel VXLAN\n10.244.0.0/16", color="#ff9800", style=dotted, dir=both]

    // BMC chain
    bmc [label="BMC n7\n:9443", shape=box, style="filled", fillcolor="#f5f5f5", color="#616161", fontsize=8]
    socat [label="socat\n:19443", shape=box, style="filled", fillcolor="#f5f5f5", color="#616161", fontsize=8]
    n7 -> bmc [dir=none]
    bmc -> socat [label="проброс", color="#616161", style=dotted]
    socat -> nginx_vps1 [label=":443", color="#616161", style=dotted]
}
```

*Схема 1.5. Полная физическая схема сети Aither. Сплошные линии — прямое соединение, штриховые — туннели (VPN), пунктирные — проброс портов.*

**Путь запроса от пользователя до модели:**

1. Пользователь → Интернет → `170.168.91.95:10443` (VPS1, nginx, HTTPS)
2. VPS1 → WireGuard → `10.99.0.2:3000` (VPS2, BFF)
3. VPS2 → WireGuard → `170.168.91.95:30900` (VPS1, nginx-прокси)
4. VPS1 → WireGuard → Cisco VPN → VLAN 308 → `10.129.13.77:30900` (n7, Gateway NodePort)
5. Gateway → `vllm-qwen32b:8000` (K8s-сервис) → модель → ответ
6. Ответ идёт обратно по той же цепочке, но Gateway сразу стримит токены через BFF в браузер

**BMC-проброс (как администратор включает сервер удалённо):**

1. Администратор → `https://170.168.91.95:443` (VPS1, nginx)
2. VPS1 → WireGuard → VPS2 → `socat` перенаправляет :19443 → WireGuard → Cisco → VLAN 308 → `n7:9443`
3. Администратор видит веб-интерфейс BMC сервера n7 в своём браузере

---

## 1.4. ✏️ Закрепление: итоговый практикум

### Задание 1. «Узнай сервер»
- Сколько ядер у Xeon 6258R? А потоков?
- Почему мы не пишем «112 ядер» для сервера с двумя процессорами?
- Сколько VRAM у одной RTX 6000? А у двух?
- Зачем нужно 754 GB RAM, если модель занимает 28 GB?

### Задание 2. «Найди в системе»
На сервере с Linux (ВМ или реальном):
```bash
cat /proc/cpuinfo | grep "model name" | head -1   # модель процессора
free -h                                            # оперативная память
df -h                                              # диски
ip a                                               # сетевые интерфейсы
cat /etc/hostname                                   # имя компьютера
```

### Задание 3. «Проследи маршрут»
Нарисуй на бумаге путь запроса: пользователь в браузере → `fb1.spb.ru:10443` → ... → модель на n7. Подпиши каждый узел, IP-адрес и порт.

### Задание 4. «Словарь термина»
Выпиши и дай определение своими словами:
- Процессор, ядро, поток
- RAM, VRAM
- IP-адрес, порт, DNS
- HTTP, HTTPS
- VPN, WireGuard
- systemd, демон

---

**Итог главы 1.** Вы узнали:
- Из чего состоит сервер (CPU, RAM, диск, GPU, BMC)
- Как устроен Linux (ядро, файловая система, процессы, systemd)
- Как компьютеры общаются по сети (IP, порты, DNS, HTTP, VPN)
- Как устроена физическая сеть Aither (VPS1↔VPS2↔Cisco↔n7/n8)

В следующей главе — контейнеры и Docker.

---

*Глава 1 из 18.*


# Глава 2. Виртуализация и контейнеризация

> **Цель главы:** понять, что такое виртуальная машина и контейнер, чем они отличаются, как работает Docker и Docker Compose. После этой главы вы сможете собрать свой первый Docker-образ и запустить контейнер.

---

## 2.1. Виртуальные машины: компьютер внутри компьютера

### Зачем нужна виртуализация

Представьте: у вас есть один мощный сервер (YADRO VEGMAN S320, 56 ядер, 754 GB RAM). Вы хотите запустить на нём:
- Kubernetes (для оркестрации)
- Базу данных PostgreSQL
- Отдельный тестовый сервер для экспериментов

Проблема: если запустить всё на одной операционной системе, программы будут мешать друг другу. PostgreSQL займёт порт 5432, тестовый сервер — тоже порт 5432. Конфликт. Одна программа может «уронить» ядро, и всё упадёт.

Решение: **виртуализация** — технология, позволяющая запустить несколько операционных систем на одном физическом сервере.

### Как работает виртуальная машина

**Гипервизор** (hypervisor) — программа, которая создаёт и управляет виртуальными машинами. Она «притворяется» железом: говорит гостевой ОС «у тебя есть 4 ядра, 8 GB RAM и диск на 100 GB», хотя на самом деле это лишь часть реального сервера.

| Тип гипервизора | Где работает | Примеры | Используется в Aither? |
|---|---|---|---|
| **Тип 1** (bare-metal) | Прямо на железе, без ОС | VMware ESXi, KVM, Proxmox VE | ✅ Proxmox VE |
| **Тип 2** (hosted) | Поверх обычной ОС | VirtualBox, VMware Workstation | Нет |

**KVM** (Kernel-based Virtual Machine) — гипервизор, встроенный в ядро Linux. Он превращает ядро Linux в гипервизор типа 1. **QEMU** (Quick EMUlator) — эмулятор устройств: притворяется жёстким диском, сетевой картой, видеокартой.

**Proxmox VE** (Virtual Environment) — это «обёртка» над KVM+QEMU с удобным веб-интерфейсом. В нашем проекте Proxmox используется для управления виртуальными машинами на серверах.

> 🏢 **Аналогия.** Физический сервер — многоквартирный дом. Гипервизор — управляющая компания. Виртуальные машины — квартиры. Каждая квартира изолирована: что происходит у соседей, вас не касается. Но все пользуются общим фундаментом, водопроводом и электричеством.

```dot
digraph VM {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    hardware [label="Физическое железо\nCPU: 56 ядер | RAM: 754 GB | Диск: 42 TB", shape=box, style="rounded,filled", fillcolor="#f5f5f5", color="#616161", fontsize=10]

    hypervisor [label="Гипервизор (KVM + QEMU)\nУправляет ресурсами: CPU, RAM, диск, сеть", shape=box, style="rounded,filled", fillcolor="#fce4ec", color="#e91e63", fontsize=10]

    subgraph cluster_vm1 {
        label="ВМ 1: Linux (K8s control-plane)"
        style="rounded,dashed"
        color="#1976d2"
        fontname="system-ui"
        vm1_os [label="Гостевая ОС\nAstra Linux SE 1.8", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
        vm1_app [label="kube-apiserver\nscheduler\ncontroller-manager", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2", fontsize=8]
        vm1_os -> vm1_app
    }

    subgraph cluster_vm2 {
        label="ВМ 2: Windows 11 (тестовая)"
        style="rounded,dashed"
        color="#43a047"
        fontname="system-ui"
        vm2_os [label="Гостевая ОС\nWindows 11", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    }

    subgraph cluster_vm3 {
        label="ВМ 3: Linux (База данных)"
        style="rounded,dashed"
        color="#ff9800"
        fontname="system-ui"
        vm3_os [label="Гостевая ОС\nUbuntu 24.04", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
        vm3_app [label="PostgreSQL 16", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800", fontsize=8]
        vm3_os -> vm3_app
    }

    hardware -> hypervisor
    hypervisor -> vm1_os
    hypervisor -> vm2_os
    hypervisor -> vm3_os

    // Passthrough
    gpu [label="GPU RTX 6000\n(проброшена в ВМ 1\nцеликом — PCIe Passthrough)", shape=box, style="rounded,filled", fillcolor="#fce4ec", color="#e91e63", fontsize=8]
    hardware -> gpu [style=dashed, dir=none]
    gpu -> vm1_os [style=dashed]
}
```

*Схема 2.1. Гипервизор KVM с тремя виртуальными машинами. GPU проброшена в ВМ 1 целиком через PCIe Passthrough — ВМ «видит» настоящую видеокарту.*

### PCIe Passthrough: отдаём GPU виртуальной машине

Обычно виртуальная машина не видит настоящую видеокарту — гипервизор даёт ей виртуальную (медленную). Но для работы с моделями ИИ нужна производительность настоящей RTX 6000.

**PCIe Passthrough** — технология, которая пробрасывает (перенаправляет) физическое PCIe-устройство (видеокарту) внутрь виртуальной машины. Гостевая ОС видит настоящую RTX 6000, устанавливает настоящие драйверы NVIDIA и работает с ней на полной скорости.

⚠️ **Ограничение:** одну видеокарту можно пробросить только в одну ВМ. Нельзя «поделить» RTX 6000 между двумя виртуальными машинами (в отличие от процессора или памяти). Именно поэтому в сервере YADRO 2 видеокарты: одну можно отдать ВМ с vLLM, вторую — ВМ с обучением моделей.

В Proxmox для проброса GPU нужно:
1. Включить IOMMU (Input-Output Memory Management Unit) в BIOS и ядре — технология, которая изолирует устройства PCIe друг от друга
2. Добавить в конфигурацию ВМ: `hostpci0: 01:00.0` (где `01:00.0` — адрес видеокарты на шине PCIe)

---

## 2.2. Контейнеры и Docker

### Контейнер vs виртуальная машина

Виртуальная машина — это полноценный компьютер: своё ядро ОС, свои драйверы, свои системные службы. На запуск уходит 30–60 секунд, занимает гигабайты памяти.

**Контейнер** — это изолированное окружение для одной программы и её зависимостей. В отличие от ВМ, контейнер **не содержит своей операционной системы** — он использует ядро хостовой ОС.

| | Виртуальная машина | Контейнер |
|---|---|---|
| **Что внутри** | Полноценная ОС + программы | Программа + её библиотеки |
| **Ядро** | Своё, отдельное | Хостовое (общее с другими контейнерами) |
| **Запуск** | 30–60 секунд | 1–2 секунды |
| **Память** | Гигабайты (сама ОС) | Мегабайты (только программа) |
| **Изоляция** | Полная (ничего не видно) | На уровне процессов (namespaces) |
| **Аналогия** | Отдельная квартира | Отдельная комната в общежитии |

```dot
digraph VMvsContainer {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    subgraph cluster_vm_side {
        label="Виртуальная машина"
        style="rounded,dashed"
        color="#e91e63"
        fontname="system-ui"
        fontsize=11

        subgraph cluster_vm_real {
            label=""
            color=white
            vm_app [label="BFF", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
            vm_bins [label="Библиотеки", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
            vm_os [label="Гостевая ОС\n(своё ядро)", shape=box, style="filled", fillcolor="#f5f5f5", color="#616161"]
            vm_app -> vm_bins -> vm_os
        }
    }

    subgraph cluster_container_side {
        label="Контейнеры"
        style="rounded,dashed"
        color="#43a047"
        fontname="system-ui"
        fontsize=11

        subgraph cluster_c1 {
            label="Контейнер 1"
            style="rounded"
            color="#1976d2"
            c1_app [label="Gateway", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
            c1_bins [label="Библиотеки", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
            c1_app -> c1_bins
        }

        subgraph cluster_c2 {
            label="Контейнер 2"
            style="rounded"
            color="#ff9800"
            c2_app [label="PostgreSQL", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
            c2_bins [label="Библиотеки", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
            c2_app -> c2_bins
        }
    }

    hypervisor [label="Гипервизор", shape=box, style="filled", fillcolor="#f5f5f5", color="#616161"]
    docker [label="Docker Engine", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]

    host_os [label="Ядро хостовой ОС (Linux)", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63", fontsize=10]
    hardware [label="Физическое железо", shape=box, style="filled", fillcolor="#f5f5f5", color="#616161", fontsize=10]

    vm_os -> hypervisor -> host_os -> hardware
    c1_bins -> docker -> host_os
    c2_bins -> docker
}
```

*Схема 2.2. Сравнение виртуальной машины и контейнеров. Ключевое отличие: контейнеры используют общее ядро ОС, ВМ — своё собственное.*

### Как Docker изолирует контейнеры

Docker использует две технологии ядра Linux:

1. **Namespaces** (пространства имён) — изолируют то, что контейнер «видит»:
   - `pid` namespace: контейнер видит только свои процессы (PID 1 внутри контейнера — не PID 1 в хосте)
   - `net` namespace: контейнер имеет свои сетевые интерфейсы, свой IP-адрес
   - `mnt` namespace: контейнер имеет свою файловую систему
   - `uts` namespace: контейнер имеет свой hostname

2. **Cgroups** (Control Groups) — ограничивают то, что контейнер может «потребить»:
   - `cpu`: не больше 2 ядер
   - `memory`: не больше 512 MB RAM
   - `blkio`: не больше 100 MB/s на диск

### Docker: архитектура

Docker состоит из двух частей:
- **Docker Daemon** (`dockerd`) — сервер, который управляет контейнерами, образами, сетями и томами
- **Docker CLI** (`docker`) — команда, которую вы пишете в терминале. Она отправляет запросы демону

Когда вы пишете `docker run nginx`, происходит:
1. Docker CLI → Docker Daemon: «запусти контейнер из образа nginx»
2. Docker Daemon → containerd: «запусти контейнер»
3. containerd → runc: «создай контейнер с изоляцией (namespaces + cgroups)»
4. runc запускает процесс nginx внутри изолированного окружения

```dot
digraph DockerArch {
    rankdir=LR
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    user [label="Пользователь\nтерминал", shape=box, style="rounded,filled", fillcolor="#e3f2fd", color="#1976d2", fontsize=10]
    cli [label="docker CLI\n(команда docker)", shape=box, style="rounded,filled", fillcolor="#e3f2fd", color="#1976d2"]
    daemon [label="dockerd\n(Docker Daemon)\n— управляет образами\n— управляет контейнерами\n— управляет сетями\n— управляет томами", shape=box, style="rounded,filled", fillcolor="#fce4ec", color="#e91e63", fontsize=9]
    containerd [label="containerd\n— запуск контейнеров\n— управление жизненным циклом", shape=box, style="rounded,filled", fillcolor="#e8f5e9", color="#43a047"]
    runc [label="runc\n— создаёт namespaces\n— применяет cgroups\n— запускает процесс", shape=box, style="rounded,filled", fillcolor="#fff3e0", color="#ff9800"]

    registry [label="Registry\n(Docker Hub, ghcr.io)\nхранилище образов", shape=cylinder, style="filled", fillcolor="#f3e5f5", color="#9c27b0"]

    container [label="Контейнер\n(изолированный\nпроцесс)", shape=box, style="rounded", color="#43a047", fontsize=10]

    user -> cli [label="docker run"]
    cli -> daemon [label="REST API\n/var/run/docker.sock"]
    daemon -> containerd [label="gRPC"]
    containerd -> runc [label="OCI runtime"]
    runc -> container
    daemon -> registry [label="docker pull", style=dashed, color="#9c27b0"]
    registry -> daemon [label="образ", style=dashed, color="#9c27b0"]
}
```

*Схема 2.3. Архитектура Docker. Команда docker → демон → containerd → runc → контейнер. Образы скачиваются из Registry.*

> ⚠️ **containerd vs Docker.** На серверах Kubernetes мы используем containerd напрямую (без Docker). Docker — это «всё в одном», containerd — только среда выполнения контейнеров (легче и быстрее). Но команды `docker` удобнее для разработки — поэтому изучаем Docker.

### Dockerfile: инструкция по сборке образа

**Образ** (image) — это «слепок» контейнера: операционная система + программа + все зависимости. Как ISO-файл для установки ОС: один раз создали, много раз запустили.

**Dockerfile** — текстовый файл с инструкциями, как собрать образ.

Разберём на примере нашего Gateway:

```dockerfile
# syntax=docker/dockerfile:1          ← версия синтаксиса

FROM python:3.12-slim                ← базовый образ: берём готовый Python 3.12
                                      #   (slim = облегчённый, без лишнего)

WORKDIR /app                          ← рабочая папка внутри контейнера
                                      #   (все следующие команды — из /app)

COPY gateway/requirements.txt .       ← копируем файл зависимостей из проекта
                                      #   (слева — путь на хосте, справа — в контейнере)

RUN pip install --no-cache-dir -r requirements.txt
                                      ← выполняем команду внутри образа:
                                      #   устанавливаем Python-пакеты

COPY gateway/ .                       ← копируем весь код Gateway

RUN mkdir -p /app/wiki                ← создаём папку для базы знаний

EXPOSE 8080                           ← сообщаем Docker: контейнер слушает порт 8080
                                      #   (это документация, порт не открывается автоматически)

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1
                                      ← проверка здоровья контейнера каждые 10 секунд

CMD ["python3", "gateway.py"]         ← команда, которая выполняется при запуске контейнера
```

**Слои (layers):** каждая инструкция (FROM, RUN, COPY) создаёт новый слой. Слои кэшируются: если вы изменили только `gateway.py`, а `requirements.txt` не менялся — Docker не будет заново выполнять `pip install`, а возьмёт готовый слой из кэша. Это ускоряет сборку.

```dot
digraph Layers {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    l1 [label="Слой 1: python:3.12-slim\n(базовый образ, ~50 MB)", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
    l2 [label="Слой 2: WORKDIR /app\n(метаданные, 0 MB)", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
    l3 [label="Слой 3: COPY requirements.txt\n(~100 B)", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    l4 [label="Слой 4: RUN pip install\n(~50 MB — пакеты Python)", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    l5 [label="Слой 5: COPY gateway/\n(~300 KB — код)", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    l6 [label="Слой 6: RUN mkdir /app/wiki\n(0 MB)", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    l7 [label="Слой 7: CMD\n(метаданные, 0 MB)", shape=box, style="filled", fillcolor="#f3e5f5", color="#9c27b0"]

    l1 -> l2 -> l3 -> l4 -> l5 -> l6 -> l7

    note [label="Слои 1-4 кэшируются\n(меняются редко)\n\nСлой 5 пересобирается\nпри каждом изменении кода", shape=plaintext, fontsize=9]

    l7 -> note [style=invis]
}
```

*Схема 2.4. Слои Docker-образа Gateway. При изменении кода пересобирается только слой 5.*

### Основные команды Docker

| Команда | Что делает | Пример |
|---|---|---|
| `docker build -t name .` | Собрать образ из Dockerfile | `docker build -t my-gateway .` |
| `docker run -d -p 8080:8080 name` | Запустить контейнер | `docker run -d -p 8080:8080 my-gateway` |
| `docker ps` | Список запущенных контейнеров | `docker ps` |
| `docker ps -a` | Все контейнеры (включая остановленные) | |
| `docker logs -f name` | Логи контейнера | `docker logs -f gateway` |
| `docker exec -it name bash` | Зайти внутрь контейнера | `docker exec -it gateway bash` |
| `docker stop name` | Остановить контейнер | `docker stop gateway` |
| `docker rm name` | Удалить контейнер | `docker rm gateway` |
| `docker rmi name` | Удалить образ | `docker rmi my-gateway` |
| `docker pull name` | Скачать образ из registry | `docker pull nginx:alpine` |
| `docker push name` | Отправить образ в registry | `docker push ghcr.io/my-org/gateway:latest` |
| `docker save -o file.tar name` | Сохранить образ в файл (для переноса) | `docker save -o gateway.tar gateway:latest` |
| `docker load -i file.tar` | Загрузить образ из файла | `docker load -i gateway.tar` |

Ключевые флаги `docker run`:
- `-d` — запустить в фоне (detached mode: контейнер работает, терминал свободен)
- `-p 8080:8080` — пробросить порт (внешний:внутренний)
- `-v /host/path:/container/path` — примонтировать папку (том)
- `--name gateway` — дать контейнеру имя (вместо случайного)
- `--restart always` — перезапускать при падении
- `-e VAR=value` — задать переменную окружения
- `--gpus all` — дать контейнеру доступ ко всем GPU (нужен nvidia-container-toolkit)

### Сеть в Docker

По умолчанию Docker создаёт виртуальную сеть `bridge`. Контейнеры в этой сети видят друг друга по именам:
```
docker run -d --name redis redis:7-alpine
docker run -d --name gateway --link redis my-gateway
# Теперь gateway может обратиться к redis по адресу redis:6379
```

Режимы сети:
- **bridge** (по умолчанию) — изолированная сеть, контейнеры видят друг друга
- **host** — контейнер использует сеть хоста напрямую (нет изоляции, но быстрее). Используется для nginx на VPS2
- **none** — без сети

### Тома (volumes): постоянное хранилище

Контейнеры — временные. Если контейнер удалить, все данные внутри него пропадут. **Тома** (volumes) решают эту проблему — данные хранятся на хосте, а контейнер их «видит» через примонтированную папку.

```bash
# Bind mount: пробрасываем реальную папку хоста внутрь контейнера
docker run -v /mnt/models:/models vllm/vllm-openai
# Теперь контейнер «видит» наши модели в /mnt/models
```

Типы:
- **bind mount** — конкретная папка на хосте (`/mnt/models` → `/models`)
- **volume** — Docker сам управляет папкой (лучше для продакшена)
- **tmpfs** — временная папка в RAM (исчезает при остановке)

---

## 2.3. Docker Compose: много контейнеров сразу

**Docker Compose** — инструмент для запуска нескольких контейнеров одной командой. Вместо трёх команд `docker run` вы описываете все контейнеры в одном YAML-файле и запускаете: `docker compose up -d`.

Файл `docker-compose.yml` для VPS2 (nginx + PostgreSQL + BFF):

```yaml
version: "3.8"

services:
  nginx:
    image: nginx:alpine          # готовый образ nginx (облегчённый)
    network_mode: host           # используем сеть хоста напрямую
    volumes:
      - ./static:/usr/share/nginx/html  # пробрасываем статику портала
      - ./nginx.conf:/etc/nginx/nginx.conf  # и конфиг nginx
    restart: always

  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: aither
      POSTGRES_PASSWORD: ***
      POSTGRES_DB: aither
    volumes:
      - pgdata:/var/lib/postgresql/data  # данные БД — в томе (не исчезнут)
    ports:
      - "5432:5432"
    restart: always

volumes:
  pgdata:                         # объявляем именованный том
```

Ключевые команды:
- `docker compose up -d` — запустить все сервисы в фоне
- `docker compose down` — остановить и удалить
- `docker compose logs -f` — логи всех сервисов
- `docker compose restart nginx` — перезапустить конкретный сервис

---

## 2.4. containerd и nvidia-runtime

### containerd — «движок» Kubernetes

**containerd** (произносится «контэйнэр-ди») — это промышленная среда выполнения контейнеров. Docker использует containerd внутри себя, но Kubernetes использует containerd напрямую — без Docker.

Зачем? Docker — это «комбайн»: сборка образов, управление контейнерами, сеть, тома, registry. Kubernetes нужна только среда выполнения (запустить контейнер, следить за ним). containerd делает именно это.

> Если Docker = швейцарский нож (всё в одном), то containerd = скальпель (одна задача, идеально).

Команда для работы с containerd (аналог `docker`):
```bash
# docker ps          →  crictl ps
# docker logs        →  crictl logs
# docker pull        →  crictl pull
# docker run         →  ctr run   (низкоуровневая)
```

### nvidia-container-toolkit: GPU в контейнере

Обычный контейнер не видит видеокарту — у него нет драйверов NVIDIA. **nvidia-container-toolkit** решает эту проблему: он «подсовывает» контейнеру драйверы с хоста.

```bash
# Без toolkit:
docker run --gpus all nvidia/cuda:12.0-base nvidia-smi
# Ошибка: GPU не найдена

# С toolkit:
docker run --gpus all nvidia/cuda:12.0-base nvidia-smi
# Показывает RTX 6000!
```

Как работает:
1. На хосте установлены драйверы NVIDIA и `nvidia-container-toolkit`
2. containerd настроен использовать `nvidia` runtime для контейнеров с GPU
3. При запуске контейнера с флагом `--gpus all` toolkit монтирует в контейнер `/usr/lib/x86_64-linux-gnu/libcuda.so` и другие файлы драйверов
4. Контейнер «видит» GPU, как будто драйверы установлены внутри

В Kubernetes это делается через `runtimeClassName: nvidia` в манифесте пода.

---

## 2.5. Docker Registry: хранилище образов

**Registry** — это сервер, который хранит Docker-образы. Как GitHub для кода, но для образов.

Публичные registry:
- **Docker Hub** (`docker.io/library/nginx`) — самый большой, общедоступный
- **GitHub Container Registry** (`ghcr.io/dedvmedved-dot/aither-project-gateway`) — наш registry для Gateway
- **Quay.io** — Red Hat

Приватный registry для закрытого контура:
```bash
# На любой машине в контуре:
docker run -d -p 5000:5000 --restart always --name registry registry:2

# Теперь можно пушить в него:
docker tag my-image localhost:5000/my-image
docker push localhost:5000/my-image
```

В закрытом контуре без интернета — это единственный способ доставки образов:
1. На машине с интернетом: `docker pull` → `docker save -o images.tar.gz`
2. Перенос `images.tar.gz` на флешке в закрытый контур
3. В контуре: `docker load -i images.tar.gz` → `docker tag` → `docker push localhost:5000/...`

---

## 2.6. ✏️ Практикум: Docker своими руками

### Задание 1. Первый контейнер
```bash
# Запускаем nginx
docker run -d -p 8080:80 --name my-nginx nginx:alpine

# Проверяем:
docker ps                  # видим контейнер
curl http://localhost:8080 # видим приветствие nginx

# Заходим внутрь:
docker exec -it my-nginx sh
# Вы внутри контейнера! Попробуйте:
hostname      # имя контейнера (не вашего сервера)
cat /etc/os-release  # Alpine Linux (не ваш хост!)
exit          # выходим обратно

# Останавливаем и удаляем:
docker stop my-nginx
docker rm my-nginx
```

### Задание 2. Свой Dockerfile
Создайте файл `Dockerfile`:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN echo 'print("Привет, Aither! Я внутри контейнера.")' > app.py
CMD ["python3", "app.py"]
```

Соберите и запустите:
```bash
docker build -t my-python .
docker run my-python
# → Привет, Aither! Я внутри контейнера.
```

### Задание 3. Docker Compose
Создайте `docker-compose.yml` с двумя сервисами: nginx и ваш Python-образ. Проверьте, что оба запускаются одной командой `docker compose up -d`.

### Задание 4. «Переведи на русский»
Объясните своими словами, что делают эти команды:
- `docker build -t gateway .`
- `docker run -d -p 3000:3000 --name bff -e PG_URL=... bff:latest`
- `docker exec -it postgres psql -U aither`
- `docker save -o gateway.tar gateway:latest`

### Задание 5. «Словарь термина»
Выпишите и дайте определение:
- Гипервизор, KVM, QEMU
- Образ, контейнер, Dockerfile
- Слой, кэширование
- Том (volume), bind mount
- Registry, containerd, runc
- Namespace, cgroup, runtimeClassName

---

**Итог главы 2.** Вы узнали:
- Чем отличается виртуальная машина от контейнера (ядро, изоляция, скорость)
- Как работает Docker: клиент → демон → containerd → runc → контейнер
- Как писать Dockerfile (FROM, COPY, RUN, CMD) и почему слои кэшируются
- Как запускать много контейнеров через Docker Compose
- Что такое containerd и почему Kubernetes использует его вместо Docker
- Как GPU попадает в контейнер (nvidia-container-toolkit)
- Как переносить образы в закрытый контур (docker save/load)

В следующей главе — Kubernetes: от Pod до кластера.


# Глава 3. Kubernetes: от Pod до кластера

> **Цель главы:** понять, зачем нужен Kubernetes, выучить его азбуку (Pod, Deployment, Service, ConfigMap), научиться читать YAML-манифесты и разобраться в устройстве кластера Aither. После этой главы вы сможете осмысленно набирать `kubectl get pods` и понимать, что видите.

---

## 3.1. Зачем нужен Kubernetes

### Проблема: когда контейнеров много

В прошлой главе мы научились запускать контейнеры через Docker. Один контейнер — легко:

```bash
docker run -d -p 8080:8080 --name gateway gateway:latest
```

Но что, когда контейнеров десять? А двадцать? А когда их нужно запустить на двух серверах?

Проблемы ручного управления:
1. **Размещение.** На каком сервере запустить контейнер? Где есть свободная память? Где есть GPU?
2. **Самовосстановление.** Контейнер упал в 3 часа ночи. Кто его перезапустит?
3. **Масштабирование.** Пользователей стало вдвое больше — нужно запустить ещё 2 копии Gateway. Кто это сделает?
4. **Сеть.** Как контейнер на сервере n8 узнает IP-адрес контейнера на сервере n7? А если контейнер перезапустился и адрес поменялся?
5. **Обновление.** Новая версия Gateway. Как обновить без остановки сервиса?
6. **Конфигурация.** Где хранить пароли и настройки, чтобы не «зашивать» их в образ?

**Kubernetes** (K8s) — это «операционная система для дата-центра». Он решает все эти проблемы автоматически.

> 🔤 **K8s** — сокращение от **K**ubernetes (K + 8 букв между K и s + s). Часто произносят «кейтс».

```dot
digraph K8sWhy {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    subgraph cluster_problems {
        label="Проблемы без оркестратора"
        style="rounded,dashed"
        color="#e91e63"
        fontname="system-ui"
        fontsize=11

        p1 [label="Где запустить\nконтейнер?", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
        p2 [label="Кто перезапустит\nупавший?", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
        p3 [label="Как найти\nнужный контейнер?", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
        p4 [label="Как обновить\nбез остановки?", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
        p5 [label="Где хранить\nпароли?", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
        p6 [label="Как добавить\nмощностей?", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
    }

    k8s [label="Kubernetes\nРешает всё это\nавтоматически", shape=box, style="rounded,filled", fillcolor="#e8f5e9", color="#43a047", fontsize=12]

    subgraph cluster_solutions {
        label="Решения K8s"
        style="rounded,dashed"
        color="#43a047"
        fontname="system-ui"
        fontsize=11

        s1 [label="Scheduler\nразмещает поды", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
        s2 [label="Контроллеры\nперезапускают", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
        s3 [label="Service\nдаёт постоянный IP", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
        s4 [label="Rolling Update\nбез downtime", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
        s5 [label="Secret\nхранит пароли", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
        s6 [label="HPA\nмасштабирует", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    }

    p1 -> s1 [style=dashed, color="#616161"]
    p2 -> s2 [style=dashed, color="#616161"]
    p3 -> s3 [style=dashed, color="#616161"]
    p4 -> s4 [style=dashed, color="#616161"]
    p5 -> s5 [style=dashed, color="#616161"]
    p6 -> s6 [style=dashed, color="#616161"]
}
```

*Схема 3.1. Каждую проблему ручного управления контейнерами Kubernetes решает автоматически.*

### Что даёт Kubernetes

| Возможность | Как было (руками) | Как стало (K8s) |
|---|---|---|
| Размещение | `ssh n7 "docker run..."` | Scheduler сам выбирает узел |
| Перезапуск | `while true; do docker start...` | Deployment перезапускает автоматически |
| Сеть | Запомнить IP каждого контейнера | Service: постоянный IP и DNS-имя |
| Обновление | Остановить → обновить → запустить | Rolling Update: по одному поду |
| Конфигурация | Вшита в образ | ConfigMap и Secret: отдельно от кода |
| Масштабирование | `docker run` ещё 3 раза на разных серверах | `kubectl scale --replicas=5` |
| Балансировка | Nginx с ручным списком серверов | Service автоматически балансирует |

Kubernetes работает по **декларативной** модели: вы говорите **«я хочу чтобы было 3 экземпляра Gateway, каждый с 512 MB памяти, на порту 8080»**, а K8s сам делает так, чтобы реальность соответствовала вашему описанию. Если под упадёт — K8s запустит новый. Если узел выйдет из строя — K8s перенесёт поды на другой.

> 📋 **Декларативный vs императивный.** Императивный: «сделай А, потом Б, потом В». Декларативный: «я хочу чтобы было состояние Х». Вы не говорите КАК достичь состояния — только КАКОЕ состояние нужно. K8s сам решает как.

---

## 3.2. Архитектура Kubernetes

Kubernetes — это распределённая система. Она состоит из двух типов узлов:

### Control Plane (плоскость управления) — «мозг»

**Control Plane** управляет всем кластером. Он решает: где запускать поды, сколько их должно быть, как они связаны. В нашем кластере Control Plane живёт на сервере **n8**.

Компоненты Control Plane:

| Компонент | Что делает | Аналогия |
|---|---|---|
| **kube-apiserver** | Принимает все команды (`kubectl apply`) | Секретарь — принимает заявки |
| **etcd** | Хранит ВСЁ состояние кластера (ключ-значение) | База данных кластера |
| **kube-scheduler** | Выбирает, на каком узле запустить новый под | Диспетчер — распределяет работу |
| **kube-controller-manager** | Следит, чтобы реальность = желаемое (запускает/убивает поды) | Прораб — контролирует исполнение |

> 🔤 **etcd** — распределённое key-value хранилище. Название происходит от `/etc` (папка конфигов в Linux) + `d` (distributed — распределённый). Хранит: «deployment gateway должен иметь 3 реплики», «под gateway-7f8b9c-abc1 запущен на n7», «сервис gateway слушает порт 8080».

### Worker Node (рабочий узел) — «руки»

**Worker Node** — это сервер, на котором реально бегут контейнеры. В нашем кластере два узла: n8 (совмещает Control Plane и Worker) и n7 (чистый Worker).

Компоненты Worker Node:

| Компонент | Что делает |
|---|---|
| **kubelet** | «Агент K8s» на узле. Получает задания от Control Plane: «запусти под X». Следит за подами, докладывает статус |
| **kube-proxy** | Настраивает сетевые правила (iptables), чтобы трафик доходил до нужных подов |
| **Container Runtime** | containerd — запускает контейнеры (как мы изучили в гл. 2) |

### Addons (дополнения)

Это не часть ядра K8s, но без них кластер неполноценен:

| Addon | Зачем |
|---|---|
| **Flannel** (CNI) | Сеть между подами на разных узлах (overlay) |
| **CoreDNS** | DNS внутри кластера (`gateway` → IP сервиса) |
| **Metrics Server** | Сбор метрик CPU/памяти (`kubectl top`) |
| **NVIDIA GPU Operator** | Доступ к GPU из подов |

```dot
digraph K8sArch {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    subgraph cluster_cp {
        label="Control Plane (n8)"
        style="rounded,dashed"
        color="#e91e63"
        fontname="system-ui"
        fontsize=11

        api [label="kube-apiserver\nREST API", shape=box, style="rounded,filled", fillcolor="#fce4ec", color="#e91e63"]
        etcd [label="etcd\nхранилище\nсостояния", shape=cylinder, style="filled", fillcolor="#f3e5f5", color="#9c27b0"]
        sched [label="kube-scheduler\nпланировщик", shape=box, style="rounded,filled", fillcolor="#fff3e0", color="#ff9800"]
        ctrl [label="controller-manager\nконтроллеры", shape=box, style="rounded,filled", fillcolor="#fff3e0", color="#ff9800"]

        api -> etcd
        api -> sched
        api -> ctrl
    }

    kubectl [label="kubectl\n(команда\nадмина)", shape=box, style="rounded,filled", fillcolor="#e3f2fd", color="#1976d2", fontsize=10]
    kubectl -> api [label="HTTPS\n:6443", color="#1976d2"]

    subgraph cluster_n8 {
        label="Worker: n8 (control-plane)"
        style="rounded"
        color="#ff9800"
        fontname="system-ui"
        fontsize=10

        kubelet_n8 [label="kubelet", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
        proxy_n8 [label="kube-proxy", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
        cr_n8 [label="containerd", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
        pods_n8 [label="Поды:\nvLLM 14B, PostgreSQL,\nRedis, ChromaDB", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]

        kubelet_n8 -> pods_n8
        cr_n8 -> pods_n8 [style=dashed]
    }

    subgraph cluster_n7 {
        label="Worker: n7 (worker)"
        style="rounded"
        color="#ff9800"
        fontname="system-ui"
        fontsize=10

        kubelet_n7 [label="kubelet", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
        proxy_n7 [label="kube-proxy", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
        cr_n7 [label="containerd", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
        pods_n7 [label="Поды:\nvLLM 32B, Gateway,\nGrafana, Prometheus", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]

        kubelet_n7 -> pods_n7
        cr_n7 -> pods_n7 [style=dashed]
    }

    api -> kubelet_n8 [label="задания", color="#e91e63", style=dashed]
    api -> kubelet_n7 [label="задания", color="#e91e63", style=dashed]
}
```

*Схема 3.2. Архитектура Kubernetes. Control Plane (n8) управляет, Worker Nodes (n8+n7) выполняют. Администратор общается только с apiserver через kubectl.*

### Как команда `kubectl apply` доходит до пода

Проследим путь команды `kubectl apply -f deployment.yaml`:

1. **kubectl** читает YAML-файл, преобразует в JSON, отправляет HTTPS-запрос на **apiserver** (порт 6443)
2. **apiserver** проверяет права (аутентификация, авторизация) и сохраняет желаемое состояние в **etcd**
3. **controller-manager** (конкретно Deployment Controller) замечает: «в etcd появился новый deployment, а подов для него нет»
4. Deployment Controller создаёт в etcd запись: «нужен новый под для deployment gateway»
5. **scheduler** видит непланированный под, выбирает подходящий узел (n7 — есть свободные ресурсы) и записывает в etcd: «под gateway-xyz должен быть на n7»
6. **kubelet** на n7 видит назначенный ему под, говорит containerd: «запусти контейнер gateway»
7. containerd запускает контейнер, kubelet докладывает apiserver: «под gateway-xyz Running»

Всё это занимает секунды, и администратору не нужно делать НИ ОДНОГО шага руками после `kubectl apply`.

---

## 3.3. Азбука Kubernetes — все примитивы

### Pod — минимальная единица

**Под** (Pod) — это один или несколько контейнеров, которые:
- Запускаются вместе на одном узле
- Имеют общий IP-адрес и общую файловую систему
- Масштабируются как единое целое

Обычно под = 1 контейнер. Иногда 2 (например, основной контейнер + sidecar для логов).

Жизненный цикл пода:

```
Pending → Running → Succeeded (завершился успешно)
                  → Failed (завершился с ошибкой)
```

А также: `CrashLoopBackOff` (падает и перезапускается), `OOMKilled` (убит за перерасход памяти), `ImagePullBackOff` (не может скачать образ).

```dot
digraph PodLifecycle {
    rankdir=LR
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=10]

    pending [label="Pending\n(ждёт назначения\nна узел)", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
    running [label="Running\n(контейнеры\nработают)", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    succeeded [label="Succeeded\n(завершился\nс кодом 0)", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
    failed [label="Failed\n(завершился\nс ошибкой)", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
    crash [label="CrashLoopBackOff\n(падает → перезапуск\n→ падает → ...)", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]

    pending -> running [label="контейнеры\nзапущены"]
    running -> succeeded [label="exit 0"]
    running -> failed [label="exit ≠0"]
    failed -> crash [label="перезапуск"]
    crash -> running [label="удачный\nзапуск"]
}
```

*Схема 3.3. Жизненный цикл Kubernetes Pod.*

### Deployment — «я хочу N подов»

**Deployment** — это контроллер, который управляет подами. Вы говорите: «я хочу 3 экземпляра Gateway с такими-то параметрами», и Deployment гарантирует, что их будет ровно 3. Если под упадёт — создаст новый. Если вы измените образ — обновит поды по одному (Rolling Update).

Основные поля deployment:

```yaml
spec:
  replicas: 3              # сколько подов нужно
  selector:
    matchLabels:
      app: gateway         # какие поды относятся к этому deployment
  strategy:
    type: RollingUpdate    # как обновлять
    rollingUpdate:
      maxSurge: 1          # сколько новых подов можно создать сверх replicas
      maxUnavailable: 1    # сколько старых подов можно убить одновременно
```

**Recreate vs RollingUpdate:**
- **RollingUpdate** (по умолчанию) — обновляет по одному: создаёт новый под → убивает старый → следующий. Нет простоя.
- **Recreate** — убивает ВСЕ старые поды, потом создаёт новые. Есть простой, но для GPU-подов это необходимо: две копии vLLM не могут использовать одни и те же GPU.

> ⚠️ **Почему vLLM использует Recreate.** Узел n8 имеет 2 GPU RTX 6000. vLLM 14B с TP=2 занимает обе карты. Если бы мы использовали RollingUpdate, K8s попытался бы запустить новый под (ему нужны 2 GPU), пока старый ещё работает (тоже занимает 2 GPU). Это 4 GPU, а есть только 2 — deadlock. Recreate решает проблему: старый под убивается (GPU освобождаются), потом запускается новый.

### Service — постоянный адрес

Поды — временные. Они создаются и умирают, их IP-адреса меняются. **Service** даёт постоянный IP-адрес и DNS-имя, которые не меняются.

Типы Service:

| Тип | Что делает | Пример в Aither |
|---|---|---|
| **ClusterIP** | IP виден только внутри кластера | `gateway:8080` |
| **NodePort** | Открывает порт на КАЖДОМ узле кластера (30000–32767) | `n7:30900 → gateway:8080` |
| **LoadBalancer** | Внешний балансировщик (в облаке) | Не используется |

```dot
digraph Service {
    rankdir=LR
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    client [label="Клиент\n(BFF на VPS2)", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]

    service [label="Service: gateway\nClusterIP: 10.98.238.242\nСелектор: app=gateway", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047", fontsize=9]

    subgraph cluster_pods {
        label="Поды"
        style=rounded
        color="#ff9800"

        pod1 [label="gateway-abc1\n10.244.1.10:8080", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800", fontsize=8]
        pod2 [label="gateway-def2\n10.244.2.15:8080", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800", fontsize=8]
        pod3 [label="gateway-ghi3\n10.244.1.20:8080", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800", fontsize=8]
    }

    nodeport [label="NodePort: 30900\n(на каждом узле)", shape=box, style="filled", fillcolor="#f3e5f5", color="#9c27b0"]

    client -> nodeport [label="http://VPS1:30900"]
    nodeport -> service
    service -> pod1 [label="балансировка"]
    service -> pod2
    service -> pod3
}
```

*Схема 3.4. Service балансирует трафик между подами. NodePort открывает порт на всех узлах.*

### ConfigMap и Secret — настройки отдельно от кода

Плохо: пароль от БД вшит в Docker-образ. Чтобы сменить пароль, нужно пересобрать образ.

Хорошо: пароль лежит в **Secret**, код читает его при запуске. Чтобы сменить пароль, обновляете Secret и перезапускаете поды.

```yaml
# ConfigMap — несекретные настройки
apiVersion: v1
kind: ConfigMap
metadata:
  name: gateway-catalog
data:
  catalog.yaml: |
    models:
      - name: qwen2.5-14b
        backend: "http://vllm:8000"

---
# Secret — секретные данные (пароли, токены, ключи)
apiVersion: v1
kind: Secret
metadata:
  name: pg-url
type: Opaque
stringData:
  url: "postgresql://aither:SuperSecret123@postgres/aither"
```

Как монтировать в под:
```yaml
volumes:
- name: catalog
  configMap:
    name: gateway-catalog       # ConfigMap → файл
- name: pg-secret
  secret:
    secretName: pg-url          # Secret → переменная окружения

containers:
- name: gateway
  volumeMounts:
  - name: catalog
    mountPath: /app/catalog.yaml
    subPath: catalog.yaml       # только один ключ ConfigMap как файл
  env:
  - name: PG_URL
    valueFrom:
      secretKeyRef:
        name: pg-url
        key: url                # конкретный ключ из секрета
```

### Namespace — изоляция

**Namespace** (пространство имён) — это «виртуальный кластер» внутри физического. Позволяет изолировать:
- Разработку от продакшена (dev/prod)
- Разные проекты (aither/monitoring)
- Разных пользователей (team-a/team-b)

В нашем кластере всё живёт в `default` (для простоты). Но правильно — разделять.

### Volume и PVC — постоянное хранилище

Поды перезапускаются — их файловая система очищается. **PersistentVolume (PV)** и **PersistentVolumeClaim (PVC)** дают постоянное хранилище.

```yaml
# PVC — запрос на хранилище: «мне нужно 100 GB»
kind: PersistentVolumeClaim
metadata:
  name: models-32b-pvc
spec:
  accessModes:
  - ReadWriteOnce     # только один под может писать
  resources:
    requests:
      storage: 100Gi
  storageClassName: local-path  # Local Path Provisioner
```

В поде монтируется как обычный том:
```yaml
volumes:
- name: models
  persistentVolumeClaim:
    claimName: models-32b-pvc
```

---

## 3.4. YAML-манифесты — мастер-класс

### Почему YAML

YAML (YAML Ain't Markup Language) — формат для описания данных, понятный человеку. Kubernetes использует его для всех манифестов.

**Правила YAML:**
- Отступы — **только пробелы** (не табуляция!), обычно 2 пробела
- `key: value` — словарь (ассоциативный массив)
- `- item` — элемент списка
- `# комментарий` — однострочный
- `|` — многострочный текст (сохраняет переносы)
- `>` — многострочный текст (сворачивает в одну строку)

### Структура манифеста

Любой манифест K8s имеет четыре обязательных поля верхнего уровня:

```yaml
apiVersion: apps/v1        # 1. Версия API K8s
                            #    apps/v1 = стабильная для Deployments
                            #    v1 = стабильная для Pod, Service, ConfigMap

kind: Deployment            # 2. Тип ресурса
                            #    Deployment, Service, ConfigMap, Secret,
                            #    Pod, HPA, Ingress, Namespace, PVC, ...

metadata:                   # 3. Метаданные: имя, метки
  name: gateway             #    Уникальное имя в namespace
  labels:                   #    Метки для поиска и группировки
    app: gateway

spec:                       # 4. Спецификация: ЧТО должно быть
  replicas: 1               #    Различается для каждого kind
```

### Полный разбор: gateway/deployment.yaml

Разберём **каждую строку** реального манифеста:

```yaml
apiVersion: apps/v1
# ↑ Версия API. apps/v1 — стабильная версия для работы с Deployments.
#   Бывают: v1 (Pod, Service), autoscaling/v2 (HPA), networking.k8s.io/v1 (Ingress)

kind: Deployment
# ↑ Тип ресурса. Deployment управляет подами (создаёт, обновляет, откатывает).

metadata:
  name: gateway
  # ↑ Имя deployment. Должно быть уникальным в namespace.
  #   Поды получат имена: gateway-<random-suffix> (gateway-7f8b9c-abc1)

  labels:
    app: gateway
  # ↑ Метки — пары ключ-значение для поиска.
  #   Команда: kubectl get pods -l app=gateway

  namespace: default
  # ↑ В каком namespace живёт deployment.
  #   Если не указать — default.

spec:
  replicas: 1
  # ↑ Сколько подов должно работать одновременно.
  #   1 = один экземпляр Gateway. Можно увеличить для отказоустойчивости.

  revisionHistoryLimit: 10
  # ↑ Сколько старых ReplicaSet хранить (для отката).
  #   10 = можно откатиться на 10 версий назад.

  selector:
    matchLabels:
      app: gateway
  # ↑ Какие поды принадлежат этому deployment.
  #   Должно совпадать с labels в template.

  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 25%
  # ↑ Стратегия обновления.
  #   RollingUpdate: обновляет поды по одному, без остановки сервиса.
  #   maxSurge=25%: можно создать 1 лишний под (25% от 1 = 0.25 → округляется до 1).
  #   maxUnavailable=25%: можно убить 1 старый под.

  template:
  # ↑ Шаблон для создания подов. Всё, что внутри — применяется к каждому поду.

    metadata:
      labels:
        app: gateway
    # ↑ Метки пода. Должны совпадать с selector.matchLabels!

    spec:
    # ↑ Спецификация пода (контейнеры, тома, переменные).

      containers:
      - name: gateway
      # ↑ Имя контейнера внутри пода. Может быть любым.

        image: ghcr.io/dedvmedved-dot/aither-project-gateway:latest
        # ↑ Docker-образ. Откуда скачивать.
        #   ghcr.io = GitHub Container Registry.
        #   latest = тег (обычно последняя версия).

        imagePullPolicy: Always
        # ↑ Когда скачивать образ заново.
        #   Always = при каждом запуске (гарантирует свежую версию).
        #   IfNotPresent = только если нет локально.

        ports:
        - containerPort: 8080
          name: http
          protocol: TCP
        # ↑ Порты, которые слушает контейнер.
        #   Это декларация — порт не открывается автоматически!

        env:
        - name: VLLM_URL
          value: "http://vllm:8000"
        # ↑ Переменная окружения. vllm — это DNS-имя Service в кластере.

        - name: PG_URL
          valueFrom:
            secretKeyRef:
              key: url
              name: pg-url
        # ↑ Переменная из Secret. Не светит пароль в манифесте!

        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          # ↑ Гарантированные ресурсы.
          #   100m = 0.1 ядра CPU (m = milli, тысячные доли).
          #   128Mi = 128 мебибайт памяти.

          limits:
            cpu: 500m
            memory: 512Mi
          # ↑ Максимальные ресурсы.
          #   Если превысит память → OOMKilled.
          #   CPU не убивает, а throttles (замедляет).

        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
          failureThreshold: 3
          timeoutSeconds: 1
        # ↑ Проверка готовности.
        #   K8s каждые 5 секунд делает GET /health.
        #   Если 3 раза подряд неудача → под считается неготовым → трафик не идёт.
        #   initialDelaySeconds=5: первые 5 секунд после старта не проверять.

        volumeMounts:
        - name: catalog
          mountPath: /app/catalog.yaml
          subPath: catalog.yaml
        # ↑ Монтируем ConfigMap как файл.
        #   subPath: монтируем только один ключ (catalog.yaml), а не всю папку.

      volumes:
      - name: catalog
        configMap:
          name: gateway-catalog
      # ↑ Сам том. Ссылается на ConfigMap gateway-catalog.

      - name: wiki
        configMap:
          name: gateway-wiki
      # ↑ Ещё один ConfigMap — база знаний.

      - name: delegation-key
        configMap:
          name: delegation-public-key
      # ↑ Публичный ключ для JWT-подписи.
```

### ✏️ Практика: «переведи манифест на русский»

Прочитайте манифест `vllm-14b/deployment.yaml` и переведите **своими словами**:
1. Какой образ используется?
2. Сколько GPU запрошено?
3. Почему `strategy: Recreate`?
4. На каком узле должен запуститься под? (подсказка: `nodeSelector`)
5. Какой `runtimeClassName` и зачем?

---

## 3.5. Кластер Aither — анатомия

### Топология

Наш кластер Kubernetes v1.33.5 состоит из двух узлов:

| Узел | Роль | Адрес | GPU | Что запущено |
|---|---|---|---|---|
| **n8** | control-plane + worker | 10.129.13.78 | 2× RTX 6000 | vLLM 14B, PostgreSQL, Redis, ChromaDB, kube-apiserver, etcd |
| **n7** | worker | 10.129.13.77 | 2× RTX 6000 | vLLM 32B, Gateway, Prometheus, Grafana, Flannel, CoreDNS |

Особенность: n8 совмещает роли control-plane и worker. В продакшене так не делают (control-plane должен быть отдельно от рабочих нагрузок), но для пилотного проекта с двумя серверами — допустимо.

### Flannel VXLAN: как поды видят друг друга

Проблема: под на n8 имеет IP `10.244.1.10`, под на n7 — `10.244.2.15`. Их разделяет физическая сеть. Как им общаться?

**Flannel** создаёт overlay-сеть (сеть поверх сети). Он инкапсулирует IP-пакеты от пода на n8 в VXLAN-пакеты и отправляет через физическую сеть на n7, где они распаковываются и доставляются поду.

```
Под на n8 (10.244.1.10)
  → пакет для 10.244.2.15
    → Flannel на n8: заворачивает в VXLAN
      → физическая сеть (10.129.13.78 → 10.129.13.77)
        → Flannel на n7: распаковывает
          → под на n7 (10.244.2.15)
```

Overlay-сеть: `10.244.0.0/16` (65 536 адресов, хватит на тысячи подов).

### NodePort: внешний мир стучится в кластер

ClusterIP-сервисы видны только внутри кластера. Чтобы внешний мир (VPS1) мог достучаться до Gateway, используется **NodePort**.

NodePort открывает один и тот же порт на **каждом** узле кластера. Порт выбирается из диапазона 30000–32767.

| Сервис | ClusterIP | NodePort | На каком узле物理чески |
|---|---|---|---|
| Gateway | `gateway:8080` | **30900** | n7 |
| vLLM 14B | `vllm:8000` | **32293** | n8 |
| vLLM 32B | `vllm-qwen32b:8000` | **32294** | n7 |
| Grafana | `grafana:80` | **30300** | n7 |

```
VPS1 (170.168.91.95) → nginx :30900 → любой узел K8s:30900 → Gateway:8080
```

**Важно:** NodePort работает на ВСЕХ узлах, даже если под физически только на одном. K8s автоматически проксирует трафик на нужный узел.

### nodeSelector: привязка к серверу

Не все узлы одинаковы. n8 имеет модели в `/data/models`, n7 — в PVC. vLLM 14B должен запускаться только на n8, vLLM 32B — только на n7.

```yaml
nodeSelector:
  kubernetes.io/hostname: bootsman-k8s-clnt01-n8-gpu
```

Это гарантирует, что под с vLLM 14B никогда не запустится на n7 (где нет нужной модели).

### Taints и Tolerations

Control-plane узлы имеют **taint** (ограничение): `node-role.kubernetes.io/control-plane:NoSchedule`. Это значит: «не запускай обычные поды на этом узле». Но наш n8 — и control-plane, и worker. Поэтому на нём:
- Системные поды (apiserver, etcd) — запускаются
- vLLM 14B — запускается, потому что у него есть **toleration** (разрешение) на этот taint, ИЛИ taint снят

Taint — это табличка «Посторонним вход воспрещён». Toleration — пропуск «Этому можно».

```dot
digraph K8sClusterAither {
    rankdir=TB
    bgcolor="#ffffff"
    node [fontname="system-ui", fontsize=9]

    subgraph cluster_phys {
        label="Физическая сеть: 10.129.13.0/24 (VLAN 308)"
        style="rounded,dashed"
        color="#ff9800"
        fontname="system-ui"
        fontsize=11

        subgraph cluster_n8 {
            label="n8 (control-plane + worker)\n10.129.13.78 | 2× RTX 6000"
            style="rounded"
            color="#ff9800"
            fontname="system-ui"

            subgraph cluster_n8_pods {
                label="Поды"
                style=rounded
                color="#e91e63"

                vllm14 [label="vLLM 14B\nTP=2\n28 tok/s", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
                postgres [label="PostgreSQL\nбиллинг", shape=box, style="filled", fillcolor="#f3e5f5", color="#9c27b0"]
                redis [label="Redis\nrate limit", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
                chroma [label="ChromaDB\nRAG", shape=box, style="filled", fillcolor="#e0f7fa", color="#00838f"]
            }

            control [label="Control Plane:\napiserver, etcd,\nscheduler, ctrl-mgr", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800", fontsize=8]
        }

        subgraph cluster_n7 {
            label="n7 (worker)\n10.129.13.77 | 2× RTX 6000"
            style="rounded"
            color="#ff9800"
            fontname="system-ui"

            subgraph cluster_n7_pods {
                label="Поды"
                style=rounded
                color="#e91e63"

                vllm32 [label="vLLM 32B\nTP=2, GPTQ\n35 tok/s", shape=box, style="filled", fillcolor="#fce4ec", color="#e91e63"]
                gateway [label="Gateway\nPython 3.12\nHPA", shape=box, style="filled", fillcolor="#fff3e0", color="#ff9800"]
                grafana [label="Grafana\n:30300", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
                prom [label="Prometheus", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
            }
        }
    }

    // Flannel overlay
    flannel [label="Flannel VXLAN\n10.244.0.0/16", shape=box, style="filled", fillcolor="#e8f5e9", color="#43a047"]
    vllm14 -> flannel [style=dashed, dir=both]
    gateway -> flannel [style=dashed, dir=both]

    // External access
    external [label="Внешний мир\n(VPS1:30900)", shape=box, style="filled", fillcolor="#e3f2fd", color="#1976d2"]
    np [label="NodePort\n:30900", shape=box, style="filled", fillcolor="#f3e5f5", color="#9c27b0", fontsize=8]
    external -> np -> gateway
}
```

*Схема 3.5. Кластер Aither: n8 (control-plane + vLLM 14B + DB) и n7 (vLLM 32B + Gateway + мониторинг). Flannel соединяет поды через overlay-сеть.*

---

## 3.6. Основные команды kubectl

Короткая таблица — полная шпаргалка в Приложении B.

| Команда | Что делает |
|---|---|
| `kubectl get pods` | Список подов |
| `kubectl get pods -o wide` | С IP и узлом |
| `kubectl get pods -w` | Watch — следить в реальном времени |
| `kubectl describe pod <name>` | ВСЁ о поде (события, состояние) |
| `kubectl logs <pod-name>` | Логи пода |
| `kubectl logs -f <pod-name>` | Логи в реальном времени |
| `kubectl logs -l app=gateway --all-containers` | Логи всех контейнеров всех подов с меткой |
| `kubectl exec -it <pod> -- bash` | Зайти внутрь пода |
| `kubectl apply -f file.yaml` | Применить манифест (создать/обновить) |
| `kubectl delete -f file.yaml` | Удалить ресурс |
| `kubectl rollout restart deploy/gateway` | Перезапустить все поды deployment |
| `kubectl rollout undo deploy/gateway` | Откатить deployment |
| `kubectl scale --replicas=3 deploy/gateway` | Изменить количество реплик |
| `kubectl get nodes` | Список узлов |
| `kubectl top pods` | Потребление CPU/памяти |
| `kubectl get events --sort-by=.metadata.creationTimestamp` | Последние события кластера |
| `kubectl port-forward pod/gateway-abc 8080:8080` | Временный проброс порта |

---

## 3.7. ✏️ Практикум: Kubernetes

### Задание 1. «Кластер на бумаге»
Нарисуйте схему кластера Aither: два узла, на каждом — поды, соедините их Flannel-сетью, покажите NodePort для внешнего доступа.

### Задание 2. «Читаем манифесты»
Возьмите `k8s/vllm-32b/deployment.yaml` и ответьте:
1. Сколько реплик?
2. Какой образ?
3. Какая стратегия обновления и почему?
4. На каком узле должен запуститься под?
5. Сколько GPU запрошено и лимит?
6. Какой `runtimeClassName` и зачем?

### Задание 3. «Словарь термина»
Выпишите и дайте определение:
- Control Plane, Worker Node
- kube-apiserver, etcd, scheduler, controller-manager
- kubelet, kube-proxy, containerd
- Pod, Deployment, Service, ConfigMap, Secret
- Namespace, Volume, PVC
- Flannel, VXLAN, NodePort
- nodeSelector, taint, toleration

### Задание 4. «Первый kubectl»
Если есть доступ к кластеру:
```bash
kubectl get nodes                    # узлы
kubectl get pods -A                  # все поды во всех namespace
kubectl get pods -o wide             # с IP и узлом
kubectl describe node n7             # информация об узле
kubectl top pods                     # потребление ресурсов
kubectl get events --sort-by=.metadata.creationTimestamp | tail -20
```

---

**Итог главы 3.** Вы узнали:
- Зачем нужен Kubernetes (размещение, самовосстановление, масштабирование, сеть)
- Как устроен K8s: Control Plane (apiserver, etcd, scheduler) и Worker Nodes (kubelet, containerd)
- Все примитивы: Pod, Deployment (Recreate/RollingUpdate), Service (ClusterIP/NodePort), ConfigMap, Secret, PVC
- Как читать YAML-манифесты (4 обязательных поля, построчный разбор gateway/deployment.yaml)
- Как устроен кластер Aither: n8 (control-plane + vLLM 14B) и n7 (worker + vLLM 32B), Flannel VXLAN, NodePort-ы

В следующей главе — искусственный интеллект и LLM: от нейросети до токенов.
