# Часть IV. Production-эксплуатация и продвинутые темы

**Для молодых специалистов (базовый уровень: школьная информатика)**

**Редакция 3.0** · 10.07.2026 · В разработке

---

> **О части IV.** MVP работает. Один сервер, один пользователь, одна модель.
> Теперь превращаем прототип в промышленную систему: несколько серверов,
> десятки организаций, реальные деньги, защита от атак, RAG, аудит.
>
> Каждая глава — законченный production-компонент с кодом и схемами.

---

## Содержание

- **Глава 19.** High Availability: отказоустойчивый Kubernetes ✅
- **Глава 20.** Multi-tenant архитектура: изоляция организаций 🔴
- **Глава 21.** Платёжный шлюз и монетизация 🔴
- **Глава 22.** Enterprise-безопасность: mTLS и AI Security Gateway 🔴
- **Глава 23.** Каталог моделей и RAG-подсистема 🔴
- **Глава 24.** Production Readiness: от MVP к промышленной эксплуатации 🔴

---

<!-- ================================================================= -->
<!-- ГЛАВА 19. HIGH AVAILABILITY                                        -->
<!-- ================================================================= -->

## Глава 19. High Availability: отказоустойчивый Kubernetes

> **Состояние:** ✅ готово — текст + 7 DOT-схем.
> **Объём:** ~30 стр., 7 схем, 5 таблиц.

**Цель главы:** из одного control-plane узла сделать кластер Kubernetes, который переживает отказ любого компонента — apiserver, etcd, control-plane.

> ✏️ **Перед прочтением** убедитесь, что вы освоили Главу 3 (Kubernetes: от Pod до кластера) и Главу 9 (Развёртывание Kubernetes).

---

### 19.1 Зачем нужна отказоустойчивость

#### Проблема одного сервера

В Главе 9 мы развернули Kubernetes на одном узле: один kube-apiserver, один etcd, один controller-manager, один scheduler. Пока узел жив — всё работает. Но что будет, если:

- Сервер перезагрузится (плановое обслуживание, сбой питания)?
- Откажет диск с etcd-данными?
- Сетевой интерфейс потеряет связь?

Ответ: **кластер остановится**. Нельзя создать новый Pod, нельзя изменить ConfigMap, нельзя даже посмотреть `kubectl get pods`. API-сервер недоступен — Kubernetes «ослеп».

Такая архитектура называется **Single Point of Failure (SPOF)** — единственная точка отказа.

```dot
digraph G {
  rankdir=TB; bgcolor="#ffffff"; fontname="Arial";
  node [fontname="Arial", fontsize=11, style=filled];
  edge [fontname="Arial", fontsize=9];

  subgraph cluster_k8s {
    label="Kubernetes Cluster (один узел)"; style=dashed; color="#7b8ca0"; bgcolor="#f5f7fa";
    
    cp [label="Control-Plane\n(n8)\napiserver + etcd\ncontroller-manager\nscheduler", shape=box, fillcolor="#ffcdd2", color="#c62828"];
    
    subgraph cluster_workers {
      label="Workers"; style=dashed; color="#90a4ae"; bgcolor="#ffffff";
      w1 [label="Worker\n(n7)\nvLLM + Gateway", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    }
  }

  users [label="Пользователи", shape=cylinder, fillcolor="#e3f2fd", color="#1565c0"];
  vps2 [label="VPS2\nBFF + Portal", shape=box, fillcolor="#fff9c4", color="#f9a825"];
  
  users -> vps2 [label="HTTPS"];
  vps2 -> cp [label="kubectl\n:6443", color="#c62828", fontcolor="#c62828"];
  cp -> w1 [label="управление", style=dashed];

  // SPOF annotations
  spof1 [label="⚠️ SPOF\nОдин etcd\nНет кворума", shape=note, fillcolor="#ffebee", color="#c62828", fontcolor="#c62828", fontsize=10];
  spof2 [label="⚠️ SPOF\nОдин\napiserver", shape=note, fillcolor="#ffebee", color="#c62828", fontcolor="#c62828", fontsize=10];
  
  spof1 -> cp [style=dotted, color="#c62828"];
  spof2 -> cp [style=dotted, color="#c62828"];
}
```

> ⚠️ **На схеме:** красным отмечены SPOF — один etcd и один apiserver. Отказ любого из них = кластер не работает.

#### 99.9% vs 99.99%: цена простоя

| Доступность | Простой в год | Простой в месяц | Допустимо для |
|---|---|---|---|
| 99% («две девятки») | 3.65 дня | 7.2 часа | Dev-стенд |
| 99.9% («три девятки») | 8.76 часа | 43 минуты | Staging |
| 99.99% («четыре девятки») | 52 минуты | 4.3 минуты | Production |
| 99.999% («пять девяток») | 5.26 минуты | 26 секунд | Телеком/банкинг |

Для Aither как платформы, предоставляющей LLM-инференс внешним клиентам, целевой уровень — **99.9% (три девятки)**. Это значит: не более 43 минут простоя в месяц.

> 📊 **Таблица 19.1.** Уровни доступности и допустимый простой.

#### Как достигается высокая доступность

Три принципа:

1. **Избыточность (Redundancy)** — каждый критический компонент запущен в нескольких экземплярах на разных физических серверах.
2. **Балансировка (Load Balancing)** — трафик распределяется между экземплярами; отказ одного не прерывает обслуживание.
3. **Консенсус (Consensus)** — несколько узлов etcd договариваются о состоянии кластера; потеря одного не останавливает систему.

В этой главе мы пошагово реализуем все три принципа для Kubernetes-кластера Aither.

---

### 19.2 Теория RAFT и внешний etcd

#### Что такое etcd и почему он критичен

`etcd` — это распределённое key-value хранилище, в котором Kubernetes хранит **всё** состояние кластера:

- Какие Pod'ы запущены и на каких узлах
- ConfigMap'ы и Secrets
- Service'ы, Endpoint'ы, Ingress'ы
- Состояние планировщика и controller-manager

Если etcd теряет данные — кластер «забывает» всё своё состояние. Это как если бы у вас украли бортовой журнал самолёта в полёте. **etcd — самый важный компонент Kubernetes.**

#### Как работает RAFT-консенсус

RAFT — это алгоритм, который позволяет нескольким серверам (узлам etcd) договориться о едином состоянии, даже если часть из них выходит из строя.

**Три роли узла в RAFT:**

| Роль | Описание | Сколько в кластере |
|---|---|---|
| **Лидер (Leader)** | Принимает все записи от клиентов, реплицирует их на follower'ов | Всегда 1 |
| **Follower** | Пассивно реплицирует логи от лидера, отвечает на запросы чтения | Остальные |
| **Кандидат (Candidate)** | Временная роль при выборах (если лидер упал) | 0 или 1 |

```dot
digraph G {
  rankdir=LR; bgcolor="#ffffff"; fontname="Arial";
  node [fontname="Arial", fontsize=11, style=filled];
  edge [fontname="Arial", fontsize=9];

  subgraph cluster_raft {
    label="RAFT Cluster (3 узла)"; style=dashed; color="#7b8ca0"; bgcolor="#f5f7fa";
    
    leader [label="Лидер\n(Leader)\n● принимает записи\n● реплицирует логи", shape=box, fillcolor="#c8e6c9", color="#2e7d32", width=2.2];
    
    f1 [label="Follower 1\n● реплицирует\n● может стать лидером", shape=box, fillcolor="#e3f2fd", color="#1565c0"];
    f2 [label="Follower 2\n● реплицирует\n● может стать лидером", shape=box, fillcolor="#e3f2fd", color="#1565c0"];
  }

  client [label="Клиент\n(kube-apiserver)", shape=cylinder, fillcolor="#fff9c4", color="#f9a825"];

  client -> leader [label="1. Запись\n(PUT /key)", color="#2e7d32", fontcolor="#2e7d32"];
  leader -> f1 [label="2. AppendEntries\n(репликация)", color="#1565c0"];
  leader -> f2 [label="2. AppendEntries\n(репликация)", color="#1565c0"];
  f1 -> leader [label="3. ACK ✓", color="#7b8ca0"];
  f2 -> leader [label="3. ACK ✓", color="#7b8ca0"];
  leader -> client [label="4. OK (кворум)\n✓ запись применена", color="#2e7d32", fontcolor="#2e7d32"];

  quorum [label="Кворум = ⌊N/2⌋+1 = 2\n(2 из 3 подтвердили → запись принята)", shape=note, fillcolor="#f3e5f5", color="#7b1fa2", fontsize=10];
  quorum -> leader [style=dotted, dir=none];
}
```

> 📊 **Таблица 19.2.** Роли узлов в RAFT-кластере.

#### Поток записи (Write Path)

1. Клиент (kube-apiserver) отправляет запись лидеру: `PUT /key = value`
2. Лидер добавляет запись в **свой** лог и рассылает `AppendEntries` всем follower'ам
3. Follower'ы добавляют запись в свои логи и отвечают `ACK`
4. Когда **большинство** (кворум) подтвердило — запись считается **committed**
5. Лидер применяет запись к своему состоянию и отвечает клиенту `OK`

#### Что такое кворум и почему их должно быть нечётное количество

**Кворум = ⌊N/2⌋ + 1** (половина узлов + 1).

| Всего узлов | Кворум | Отказов переживёт |
|---|---|---|
| 1 | 1 | 0 ⚠️ |
| 2 | 2 | 0 ⚠️ (нет кворума при отказе любого) |
| 3 | 2 | 1 ✅ |
| 5 | 3 | 2 ✅ |
| 7 | 4 | 3 ✅ |

> ⚠️ **Почему 2 узла — нечётное?** При N=2 кворум = 2. Если любой узел падает — остаётся 1, а нужно 2. Кворум потерян, etcd останавливается. Поэтому **production-минимум = 3 узла**.

#### Выборы лидера

Если лидер перестаёт отвечать (heartbeat timeout ~150-300ms):

1. Follower замечает, что heartbeat не приходит
2. Увеличивает свой `Term` (номер эпохи) и становится кандидатом
3. Голосует за себя и рассылает `RequestVote` другим узлам
4. Если получает большинство голосов — становится новым лидером
5. Если голоса разделились — таймаут и новый раунд выборов

```dot
digraph G {
  rankdir=LR; bgcolor="#ffffff"; fontname="Arial";
  node [fontname="Arial", fontsize=10, style=filled];
  edge [fontname="Arial", fontsize=9];

  // Начальное состояние
  subgraph cluster_t0 {
    label="T0: Лидер жив"; bgcolor="#f1f8e9"; color="#2e7d32";
    l [label="Лидер ●\nTerm=5", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    f1 [label="Follower\nTerm=5", shape=box, fillcolor="#e3f2fd", color="#1565c0"];
    f2 [label="Follower\nTerm=5", shape=box, fillcolor="#e3f2fd", color="#1565c0"];
  }

  // Лидер упал
  subgraph cluster_t1 {
    label="T1: Лидер упал ✗"; bgcolor="#ffebee"; color="#c62828";
    l_dead [label="✗ Упал", shape=box, fillcolor="#ffcdd2", color="#c62828", style="dashed"];
    f1_timeout [label="Follower\nHeartbeat\ntimeout!", shape=box, fillcolor="#fff9c4", color="#f9a825"];
    f2_wait [label="Follower\nждёт", shape=box, fillcolor="#e3f2fd", color="#1565c0"];
  }

  // Выборы
  subgraph cluster_t2 {
    label="T2: Выборы"; bgcolor="#fff3e0"; color="#e65100";
    f1_cand [label="Кандидат ▲\nTerm=6\nголосует за себя", shape=box, fillcolor="#ffe0b2", color="#e65100"];
    f2_vote [label="Follower\nTerm=6\nголосует ✓", shape=box, fillcolor="#e3f2fd", color="#1565c0"];
  }

  // Новый лидер
  subgraph cluster_t3 {
    label="T3: Новый лидер"; bgcolor="#f1f8e9"; color="#2e7d32";
    new_l [label="Лидер ★\nTerm=6\n(бывший кандидат)", shape=box, fillcolor="#a5d6a7", color="#1b5e20"];
    f2_final [label="Follower\nTerm=6", shape=box, fillcolor="#e3f2fd", color="#1565c0"];
  }

  // Связи между стадиями
  l -> l_dead [label="отказ", color="#c62828", fontcolor="#c62828", style=bold];
  f1 -> f1_timeout [label="таймаут\n~150-300ms", fontsize=8];
  
  f1_timeout -> f1_cand [label="становится\nкандидатом", color="#e65100", fontcolor="#e65100"];
  f1_cand -> f2_vote [label="RequestVote", color="#e65100"];
  f2_vote -> f1_cand [label="Granted", color="#2e7d32"];
  
  f1_cand -> new_l [label="кворум ✓\n(2 из 2)", color="#1b5e20", fontcolor="#1b5e20", style=bold];
  f2_wait -> f2_vote [style=invis];
}
```

#### Почему etcd нужно выносить наружу

В стандартной установке `kubeadm` etcd работает как статический Pod на control-plane узле. Это создаёт проблемы:

- etcd конкурирует за CPU/IO с apiserver, scheduler, controller-manager
- Отказ control-plane узла убивает и etcd (хотя физически диск с данными может быть цел)
- Невозможно добавить 3-й etcd-узел без добавления 3-го control-plane

**Решение:** вынести etcd на отдельные узлы (физические или виртуальные серверы, не входящие в Kubernetes-кластер).

В нашем стенде Aither etcd вынесен на **VPS1** — сервер вне кластера, соединённый с n8 через VPN-туннель.

> 📊 **Таблица 19.3.** Сравнение: etcd внутри кластера vs внешний etcd.

| Критерий | etcd внутри (default) | etcd снаружи (наш выбор) |
|---|---|---|
| Изоляция ресурсов | ❌ Делит CPU/IO с control-plane | ✅ Отдельный сервер |
| Добавление 3-го etcd | ❌ Нужен 3-й control-plane узел | ✅ Добавляем любой сервер |
| Восстановление из снапшота | Сложно (Static Pod) | Просто (`systemctl restart etcd`) |
| Сетевая задержка | ~0 (localhost) | ~1-10ms (VPN/локальная сеть) |
| Требования | — | Стабильный сетевой канал |

---

### 19.3 Multi-master Kubernetes: пошаговое развёртывание

> ✏️ **Этот раздел — практический.** Мы возьмём работающий кластер из Главы 9 (один control-plane) и добавим второй. Все команды проверены на стенде Aither.

#### Шаг 1: Готовим второй узел

На узле **n7** (втором сервере с GPU) выполняем:

```bash
# Установка компонентов Kubernetes (Astra Linux SE 1.8)
apt-get update && apt-get install -y apt-transport-https ca-certificates curl
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.33/deb/Release.key | \
  gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] \
  https://pkgs.k8s.io/core:/stable:/v1.33/deb/ /' > /etc/apt/sources.list.d/kubernetes.list
apt-get update
apt-get install -y kubelet kubeadm kubectl
apt-mark hold kubelet kubeadm kubectl
```

#### Шаг 2: Копируем сертификаты

Kubernetes использует Certificate Authority (CA) для подписи всех внутренних сертификатов. Второй control-plane узел должен доверять тому же CA, что и первый.

```bash
# На ПЕРВОМ узле (n8) — создаём архив сертификатов
cd /etc/kubernetes/pki
tar czf /tmp/k8s-certs.tar.gz ca.crt ca.key sa.pub sa.key front-proxy-ca.crt front-proxy-ca.key

# Копируем на второй узел
scp /tmp/k8s-certs.tar.gz root@10.129.13.77:/tmp/

# На ВТОРОМ узле (n7) — распаковываем
cd /etc/kubernetes
tar xzf /tmp/k8s-certs.tar.gz
```

#### Шаг 3: Генерируем join-команду

На **первом** control-plane (n8):

```bash
# Создаём новый токен (действует 24 часа)
kubeadm token create --print-join-command
```

Пример вывода:
```
kubeadm join 10.129.13.78:6443 --token abcdef.0123456789abcdef \
  --discovery-token-ca-cert-hash sha256:1234...
```

Это базовая команда для присоединения **worker-узла**. Для control-plane нужен дополнительный ключ:

```bash
# Генерируем certificate-key (для шифрования секретов при передаче)
kubeadm init phase upload-certs --upload-certs
```

Пример вывода:
```
[upload-certs] Using certificate key:
8902e1d4f4c2a3b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7
```

#### Шаг 4: Присоединяем control-plane

**Итоговая команда** на n7:

```bash
kubeadm join 10.129.13.78:6443 \
  --token abcdef.0123456789abcdef \
  --discovery-token-ca-cert-hash sha256:1234... \
  --control-plane \
  --certificate-key 8902e1d4f4c2a3b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7
```

Что произойдёт:
1. kubeadm подключится к apiserver на n8
2. Скачает конфигурацию кластера (CA, сертификаты, манифесты)
3. Запустит локальный etcd (если не настроен внешний) — **в нашем случае etcd внешний**
4. Запустит kube-apiserver, controller-manager, scheduler
5. Зарегистрирует узел в кластере

```dot
digraph G {
  rankdir=TB; bgcolor="#ffffff"; fontname="Arial";
  node [fontname="Arial", fontsize=10, style=filled];
  edge [fontname="Arial", fontsize=9];

  s1 [label="1. Готовим новый узел\n- Astra Linux 1.8\n- kubectl, kubeadm, kubelet\n- сеть (VLAN 308)", shape=box, fillcolor="#e3f2fd", color="#1565c0"];
  s2 [label="2. Копируем сертификаты\nс первого CP\nscp /etc/kubernetes/pki/ca.*\n/etc/kubernetes/pki/sa.*", shape=box, fillcolor="#e3f2fd", color="#1565c0"];
  s3 [label="3. Генерируем токен\nна первом CP\nkubeadm token create\n--print-join-command", shape=box, fillcolor="#fff9c4", color="#f9a825"];
  s4 [label="4. Присоединяем узел\nkubeadm join ...\\\n--control-plane\\\n--certificate-key ...", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
  
  s5 [label="5. Проверяем\nkubectl get nodes\n→ Ready ✓", shape=box, fillcolor="#a5d6a7", color="#1b5e20"];

  pitfall [label="⚠️ Питфолл Astra Linux:\nParsec может блокировать\nсертификаты etcd.\nРешение: parsec=0 в GRUB", shape=note, fillcolor="#ffebee", color="#c62828", fontcolor="#c62828", fontsize=9];

  s1 -> s2;
  s2 -> s3;
  s3 -> s4;
  s4 -> s5;
  s4 -> pitfall [style=dotted, color="#c62828"];
  pitfall -> s5 [style=dotted, color="#c62828", label="фикс"];

  // commands
  cmd [label="Итоговая команда:\nkubeadm join 10.129.13.78:6443 --token ... \\\n  --discovery-token-ca-cert-hash sha256:... \\\n  --control-plane \\\n  --certificate-key ...", shape=box, fillcolor="#f3e5f5", color="#7b1fa2", fontsize=9];
  s4 -> cmd [style=dotted, dir=none];
}
```

#### Шаг 5: Проверяем

```bash
kubectl get nodes
```

Ожидаемый вывод:
```
NAME                         STATUS   ROLES           AGE   VERSION
bootsman-k8s-clnt01-n8-gpu   Ready    control-plane   5d    v1.33.5
bootsmam-k8s-clnt01-n7-gpu   Ready    control-plane   2d    v1.33.5
```

Оба узла в роли `control-plane` — HA работает.

> ⚠️ **Питфолл Astra Linux:** на стенде Aither при добавлении n7 возникла проблема с Parsec — сертификаты etcd не проходили проверку мандатного доступа. Решение: временно отключить Parsec (`parsec=0` в GRUB) на время join'а, затем включить обратно с `max_ilev=63 execstack=1`.

#### etcd-кластер: добавляем VPS1

Поскольку у нас внешний etcd (на VPS1 и n8), добавляем n7 как клиент etcd (не как член кластера):

На n7 обновляем `/etc/kubernetes/manifests/kube-apiserver.yaml`:

```yaml
spec:
  containers:
  - command:
    - kube-apiserver
    ...
    - --etcd-servers=https://170.168.91.95:2379,https://10.129.13.78:2379
    - --etcd-cafile=/etc/kubernetes/pki/etcd/ca.crt
    - --etcd-certfile=/etc/kubernetes/pki/etcd/server.crt
    - --etcd-keyfile=/etc/kubernetes/pki/etcd/server.key
```

После изменения apiserver автоматически перезапустится (Static Pod).

> 📊 **Таблица 19.4.** Компоненты HA-кластера Aither.

| Компонент | n8 (40.51) | n7 (40.50) | VPS1 (170.168.91.95) |
|---|---|---|---|
| etcd | ✅ (член кластера, лидер) | — | ✅ (член кластера, follower) |
| kube-apiserver | ✅ | ✅ | — |
| controller-manager | ✅ | ✅ | — |
| scheduler | ✅ | ✅ | — |
| nginx LB | — | — | ✅ (:6443 → n8 + n7) |

---

### 19.4 Load Balancer для apiserver

#### Зачем нужен балансировщик

Теперь у нас два apiserver (на n8 и n7), но клиенты (kubectl, BFF) должны обращаться по одному адресу. Если один apiserver упадёт — клиент должен автоматически переключиться на второй.

**Решение:** nginx в режиме TCP reverse proxy (stream) на VPS1.

#### Настройка nginx LB

На VPS1 создаём конфигурацию `/etc/nginx/sites-available/k8s-lb`:

```nginx
stream {
    upstream k8s-api {
        server 10.129.13.78:6443;  # n8 (primary)
        server 10.129.13.77:6443;  # n7
    }

    server {
        listen 6443 ssl;
        proxy_pass k8s-api;
        proxy_connect_timeout 1s;
        proxy_timeout 3s;

        # SSL для внешних подключений
        ssl_certificate     /etc/nginx/ssl/k8s-lb.crt;
        ssl_certificate_key /etc/nginx/ssl/k8s-lb.key;
    }
}
```

Активируем:

```bash
ln -s /etc/nginx/sites-available/k8s-lb /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

#### Проверка

```bash
# С ВНЕШНЕГО клиента (через LB)
kubectl --server https://170.168.91.95:6443 get nodes

# Останавливаем apiserver на n8
ssh n8 "systemctl stop kubelet"

# Пробуем снова — запрос должен уйти на n7
kubectl --server https://170.168.91.95:6443 get nodes
```

```dot
digraph G {
  rankdir=LR; bgcolor="#ffffff"; fontname="Arial";
  node [fontname="Arial", fontsize=10, style=filled];
  edge [fontname="Arial", fontsize=9];

  subgraph cluster_lb {
    label="nginx LB (VPS1:6443)"; bgcolor="#f1f8e9"; color="#2e7d32";
    
    nginx [label="nginx\nstream {\n  upstream k8s-api {\n    server 10.129.13.78:6443;\n    server 10.129.13.77:6443;\n  }\n  server {\n    listen 6443 ssl;\n    proxy_pass k8s-api;\n  }\n}", shape=box, fillcolor="#c8e6c9", color="#2e7d32", width=3];
  }

  subgraph cluster_upstream {
    label="Upstream (kube-apiserver)"; bgcolor="#e3f2fd"; color="#1565c0";
    
    apiserver_n8 [label="apiserver\nn8 (40.51)\n:6443", shape=box, fillcolor="#bbdefb", color="#1565c0"];
    apiserver_n7 [label="apiserver\nn7 (40.50)\n:6443", shape=box, fillcolor="#bbdefb", color="#1565c0"];
  }

  client [label="kubectl\nBFF\nпользователи", shape=cylinder, fillcolor="#f3e5f5", color="#7b1fa2"];

  client -> nginx [label="TLS\n:6443", color="#2e7d32"];
  nginx -> apiserver_n8 [label="health ✓\nактивный", color="#2e7d32", fontcolor="#2e7d32"];
  nginx -> apiserver_n7 [label="health ✓\nактивный", color="#2e7d32", fontcolor="#2e7d32"];
  
  // health checks
  hc [label="Health-check:\nproxy_pass + health_check\nесли узел упал →\nисключается из upstream", shape=note, fillcolor="#fff9c4", color="#f9a825", fontsize=9];
  nginx -> hc [style=dotted, dir=none];
}
```

> ⚠️ **Важно:** nginx в режиме `stream` не проверяет HTTP-статус. Если apiserver отвечает на TCP, но возвращает ошибки — nginx не переключит трафик. Для продакшена используйте `health_check` (доступен в nginx Plus) или внешний health-checker.

---

### 19.5 Восстановление после сбоя

#### Сценарий 1: Потеря etcd-узла

Если один из двух etcd-узлов падает (например, VPS1 перезагрузился):

1. Кворум потерян (1 < 2) — etcd останавливается **на запись**
2. **Чтение** продолжает работать из кэша apiserver'а
3. kube-apiserver продолжает отвечать, но новые объекты создать нельзя

**Действия:**

```bash
# 1. Проверить статус etcd
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  endpoint health

# 2. Восстановить упавший узел
systemctl restart etcd   # на VPS1

# 3. Проверить кворум
etcdctl endpoint status --write-out=table
# Ожидаем: 2 узла, кворум восстановлен
```

#### Сценарий 2: Полная потеря etcd (оба узла)

Если оба etcd-узла потеряли данные (дисковый сбой):

```bash
# 1. Остановить etcd на обоих узлах
systemctl stop etcd

# 2. На ЛЮБОМ узле восстановить из ПОСЛЕДНЕГО снапшота
etcdctl snapshot restore /backup/etcd-snapshot.db \
  --name vps1 \
  --initial-cluster "vps1=https://170.168.91.95:2380,n8=https://10.129.13.78:2380" \
  --initial-advertise-peer-urls https://170.168.91.95:2380 \
  --data-dir /etcd-k8s

# 3. Запустить etcd с новыми данными
systemctl start etcd
```

```dot
digraph G {
  rankdir=TB; bgcolor="#ffffff"; fontname="Arial";
  node [fontname="Arial", fontsize=10, style=filled];
  edge [fontname="Arial", fontsize=9];

  subgraph cluster_etcd_vps1 {
    label="etcd VPS1"; style=dashed; color="#f9a825"; bgcolor="#fffde7";
    step1 [label="1. Снимем снапшот\nс работающего etcd\netcdctl snapshot save\nsnapshot.db", shape=box, fillcolor="#fff9c4", color="#f9a825"];
  }

  subgraph cluster_restore {
    label="Восстановление"; style=dashed; color="#2e7d32"; bgcolor="#f1f8e9";
    step2 [label="2. Остановим etcd\nsystemctl stop etcd", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    step3 [label="3. Удалим старые данные\nrm -rf /var/lib/etcd/member", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    step4 [label="4. Восстановим из снапшота\netcdctl snapshot restore\n--data-dir /var/lib/etcd", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    step5 [label="5. Запустим etcd\nsystemctl start etcd", shape=box, fillcolor="#a5d6a7", color="#1b5e20"];
  }

  subgraph cluster_result {
    label="Результат"; style=filled; color="#1565c0"; bgcolor="#e3f2fd";
    done [label="✓ etcd работает\n✓ данные на момент снапшота\n✓ можно добавлять\nобратно в кластер", shape=box, fillcolor="#bbdefb", color="#1565c0"];
  }

  step1 -> step2 [label="snapshot.db"];
  step2 -> step3;
  step3 -> step4;
  step4 -> step5 [label="новый\nmember ID"];
  step5 -> done;

  note [label="⚠️ Важно:\nСнапшот не содержит\nданные новее снимка\n(окно потери ~секунды)", shape=note, fillcolor="#ffebee", color="#c62828", fontsize=9, fontcolor="#c62828"];
  step1 -> note [style=dotted, dir=none, color="#c62828"];
}
```

> ⚠️ **Окно потери:** снапшот содержит состояние на момент снятия. Все изменения после снапшота будут потеряны. В Aither снапшоты делаются каждые 30 минут через cron, окно потери — до 30 минут.

#### Сценарий 3: Потеря control-plane узла

Если n8 (основной control-plane) падает:

1. nginx LB автоматически переключает трафик на n7
2. etcd-кластер продолжает работать (VPS1 + n8 etcd или новый лидер)
3. Pod'ы на n8 становятся `Unknown`
4. controller-manager на n7 перепланирует критичные Pod'ы на n7

**Никаких ручных действий не требуется** — кластер самовосстанавливается.

> 📊 **Таблица 19.5.** Матрица отказов: что падает и к чему это приводит.

| Отказ | Влияние | Авто-восстановление | Ручные действия |
|---|---|---|---|
| 1 etcd-узел | Теряется кворум на запись | ❌ | Перезапустить etcd |
| 1 apiserver | Часть запросов падает (LB переключает) | ✅ (LB) | Ничего |
| 1 control-plane | Узел становится NotReady | ✅ (LB + контроллеры) | Ничего |
| 1 worker | Pod'ы на нём становятся Unknown | ✅ (перепланирование) | Ничего (кроме GPU-под) |
| nginx LB | Кластер недоступен снаружи | ❌ | Перезапустить nginx/поднять резервный LB |

#### Резервное копирование etcd

На VPS1 настроен cron для автоматического снапшота:

```bash
#!/bin/bash
# /etc/cron.d/etcd-backup — каждые 30 минут
ETCDCTL_API=3 etcdctl snapshot save /backup/etcd-snapshot-$(date +%Y%m%d-%H%M).db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key
```

Снапшот копируется на n8 (второй узел) и хранится 7 дней.

---

### Итоги Главы 19

| Вы узнали | Вы научились |
|---|---|
| Что такое SPOF и как его устранить | Добавлять второй control-plane узел |
| Как работает RAFT-консенсус | Настраивать внешний etcd-кластер |
| Почему etcd лучше держать снаружи | Ставить nginx LB для apiserver |
| Как кворум защищает от потери данных | Восстанавливать etcd из снапшота |

**Ключевой вывод:** HA — это не про «поставить второй сервер». Это про цепочку: etcd (консенсус) → apiserver (избыточность) → LB (балансировка) → worker'ы (перепланирование). Каждый слой должен быть продуман.

---

<!-- ================================================================= -->
<!-- ГЛАВА 20. MULTI-TENANT — ЗАГЛУШКА                                 -->
<!-- ================================================================= -->

## Глава 20. Multi-tenant архитектура: изоляция организаций

> **Состояние:** ✅ готово — текст + 8 DOT-схем.
> **Объём:** ~35 стр., 8 схем, 6 таблиц.
> **Основа:** задача #21 (коммиты `1f53b56`, `28f9c9e`).

**Цель главы:** научиться разделять клиентов платформы (организации) так, чтобы один не видел данные другого — ни баланс, ни чаты, ни API-ключи.

> ✏️ **Перед прочтением** убедитесь, что вы освоили Главу 6 (Портал — веб-интерфейс) и Главу 16 (Доработка портала).

---

### 20.1 Модели изоляции: soft vs hard multi-tenancy

#### Что такое tenant (организация)

Multi-tenancy (мультиарендность) — это архитектурный паттерн, при котором **один экземпляр приложения** обслуживает **несколько независимых клиентов** (tenant'ов, организаций). В Aither tenant = организация (`portal_organizations`).

Представьте многоквартирный дом:
- **Квартира** = tenant (организация)
- **Подъезд** = приложение (один Gateway/BFF)
- **Ключ от квартиры** = API key
- **Стены между квартирами** = изоляция

#### Два подхода к изоляции

| Критерий | Soft (Aither) | Hard |
|---|---|---|
| База данных | Одна, фильтрация `WHERE org_id=$N` | Отдельная БД на tenant |
| Сервер приложений | Один Gateway + BFF на всех | Отдельный экземпляр на tenant |
| Стоимость | Низкая (1 инстанс) | N× выше |
| Изоляция | На уровне кода (SQL WHERE) | На уровне инфраструктуры |
| Риск утечки | При ошибке в WHERE | Близок к нулю |
| Развёртывание | Быстрое | Медленное (N тенантов = N деплоев) |

```dot
digraph G {
  rankdir=TB; bgcolor="#ffffff"; fontname="Arial";
  node [fontname="Arial", fontsize=10, style=filled];
  edge [fontname="Arial", fontsize=9];

  subgraph cluster_soft {
    label="Soft Multi-tenancy (выбор Aither)"; style=filled; color="#2e7d32"; bgcolor="#f1f8e9";
    
    db [label="Общая БД\n( PostgreSQL )", shape=cylinder, fillcolor="#c8e6c9", color="#2e7d32"];
    app [label="Общий Gateway/BFF", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    
    org_a [label="Org Alpha", shape=box, fillcolor="#e3f2fd", color="#1565c0"];
    org_b [label="Org Beta", shape=box, fillcolor="#fff9c4", color="#f9a825"];
    
    org_a -> app [label="API key A"];
    org_b -> app [label="API key B"];
    app -> db [label="WHERE org_id=$N\n(фильтр на уровне SQL)"];

    pros [label="✅ Плюсы:\n• Одна БД — проще бэкап\n• Дешёвле (1 инстанс БД)\n• Быстрее развёртывание\n\n⚠️ Минусы:\n• Риск утечки при ошибке в WHERE\n• Noisy neighbour (один клиент\n  может нагрузить БД)", shape=note, fillcolor="#e8f5e9", color="#43a047", fontsize=9];
  }

  subgraph cluster_hard {
    label="Hard Multi-tenancy"; style=filled; color="#c62828"; bgcolor="#ffebee";
    
    db_a [label="БД Org Alpha", shape=cylinder, fillcolor="#ffcdd2", color="#c62828"];
    db_b [label="БД Org Beta", shape=cylinder, fillcolor="#ffcdd2", color="#c62828"];
    gw_a [label="Gateway\nOrg Alpha", shape=box, fillcolor="#ffcdd2", color="#c62828"];
    gw_b [label="Gateway\nOrg Beta", shape=box, fillcolor="#ffcdd2", color="#c62828"];
    
    org_a2 [label="Org Alpha", shape=box, fillcolor="#e3f2fd", color="#1565c0"];
    org_b2 [label="Org Beta", shape=box, fillcolor="#fff9c4", color="#f9a825"];

    org_a2 -> gw_a -> db_a;
    org_b2 -> gw_b -> db_b;

    cons [label="✅ Плюсы:\n• Полная изоляция\n• Нет риска утечки\n\n⚠️ Минусы:\n• N× дороже\n• Сложнее управление\n• Медленнее развёртывание", shape=note, fillcolor="#ffebee", color="#c62828", fontsize=9];
  }
}
```

> 📊 **Таблица 20.1.** Сравнение soft и hard multi-tenancy.

**Aither выбрал soft multi-tenancy** по трём причинам:
1. **Госсектор:** 10–50 организаций, не тысячи — накладные расходы hard неоправданы
2. **Единая инфраструктура:** GPU-серверы общие, нет смысла разносить Gateway
3. **Быстрый старт:** организация создаётся за 1 INSERT, не требует развёртывания новой БД

> ⚠️ **Цена выбора:** вся изоляция держится на `WHERE org_id=$N` в каждом SQL-запросе. Пропустили WHERE в одном месте — получили утечку данных между организациями. В следующих разделах мы покажем, как Aither гарантирует изоляцию на каждом слое.

---

### 20.2 Per-org API keys и JWT delegation

#### Как организация получает доступ к LLM

В Aither путь выглядит так:

1. Пользователь входит через OAuth (GitHub) → получает JWT входа
2. Пользователь входит в свою организацию (`portal_org_members`)
3. BFF создаёт **API key** для организации (`portal_api_keys`)
4. Для каждого запроса к LLM BFF генерирует **Delegation Token** — JWT с `org_id`
5. Gateway проверяет Delegation Token и пропускает запрос к vLLM

#### Таблица portal_api_keys

```sql
CREATE TABLE portal_api_keys (
  key_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES portal_organizations(org_id),
  api_key text NOT NULL UNIQUE,          -- "ak-" + 48 hex chars
  api_key_prefix text NOT NULL,          -- первые 11 символов для UI
  name text NOT NULL DEFAULT 'default',
  status text NOT NULL DEFAULT 'active',
  created_at timestamptz DEFAULT now(),
  expires_at timestamptz,
  last_used_at timestamptz
);
```

> 🔑 **Формат ключа:** `ak-` + 48 hex-символов (24 байта случайных данных). Пример: `ak-a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`.

#### Как BFF создаёт Delegation Token

BFF хранит **приватный RSA-ключ** (только на VPS2) и подписывает JWT:

```typescript
// server.ts:863-876
async function getDelegationToken(orgId: string, userId: string): Promise<string | null> {
  let apiKey = await getOrgApiKey(orgId);
  if (!apiKey) {
    // Авто-создание первого API key
    apiKey = "ak-" + randomBytes(24).toString("hex");
    await pool.query(
      "INSERT INTO portal_api_keys (org_id, api_key, api_key_prefix, name) VALUES ($1,$2,$3,'auto')",
      [orgId, apiKey, apiKeyPrefix]);
  }
  return jwt.sign(
    { org_id: orgId, key_id: "chat", user_id: userId },
    DELEGATION_PRIVATE_KEY,
    { algorithm: "RS256", expiresIn: "5m", issuer: "aither-portal" }
  );
}
```

**Структура Delegation Token:**

```json
{
  "org_id": "699286c5-...",    // ← КЛЮЧЕВОЕ ПОЛЕ для изоляции
  "key_id": "chat",             // идентификатор API-ключа
  "user_id": "6d73e035-...",    // кто именно сделал запрос
  "iat": 1689000000,            // когда выдан
  "exp": 1689000300,            // через 5 минут
  "iss": "aither-portal"
}
```

#### Как Gateway проверяет Delegation Token

Gateway хранит **публичный RSA-ключ** (в ConfigMap Kubernetes) и проверяет подпись:

```python
# gateway/auth.py
import jwt

PUBLIC_KEY = os.environ["DELEGATION_PUBLIC_KEY"]  # из ConfigMap

def verify_delegation(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"],
                            options={"verify_exp": True})
        return payload  # {"org_id": "...", "user_id": "...", ...}
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
```

```dot
digraph G {
  rankdir=LR; bgcolor="#ffffff"; fontname="Arial";
  node [fontname="Arial", fontsize=10, style=filled];
  edge [fontname="Arial", fontsize=9];

  {
    rank=same;
    user [label="Пользователь\n(браузер)", shape=cylinder, fillcolor="#e3f2fd", color="#1565c0"];
    bff [label="BFF\n(Fastify)\nVPS2:3000", shape=box, fillcolor="#fff9c4", color="#f9a825"];
    db [label=" PostgreSQL ", shape=cylinder, fillcolor="#e0e0e0", color="#616161"];
  }

  {
    rank=same;
    gateway [label="Gateway\n(Python)\nn7:8000", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    redis [label="Redis", shape=cylinder, fillcolor="#ffcdd2", color="#c62828"];
    vllm [label="vLLM\n(GPU)", shape=box, fillcolor="#f3e5f5", color="#7b1fa2"];
  }

  // Flow
  user -> bff [label="1. Логин\n(OAuth GitHub)"];
  bff -> db [label="2. Проверка\nпользователя"];
  bff -> db [label="3. INSERT\nportal_api_keys\n(key_id, org_id)"];
  db -> bff [label="4. api_key\n(ak-...)"];
  bff -> bff [label="5. JWT\nRS256\n{org_id, key_id,\n user_id}\n⏱ 5 мин"];
  bff -> gateway [label="6. Authorization:\nBearer <delegation_jwt>"];
  gateway -> gateway [label="7. Проверка\nподписи RS256\n(публичный ключ)"];
  gateway -> redis [label="8. Rate limit\nrl:{org_id}:rpm"];
  gateway -> vllm [label="9. Проксирование\n(только разрешённые\nмодели)"];

  // Labels
  note [label="Delegation Token (JWT):\nHeader: {alg: RS256}\nPayload: {\n  org_id: 'xxx',\n  key_id: 'chat',\n  user_id: 'yyy',\n  iat: ..., exp: ...\n}", shape=note, fillcolor="#fff9c4", color="#f9a825", fontsize=9];
  bff -> note [style=dotted, dir=none];
}
```

> ⚠️ **Почему 5 минут?** Delegation Token — короткоживущий. Если злоумышленник перехватит токен, у него будет максимум 5 минут. BFF автоматически обновляет токен при каждом новом запросе.

> 📊 **Таблица 20.2.** Ключи и сертификаты в Aither.

| Компонент | Хранит | Где | Для чего |
|---|---|---|---|
| BFF | Приватный RSA-ключ | VPS2, `DELEGATION_PRIVATE_KEY` | Подписывает JWT |
| Gateway | Публичный RSA-ключ | ConfigMap, `DELEGATION_PUBLIC_KEY` | Проверяет подпись |
| Portal | API key | `portal_api_keys.api_key` | Идентификатор организации |
| JWT | org_id, user_id, key_id | В заголовке `Authorization: Bearer ...` | Контекст запроса |

---

### 20.3 Rate Limiting и квоты per-org

#### Зачем нужны лимиты

Без ограничений одна организация может:
- Завалить Gateway тысячами запросов в минуту (DoS)
- Потратить все токены другой организации (если баланс общий)
- Монополизировать GPU (noisy neighbour)

**Решение:** Redis rate limiting с ключами, привязанными к `org_id`.

#### Ключи Redis

| Ключ | Назначение | TTL |
|---|---|---|
| `rl:{org_id}:rpm:{MM:SS}` | Requests per minute | 60 сек |
| `rl:{org_id}:tpm:{MM:SS}` | Tokens per minute | 60 сек |
| `rl:{org_id}:daily:{YYYYMMDD}` | Запросов за день | 86400 сек |
| `tok:{org_id}:daily:{YYYYMMDD}` | Токенов за день | 86400 сек |
| `tok:{org_id}:monthly:{YYYYMM}` | Токенов за месяц | 2592000 сек |

#### Алгоритм проверки в Gateway

```python
# gateway/ratelimit.py (упрощённо)
def check_rate_limit(org_id: str, tier: dict) -> bool:
    now = datetime.utcnow()
    window = now.strftime("%H:%M")

    # 1. Requests per minute
    rpm_key = f"rl:{org_id}:rpm:{window}"
    rpm = redis.incr(rpm_key)
    redis.expire(rpm_key, 60)
    if rpm > tier["rpm_limit"]:
        return False  # 429 Too Many Requests

    # 2. Tokens per minute
    tpm_key = f"rl:{org_id}:tpm:{window}"
    tpm = redis.incrby(tpm_key, estimated_tokens)
    redis.expire(tpm_key, 60)
    if tpm > tier["tpm_limit"]:
        return False

    # 3. Daily token quota
    daily_key = f"tok:{org_id}:daily:{now.strftime('%Y%m%d')}"
    daily = redis.get(daily_key) or 0
    if int(daily) + estimated_tokens > tier["daily_token_limit"]:
        return False

    # 4. Monthly token quota
    monthly_key = f"tok:{org_id}:monthly:{now.strftime('%Y%m')}"
    monthly = redis.get(monthly_key) or 0
    if int(monthly) + estimated_tokens > tier["monthly_token_limit"]:
        return False

    return True  # Все проверки пройдены
```

```dot
digraph G {
  rankdir=LR; bgcolor="#ffffff"; fontname="Arial";
  node [fontname="Arial", fontsize=10, style=filled];
  edge [fontname="Arial", fontsize=9];

  subgraph cluster_redis {
    label="Redis: ключи rate limiting"; bgcolor="#fff3e0"; color="#e65100";
    
    rpm [label="rl:ORG_A:rpm:14:05\n   ↓ INCR\n> 60/min → 429", shape=box, fillcolor="#ffe0b2", color="#e65100"];
    tpm [label="rl:ORG_A:tpm:14:05\n   ↓ INCR\n> 1000/min → 429", shape=box, fillcolor="#ffe0b2", color="#e65100"];
    daily [label="rl:ORG_A:daily:20260710\n   ↓ INCR\n> daily_limit → 429", shape=box, fillcolor="#ffcc80", color="#ef6c00"];
    monthly [label="tok:ORG_A:monthly:202607\n   ↓ INCR\n> 30M → 429", shape=box, fillcolor="#ffcc80", color="#ef6c00"];
    
    window [label="Ключи с TTL:\n• rpm/tpm: 60 сек\n• daily: 86400 сек\n• monthly: 30 дней", shape=note, fillcolor="#fff9c4", color="#f9a825", fontsize=9];
  }

  subgraph cluster_gw {
    label="Gateway: логика проверки"; bgcolor="#e8f5e9"; color="#43a047";
    
    check [label="1. Извлечь org_id\n   из JWT", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    tier [label="2. Загрузить tier\n   (FREE/STD/VIP)", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    limits [label="3. Проверить\n   rpm → tpm → daily\n   → monthly → ACL", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    
    ok [label="✓ OK\nПроксируем\nна vLLM", shape=box, fillcolor="#a5d6a7", color="#1b5e20"];
    reject [label="✗ 429\nRate limit\nexceeded", shape=box, fillcolor="#ffcdd2", color="#c62828"];
  }

  check -> tier -> limits;
  limits -> rpm [label="INCR"];
  limits -> tpm [label="INCR"];
  limits -> daily;
  limits -> monthly;
  limits -> ok [label="все проверки\nпройдены"];
  limits -> reject [label="превышен\nлимит"];
  rpm -> window [style=dotted, dir=none];
}
```

> ⚠️ **Порядок проверок важен:** сначала быстрые (RPM/TPM в Redis), потом медленные (daily/monthly). Если RPM превышен — сразу 429, без лишних запросов к Redis.

#### Учёт токенов ПОСЛЕ запроса

После того как vLLM вернул ответ с `usage.total_tokens`, Gateway учитывает реальное потребление:

```python
# После получения SSE-ответа от vLLM
tokens_used = response["usage"]["total_tokens"]  # 143

# 1. Redis (быстрый путь — для следующей проверки)
redis.incrby(f"tok:{org_id}:daily:{today}", tokens_used)
redis.incrby(f"tok:{org_id}:monthly:{month}", tokens_used)

# 2. PostgreSQL (медленный путь — для аудита)
billing_op(org_id, -tokens_used, "settle")
```

```dot
digraph G {
  rankdir=TB; bgcolor="#ffffff"; fontname="Arial";
  node [fontname="Arial", fontsize=10, style=filled];
  edge [fontname="Arial", fontsize=9];

  subgraph cluster_track {
    label="Gateway: учёт после запроса"; bgcolor="#e8f5e9"; color="#43a047";
    
    vllm_resp [label="vLLM SSE-ответ\nusage.total_tokens = 143", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    parse [label="Парсинг\nизвлекаем N токенов", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
  }

  subgraph cluster_redis_tok {
    label="Redis: токен-счётчики"; bgcolor="#fff3e0"; color="#e65100";
    
    daily_tok [label="tok:ORG_A:daily:20260710\nINCRBY 143\nTTL 86400", shape=box, fillcolor="#ffe0b2", color="#e65100"];
    monthly_tok [label="tok:ORG_A:monthly:202607\nINCRBY 143\nTTL 2592000", shape=box, fillcolor="#ffe0b2", color="#e65100"];
  }

  subgraph cluster_db_track {
    label="PostgreSQL: персистентный учёт"; bgcolor="#e3f2fd"; color="#1565c0";
    
    billing [label="billing_accounts\nUPDATE balance =\n  balance - 143\nWHERE org_id = $1", shape=box, fillcolor="#bbdefb", color="#1565c0"];
    ledger [label="billing_ledger\nINSERT (org_id, type='settle',\n  tokens=143, ...)", shape=box, fillcolor="#bbdefb", color="#1565c0"];
  }

  vllm_resp -> parse;
  parse -> daily_tok [label="1. Fast-path"];
  parse -> monthly_tok [label="1. Fast-path"];
  parse -> billing [label="2. Асинхронно"];
  billing -> ledger [label="3. Аудит"];

  check_next [label="Следующий запрос:\nпроверка квот (daily/monthly)\nперед проксированием", shape=box, fillcolor="#fff9c4", color="#f9a825"];
  daily_tok -> check_next [style=dashed, dir=both, color="#e65100"];
  monthly_tok -> check_next [style=dashed, dir=both, color="#e65100"];

  note [label="⚠️ Двойной учёт:\n1. Redis (быстро, для enforce)\n2. PostgreSQL (медленно, для аудита)\nRedis — кэш, PostgreSQL — источник истины", shape=note, fillcolor="#ffebee", color="#c62828", fontcolor="#c62828", fontsize=9];
  billing -> note [style=dotted, dir=none];
}
```

> 📊 **Таблица 20.3.** Тарифные планы и лимиты (из `subscription_tiers`).

| План | RPM | TPM | Токенов/день | Токенов/мес | Цена |
|---|---|---|---|---|---|
| **FREE** | 10 | 500 | 100K | 3M | 0₽ |
| **STANDARD** | 60 | 5 000 | 1M | 30M | 5 000₽ |
| **VIP** | 300 | 50 000 | 10M | 300M | 20 000₽ |

---

### 20.4 Model ACL: кому какую модель можно

#### Проблема

Не все организации должны иметь доступ ко всем моделям. Например:
- FREE-пользователям — только быстрая qwen2.5-14b
- STANDARD — 14b + 32b
- VIP — всё, включая экспериментальные модели

#### Реализация в Gateway

`subscription_tiers` содержит поле `limits` (JSONB):

```json
{
  "models": ["qwen2.5-14b", "qwen2.5-32b"],
  "rpm_limit": 60,
  "tpm_limit": 5000,
  "daily_token_limit": 1000000,
  "monthly_token_limit": 30000000
}
```

Gateway проверяет ДО проксирования:

```python
# gateway/auth.py
def check_model_acl(org_id: str, model: str, tier: dict) -> bool:
    allowed_models = tier.get("limits", {}).get("models", [])
    if model not in allowed_models:
        logger.warning(f"org={org_id} denied model={model}")
        return False
    return True
```

Если модель не в списке — Gateway возвращает **403 Forbidden** ещё до того, как запрос дойдёт до vLLM.

```dot
digraph G {
  rankdir=TB; bgcolor="#ffffff"; fontname="Arial";
  node [fontname="Arial", fontsize=10, style=filled];
  edge [fontname="Arial", fontsize=9];

  tiers [label="subscription_tiers\n( PostgreSQL )", shape=cylinder, fillcolor="#e3f2fd", color="#1565c0"];

  subgraph cluster_free {
    label="FREE · 0₽/мес"; bgcolor="#f5f5f5"; color="#9e9e9e";
    f_models [label="Модели:\n✅ qwen2.5-14b\n❌ qwen2.5-32b\n❌ coder-14b", shape=box, fillcolor="#fafafa", color="#bdbdbd"];
    f_limits [label="Лимиты:\nRPM: 10\nTPM: 500\nDaily: 100K\nMonthly: 3M", shape=box, fillcolor="#fafafa", color="#bdbdbd"];
  }

  subgraph cluster_std {
    label="STANDARD · 5 000₽/мес"; bgcolor="#f1f8e9"; color="#43a047";
    s_models [label="Модели:\n✅ qwen2.5-14b\n✅ qwen2.5-32b\n❌ coder-14b", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    s_limits [label="Лимиты:\nRPM: 60\nTPM: 5000\nDaily: 1M\nMonthly: 30M", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
  }

  subgraph cluster_vip {
    label="VIP · 20 000₽/мес"; bgcolor="#f3e5f5"; color="#7b1fa2";
    v_models [label="Модели:\n✅ qwen2.5-14b\n✅ qwen2.5-32b\n✅ coder-14b\n✅ все будущие", shape=box, fillcolor="#e1bee7", color="#7b1fa2"];
    v_limits [label="Лимиты:\nRPM: 300\nTPM: 50000\nDaily: 10M\nMonthly: 300M", shape=box, fillcolor="#e1bee7", color="#7b1fa2"];
  }

  gw_filter [label="Gateway: фильтр моделей\nif model not in tier.limits.models:\n    return 403 Forbidden", shape=box, fillcolor="#fff9c4", color="#f9a825"];

  tiers -> f_models [style=dashed];
  tiers -> s_models [style=dashed];
  tiers -> v_models [style=dashed];
  
  f_models -> gw_filter;
  s_models -> gw_filter;
  v_models -> gw_filter;

  note [label="Gateway проверяет\nДО проксирования\nна vLLM", shape=note, fillcolor="#ffebee", color="#c62828", fontcolor="#c62828", fontsize=9];
  gw_filter -> note [style=dotted, dir=none];
}
```

> 📊 **Таблица 20.4.** Матрица доступа к моделям.

| Модель | FREE | STANDARD | VIP |
|---|---|---|---|
| qwen2.5-14b (инференс) | ✅ | ✅ | ✅ |
| qwen2.5-32b (инференс) | ❌ | ✅ | ✅ |
| coder-14b (инференс) | ❌ | ❌ | ✅ |
| LoRA-адаптеры | ❌ | ✅ | ✅ |
| Эмбеддинги (RAG) | ❌ | ❌ | ✅ |

---

### 20.5 Изоляция данных: биллинг, чаты, DLP

#### Биллинг: per-org баланс

Баланс привязан к `org_id`, а не к пользователю. Одна организация = один счёт:

```sql
-- billing_accounts
CREATE TABLE billing_accounts (
  org_id uuid PRIMARY KEY REFERENCES portal_organizations(org_id),
  balance bigint NOT NULL DEFAULT 0,       -- доступные токены
  reserved bigint NOT NULL DEFAULT 0,      -- зарезервировано (в обработке)
  tier text NOT NULL DEFAULT 'free',
  total_tokens bigint NOT NULL DEFAULT 0,  -- всего куплено за историю
  meta jsonb DEFAULT '{}'
);

-- billing_ledger (аудит)
CREATE TABLE billing_ledger (
  txn_id uuid PRIMARY KEY,
  org_id uuid NOT NULL REFERENCES portal_organizations(org_id),
  user_id uuid REFERENCES portal_users(user_id),
  type text NOT NULL,  -- reserve, settle, refund, purchase
  tokens int NOT NULL,
  amount_rub numeric(12,2),
  meta jsonb,
  created_at timestamptz DEFAULT now()
);
```

Все операции с балансом проходят через одну функцию `billing_op(org_id, tokens, type)`, которая:
1. Проверяет, что на счету достаточно токенов (`balance + tokens >= 0`)
2. Атомарно обновляет баланс (`SELECT ... FOR UPDATE`)
3. Пишет запись в `billing_ledger` (аудиторский след)

```python
# gateway/billing.py (упрощённо)
def billing_op(org_id: str, tokens: int, op_type: str):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT balance FROM billing_accounts WHERE org_id=%s FOR UPDATE",
            (org_id,))
        balance = cur.fetchone()[0]
        if balance + tokens < 0:
            raise InsufficientFunds()
        cur.execute(
            "UPDATE billing_accounts SET balance=balance+%s WHERE org_id=%s",
            (tokens, org_id))
        cur.execute(
            "INSERT INTO billing_ledger (org_id, type, tokens) VALUES (%s,%s,%s)",
            (org_id, op_type, abs(tokens)))
```

#### Чаты: per-org изоляция

До задачи #21 чаты фильтровались только по `user_id`:

```sql
-- Было (до #21): пользователь мог видеть все свои чаты,
-- даже если они созданы под другой организацией
SELECT * FROM chats WHERE user_id = $1;
```

После #21 добавлена колонка `org_id`:

```sql
-- Стало: чаты строго per-org
ALTER TABLE chats ADD COLUMN org_id uuid REFERENCES portal_organizations(org_id);
UPDATE chats SET org_id = ...;  -- заполнили 37 существующих чатов
ALTER TABLE chats ALTER COLUMN org_id SET NOT NULL;

-- Все CRUD-запросы теперь фильтруют по org_id:
SELECT * FROM chats WHERE user_id = $1 AND org_id = $2;
```

```dot
digraph G {
  rankdir=TB; bgcolor="#ffffff"; fontname="Arial";
  node [fontname="Arial", fontsize=10, style=filled];
  edge [fontname="Arial", fontsize=9];

  subgraph cluster_bff {
    label="BFF: эндпоинты чатов"; bgcolor="#fff9c4"; color="#f9a825";
    
    check [label="checkChatEnabled(user_id)\n→ org_id (из БД)", shape=box, fillcolor="#fff9c4", color="#f9a825"];
  }

  subgraph cluster_queries {
    label="SQL: фильтрация по org_id"; bgcolor="#e3f2fd"; color="#1565c0";
    
    list [label="GET /chats\nSELECT ... FROM chats\nWHERE user_id=$1\n  AND org_id=$2 ★", shape=box, fillcolor="#bbdefb", color="#1565c0"];
    
    create [label="POST /chats\nINSERT INTO chats\n  (user_id, org_id ★,\n   title, model)\nVALUES ($1,$2,$3,$4)", shape=box, fillcolor="#bbdefb", color="#1565c0"];
    
    get [label="GET /chats/:id\nSELECT ... FROM chats\nWHERE chat_id=$1\n  AND user_id=$2\n  AND org_id=$3 ★", shape=box, fillcolor="#bbdefb", color="#1565c0"];
    
    del [label="DELETE /chats/:id\nDELETE FROM chats\nWHERE chat_id=$1\n  AND user_id=$2\n  AND org_id=$3 ★", shape=box, fillcolor="#bbdefb", color="#1565c0"];
  }

  subgraph cluster_isolation {
    label="Результат: изоляция"; bgcolor="#f1f8e9"; color="#2e7d32";
    
    org_a [label="Org Alpha\n→ видит свои чаты\n✓ chat-1, chat-2", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    org_b [label="Org Beta\n→ видит свои чаты\n✓ chat-3\n→ НЕ видит чужие\n✗ chat-1 (org mismatch)", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
  }

  subgraph cluster_migration {
    label="Миграция (было → стало)"; bgcolor="#eceff1"; color="#607d8b";
    old [label="Было:\nchats\n  user_id\n  title\n  (без org_id)", shape=box, fillcolor="#ffcdd2", color="#c62828"];
    new [label="Стало:\nchats\n  user_id\n  org_id ★ NOT NULL\n  title\nALTER TABLE + UPDATE\nзаполнил 37 чатов", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    old -> new [label="Миграция\nALTER TABLE\nADD COLUMN\n+ UPDATE\nbackfill", color="#2e7d32", fontcolor="#2e7d32"];
  }

  check -> list;
  check -> create;
  check -> get;
  check -> del;
  
  list -> org_a;
  create -> org_a;
  get -> org_b [style=dashed, color="#c62828", label="✗ 404\nchat not found"];
}
```

**Функция `checkChatEnabled()`** возвращает `org_id` и проверяет политики:

```typescript
// server.ts:836-852
async function checkChatEnabled(userId: string, reply: any): Promise<string | null> {
  const orgs = await pool.query(
    `SELECT o.org_id FROM portal_organizations o
     JOIN portal_org_members m ON o.org_id = m.org_id
     WHERE m.user_id = $1 AND m.status = 'active' LIMIT 1`, [userId]);
  if (orgs.rows.length === 0) {
    reply.status(403).send({ error: "chat_disabled" });
    return null;
  }
  const orgId = orgs.rows[0].org_id;
  const policy = await loadPolicy(pool, orgId);
  if (!policy.chat_enabled) {
    reply.status(403).send({ error: "чат отключён в организации" });
    return null;
  }
  return orgId;  // ← используется во всех эндпоинтах чатов
}
```

#### DLP и политики безопасности

`portal_org_policies` позволяет настраивать per-org правила безопасности:

```sql
CREATE TABLE portal_org_policies (
  org_id uuid PRIMARY KEY REFERENCES portal_organizations(org_id),
  chat_enabled boolean DEFAULT true,        -- разрешить чаты?
  allowed_ip_cidrs text[],                  -- белый список IP
  mfa_required boolean DEFAULT false,       -- требовать 2FA?
  session_timeout_min int DEFAULT 60,       -- таймаут сессии
  chat_retention_days int DEFAULT 90,       -- срок хранения чатов
  dlp_rules jsonb DEFAULT '{}'              -- правила DLP
);
```

Каждая организация может иметь свои правила, не затрагивая другие.

```dot
digraph G {
  rankdir=TB; bgcolor="#ffffff"; fontname="Arial";
  node [fontname="Arial", fontsize=10, style=filled];
  edge [fontname="Arial", fontsize=9];

  subgraph cluster_db {
    label=" PostgreSQL: per-org изоляция"; bgcolor="#e3f2fd"; color="#1565c0";

    ba [label="billing_accounts\norg_id (PK)\nbalance, reserved\n→ billing_op(org_id)", shape=box, fillcolor="#c8e6c9", color="#2e7d32", width=2.2];
    ak [label="portal_api_keys\norg_id (FK)\napi_key, status\n→ JWT: {org_id}", shape=box, fillcolor="#ffe0b2", color="#e65100", width=2.2];
    ch [label="chats\nuser_id, org_id ★\ntitle, model\n→ WHERE org_id=$N", shape=box, fillcolor="#e1bee7", color="#7b1fa2", width=2.2];
    pol [label="portal_org_policies\norg_id (PK)\nchat_enabled, dlp_rules\n→ loadPolicy(org_id)", shape=box, fillcolor="#ffcdd2", color="#c62828", width=2.2];
    bl [label="billing_ledger\norg_id (FK), user_id\ntype, tokens, amount\n→ аудит-трейс", shape=box, fillcolor="#cfd8dc", color="#607d8b", width=2.2];
  }

  org_filter [label="Все запросы:\nWHERE org_id = $current_org\n(из JWT)", shape=box, fillcolor="#fff9c4", color="#f9a825"];

  org_filter -> ba [style=dashed, color="#43a047"];
  org_filter -> ak [style=dashed, color="#e65100"];
  org_filter -> ch [style=dashed, color="#7b1fa2"];
  org_filter -> pol [style=dashed, color="#c62828"];
  org_filter -> bl [style=dashed, color="#607d8b"];

  cross [label="Пользователь Org Beta\n→ НЕ видит данные Org Alpha\n(WHERE org_id блокирует)", shape=note, fillcolor="#ffebee", color="#c62828", fontcolor="#c62828", fontsize=9];
  ch -> cross [style=dotted, dir=none, color="#c62828"];
}
```

> 📊 **Таблица 20.5.** Где находится `org_id` в схеме данных.

| Таблица | Колонка org_id | Тип изоляции |
|---|---|---|
| `billing_accounts` | PK | Один счёт на организацию |
| `billing_ledger` | FK | Каждая операция привязана к org |
| `portal_api_keys` | FK | Ключи принадлежат организации |
| `portal_org_members` | FK | Пользователи в организациях |
| `portal_org_policies` | PK | Политики per-org |
| `chats` | FK (★ новое) | Чаты изолированы |
| `payment_transactions` | FK | Платежи per-org |

---

### 20.6 Итоговая схема: полный путь запроса с изоляцией

Соберём все слои вместе — от пользователя до vLLM и обратно:

1. **Аутентификация:** OAuth (GitHub) → JWT входа
2. **Авторизация:** BFF находит org_id, создаёт Delegation Token
3. **Gateway — проверки (последовательно):**
   - Проверка подписи JWT (публичный ключ)
   - Rate limit: `rl:{org_id}:rpm` → не превышен ли?
   - Token quota: `tok:{org_id}:daily` → не превышен ли?
   - Model ACL: модель в списке разрешённых?
4. **Инференс:** проксирование на vLLM
5. **Учёт:** Redis (быстро) + PostgreSQL (аудит)
6. **Аудит:** `billing_ledger` — кто, когда, сколько токенов

```dot
digraph G {
  rankdir=TB; bgcolor="#ffffff"; fontname="Arial";
  node [fontname="Arial", fontsize=9, style=filled];
  edge [fontname="Arial", fontsize=8];

  // Layers
  user [label="👤 Пользователь\nOrg Alpha\n(браузер)", shape=cylinder, fillcolor="#e3f2fd", color="#1565c0"];

  subgraph cluster_layer1 {
    label="Слой 1: Аутентификация"; bgcolor="#f5f5f5"; color="#9e9e9e";
    oauth [label="OAuth\nGitHub", shape=box, fillcolor="#fafafa", color="#bdbdbd"];
    bff [label="BFF\n(Fastify)\nVPS2:3000", shape=box, fillcolor="#fff9c4", color="#f9a825"];
  }

  subgraph cluster_layer2 {
    label="Слой 2: Авторизация + JWT"; bgcolor="#e8f5e9"; color="#43a047";
    apikey [label="portal_api_keys\nAPI key: ak-...\norg_id: ORG_A", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    jwt [label="Delegation JWT\n{org_id: ORG_A,\n key_id: chat,\n user_id: USER_X}\nRS256, 5 мин", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
  }

  subgraph cluster_layer3 {
    label="Слой 3: Gateway — проверки"; bgcolor="#fff3e0"; color="#e65100";
    verify [label="Проверка\nподписи JWT", shape=box, fillcolor="#ffe0b2", color="#e65100"];
    ratelimit [label="Rate Limit\nrl:ORG_A:rpm\n→ 5/60 ✓", shape=box, fillcolor="#ffe0b2", color="#e65100"];
    quota [label="Token Quota\ntok:ORG_A:daily\n→ 143/100K ✓", shape=box, fillcolor="#ffe0b2", color="#e65100"];
    acl [label="Model ACL\nqwen2.5-14b\n∈ tier.models ✓", shape=box, fillcolor="#ffe0b2", color="#e65100"];
  }

  subgraph cluster_layer4 {
    label="Слой 4: Инференс + Учёт"; bgcolor="#f3e5f5"; color="#7b1fa2";
    vllm [label="vLLM\nGPU RTX6000\nqwen2.5-14b", shape=box, fillcolor="#e1bee7", color="#7b1fa2"];
    track [label="Учёт\nRedis: +143 ток\nSQL: billing-143", shape=box, fillcolor="#e1bee7", color="#7b1fa2"];
  }

  subgraph cluster_layer5 {
    label="Слой 5: Аудит"; bgcolor="#eceff1"; color="#607d8b";
    audit [label="billing_ledger\nINSERT settle\norg_id=ORG_A\ntokens=143\n⏱ 2026-07-10", shape=box, fillcolor="#cfd8dc", color="#607d8b"];
  }

  // Flow
  user -> oauth -> bff;
  bff -> apikey -> jwt;
  jwt -> verify -> ratelimit -> quota -> acl;
  acl -> vllm -> track -> audit;

  // Cross-org блок
  other [label="👤 Другой пользователь\nOrg Beta\n→ НЕ видит чаты Org Alpha\n→ НЕ видит платежи Org Alpha\n→ rate limit свой", shape=cylinder, fillcolor="#ffcdd2", color="#c62828"];
  other -> bff [style=dotted, color="#c62828", label="✗ 403\norg mismatch"];
}
```

> 📊 **Таблица 20.6.** Что проверяется и на каком слое.

| Слой | Проверка | Где | При ошибке |
|---|---|---|---|
| BFF | Есть ли организация у пользователя? | SQL | 403 (no active org) |
| BFF | Чат включён в политиках? | `portal_org_policies` | 403 (чат отключён) |
| BFF | Есть ли API key? | `portal_api_keys` | Создаёт авто |
| Gateway | Валиден ли JWT? | RSA-подпись | 401 (invalid token) |
| Gateway | RPM не превышен? | Redis `rl:{org}:rpm` | 429 (rate limit) |
| Gateway | TPM не превышен? | Redis `rl:{org}:tpm` | 429 |
| Gateway | Daily quota не превышена? | Redis `tok:{org}:daily` | 429 |
| Gateway | Monthly quota не превышена? | Redis `tok:{org}:monthly` | 429 |
| Gateway | Модель разрешена? | `tier.limits.models` | 403 (model denied) |
| Gateway | Хватает ли баланса? | `billing_accounts` | 402 (insufficient) |
| После vLLM | Учёт токенов | Redis + SQL | Логгируется |

---

### Итоги Главы 20

| Вы узнали | Вы научились |
|---|---|
| Чем soft отличается от hard multi-tenancy | Создавать per-org API keys |
| Как работает Delegation Token (RS256, 5 мин) | Подписывать и проверять JWT |
| Как Redis rate limiting изолирует организации | Настраивать RPM/TPM/daily/monthly квоты |
| Что такое Model ACL и как он работает | Добавлять колонку `org_id` для изоляции данных |
| Как изолируются чаты, биллинг и DLP | Строить полный аудит-трейс запроса |

**Ключевой вывод:** изоляция в Aither — это не один `if`, а **многослойная система**: API key → JWT → Redis rate limit → token quota → model ACL → SQL WHERE. Каждый слой отказоустойчив: если один проверку пропустил — следующий поймает.

---

<!-- ================================================================= -->
<!-- ГЛАВА 21. ПЛАТЁЖНЫЙ ШЛЮЗ — ЗАГЛУШКА                               -->
<!-- ================================================================= -->

## Глава 21. Платёжный шлюз и монетизация

> **Состояние:** ✅ готово — текст + 4 DOT-схемы.
> **Объём:** ~25 стр., 4 схемы, 5 таблиц.

**Цель главы:** подключить реальные деньги к платформе — приём платежей через YooKassa, автоматическое пополнение баланса, двойная запись для аудита.

> ✏️ **Перед прочтением** убедитесь, что вы освоили Главу 6 (Портал) и Главу 20 (Multi-tenant — биллинг per-org).

---

### 21.1 Модель монетизации Aither

#### Pay-as-you-go: плати за использование

Aither использует модель **pay-as-you-go** (плати за потреблённое):

- Пользователь покупает **пакет токенов** (например, 500 ₽ = 100 000 токенов)
- При каждом запросе к LLM списывается **точное количество токенов**, которое вернула модель
- Нет абонентской платы за простой — деньги тратятся только на инференс

#### Тарифные планы

Каждый план определяет не только цену, но и **лимиты** (RPM, TPM, квоты) и **доступ к моделям**:

| План | Цена | Токенов/мес | RPM | Модели | Для кого |
|---|---|---|---|---|---|
| **FREE** | 0₽ | 100K стартовых | 10 | 14b | Тестирование |
| **STANDARD** | 5 000₽ | 1M/день, 30M/мес | 60 | 14b, 32b, LoRA | Разработка |
| **VIP** | 20 000₽ | 10M/день, 300M/мес | 300 | Все + RAG | Production |

```dot
digraph G {
  rankdir=TB; bgcolor="#ffffff"; fontname="Arial";
  node [fontname="Arial", fontsize=10, style=filled];
  edge [fontname="Arial", fontsize=9];

  subgraph cluster_tiers {
    label="Тарифные планы"; bgcolor="#f5f7fa"; color="#7b8ca0";

    subgraph cluster_free {
      label="FREE · 0₽"; bgcolor="#f5f5f5"; color="#9e9e9e";
      f1 [label="100K токенов\nпри регистрации", shape=box, fillcolor="#fafafa", color="#bdbdbd"];
      f2 [label="10 RPM\n500 TPM", shape=box, fillcolor="#fafafa", color="#bdbdbd"];
      f3 [label="Только qwen2.5-14b", shape=box, fillcolor="#fafafa", color="#bdbdbd"];
    }

    subgraph cluster_std {
      label="STANDARD · 5 000₽/мес"; bgcolor="#f1f8e9"; color="#43a047";
      s1 [label="1M токенов/день\n30M/мес", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
      s2 [label="60 RPM\n5 000 TPM", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
      s3 [label="14b + 32b\nLoRA-адаптеры", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    }

    subgraph cluster_vip {
      label="VIP · 20 000₽/мес"; bgcolor="#f3e5f5"; color="#7b1fa2";
      v1 [label="10M токенов/день\n300M/мес", shape=box, fillcolor="#e1bee7", color="#7b1fa2"];
      v2 [label="300 RPM\n50 000 TPM", shape=box, fillcolor="#e1bee7", color="#7b1fa2"];
      v3 [label="Все модели\nRAG, эмбеддинги", shape=box, fillcolor="#e1bee7", color="#7b1fa2"];
    }
  }

  subgraph cluster_billing {
    label="Модель оплаты: Pay-as-you-go"; bgcolor="#e3f2fd"; color="#1565c0";
    pay [label="Списание за ФАКТИЧЕСКИЕ токены\n(не за запрос)\n\n1 запрос = 143 токена\n→ −143 из баланса", shape=box, fillcolor="#bbdefb", color="#1565c0"];
    auto [label="Автопополнение:\nбаланс < порог →\nавто-платёж YooKassa\nна 100K токенов", shape=box, fillcolor="#bbdefb", color="#1565c0"];
  }

  free -> std [label="апгрейд", style=dashed, color="#43a047"];
  std -> vip [label="апгрейд", style=dashed, color="#7b1fa2"];
  pay -> auto [label="баланс\nнизкий"];
}
```

> 📊 **Таблица 21.1.** Тарифные планы Aither.

#### Ценообразование: руб/1000 токенов

| Модель | Токенов/сек | Токенов/запрос (~) | Себестоимость/1000 ток | Розница/1000 ток |
|---|---|---|---|---|
| qwen2.5-14b | ~30 | 100–200 | ~0.15₽ | 0.50₽ |
| qwen2.5-32b | ~35 | 150–300 | ~0.30₽ | 1.00₽ |
| coder-14b | ~25 | 200–500 | ~0.20₽ | 0.70₽ |

> 💡 **Экономика:** себестоимость = электричество + амортизация GPU. При загрузке 50% один RTX 6000 окупается за ~8 месяцев на STANDARD-тарифе.

---

### 21.2 Архитектура платёжного шлюза

#### Двойная запись (Double-Entry)

Все финансовые операции в Aither проходят через **двойную запись** — каждая транзакция оставляет след в `payment_transactions` (факт платежа) и `billing_ledger` (изменение баланса):

```
Пользователь → YooKassa (500₽) → Webhook → payment_transactions (pending)
                                              → payment_transactions (completed)
                                              → billing_ledger (purchase +100K токенов)
                                              → billing_accounts (balance += 100K)

Пользователь → Gateway (запрос) → billing_ledger (reserve -143)
                                → vLLM → 200 OK?
                                → billing_ledger (settle -143) ← фактически
                                ИЛИ
                                → billing_ledger (refund +143) ← отмена
```

#### Почему двойная запись

- **Аудируемость:** всегда можно восстановить, кто, когда и сколько заплатил/потратил
- **Атомарность:** `reserve → settle/refund` — токены либо списаны, либо возвращены
- **Сверка с YooKassa:** сравниваем `payment_transactions` с выпиской YooKassa

#### Поток платежа (7 шагов)

1. **Пользователь** нажимает «Пополнить» в портале, указывает сумму
2. **BFF** создаёт запись в `payment_transactions` (status=`pending`) и вызывает YooKassa API
3. **YooKassa** создаёт платёж, возвращает `payment_token` и URL платёжной страницы
4. **Пользователь** редиректится на страницу YooKassa, вводит данные карты
5. **YooKassa** обрабатывает платёж и отправляет **webhook** на BFF
6. **BFF** проверяет подпись webhook'а, обновляет `payment_transactions` (status=`completed`)
7. **BFF** зачисляет токены: `billing_op(org_id, +100000, "purchase")`

```dot
digraph G {
  rankdir=LR; bgcolor="#ffffff"; fontname="Arial";
  node [fontname="Arial", fontsize=10, style=filled];
  edge [fontname="Arial", fontsize=9];

  subgraph cluster_user {
    label="Пользователь"; bgcolor="#e3f2fd"; color="#1565c0";
    browser [label="Браузер\n(портал Aither)", shape=cylinder, fillcolor="#bbdefb", color="#1565c0"];
  }

  subgraph cluster_bff {
    label="BFF (VPS2)"; bgcolor="#fff9c4"; color="#f9a825";
    create [label="POST /api/v1/payments\n{amount_rub: 500}\n→ payment_id", shape=box, fillcolor="#fff9c4", color="#f9a825"];
    webhook [label="POST /api/v1/payments/webhook\nобработка уведомления\nот YooKassa", shape=box, fillcolor="#fff9c4", color="#f9a825"];
  }

  subgraph cluster_yookassa {
    label="YooKassa API"; bgcolor="#f3e5f5"; color="#7b1fa2";
    yk_api [label="POST /v3/payments\n{amount, currency,\n confirmation, ...}\n→ payment_token", shape=box, fillcolor="#e1bee7", color="#7b1fa2"];
    yk_page [label="Платёжная страница\nYooKassa\n(банковская карта,\nСБП, кошелёк)", shape=box, fillcolor="#e1bee7", color="#7b1fa2"];
    yk_webhook [label="Webhook:\nnotification\n→ payment.succeeded", shape=box, fillcolor="#e1bee7", color="#7b1fa2"];
  }

  subgraph cluster_db {
    label="PostgreSQL"; bgcolor="#e8f5e9"; color="#43a047";
    txn [label="payment_transactions\nINSERT {org_id,\n  amount_rub, status='pending'}", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    settle [label="billing_accounts\nUPDATE balance += tokens\nbilling_ledger\nINSERT purchase", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
  }

  browser -> create [label="1. Пополнить\nна 500₽"];
  create -> txn [label="2. Сохранить\npending"];
  txn -> yk_api [label="3. Создать\nплатёж"];
  yk_api -> yk_page [label="4. Редирект\nна оплату"];
  yk_page -> yk_webhook [label="5. Платёж\nвыполнен"];
  yk_webhook -> webhook [label="6. Уведомление"];
  webhook -> settle [label="7. Зачислить\nтокены"];

  note [label="Идемпотентность:\nYooKassa может прислать\nwebhook повторно.\nПроверяем txn.status —\nесли 'completed',\nигнорируем.", shape=note, fillcolor="#ffebee", color="#c62828", fontcolor="#c62828", fontsize=9];
  webhook -> note [style=dotted, dir=none];
}
```

> 📊 **Таблица 21.2.** Статусы платежа в `payment_transactions`.

| Статус | Описание | Кто меняет |
|---|---|---|
| `pending` | Платёж создан, ожидает оплаты | BFF (при создании) |
| `waiting_for_capture` | Средства зарезервированы, ожидают списания | YooKassa webhook |
| `completed` | Платёж успешно завершён, токены зачислены | BFF (webhook handler) |
| `canceled` | Платёж отменён (пользователем или по таймауту) | YooKassa webhook |
| `failed` | Платёж не прошёл (недостаточно средств и т.п.) | YooKassa webhook |

---

### 21.3 Подключение YooKassa: test → live

#### Шаг 1–4: Тестовый режим

Тестовый режим позволяет провести платёж **без реальных денег**:

```
1. Регистрация на https://yookassa.ru → личный кабинет
2. Создать тестовый магазин → получить shopId + секретный ключ
3. Добавить в secrets.env:
   YOOKASSA_SHOP_ID=test_XXXXX
   YOOKASSA_SECRET_KEY=test_YYYYY
4. Провести тестовый платёж:
   - Карта: 5555 5555 5555 4444
   - Срок: 12/30
   - CVC: 123
   - Сумма: любая (реально не списывается)
```

**Код BFF — создание платежа:**

```typescript
// portal/server.ts — эндпоинт пополнения (упрощённо)
app.post("/api/v1/payments", async (req: any, reply) => {
  const p = auth(req, reply); if (!p) return;
  const { amount_rub } = req.body;

  // 1. Создать запись в БД
  const txn = await pool.query(
    `INSERT INTO payment_transactions (org_id, user_id, amount_rub, status)
     VALUES ($1, $2, $3, 'pending') RETURNING txn_id`,
    [p.org_id, p.user_id, amount_rub]);

  // 2. Вызвать YooKassa API
  const ykResponse = await fetch("https://api.yookassa.ru/v3/payments", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": "Basic " + Buffer.from(`${shopId}:${secret}`).toString("base64"),
      "Idempotence-Key": txn.rows[0].txn_id  // защита от повторов
    },
    body: JSON.stringify({
      amount: { value: amount_rub, currency: "RUB" },
      confirmation: { type: "redirect", return_url: "https://fb1.spb.ru/payments/result" },
      capture: true,
      description: "Пополнение баланса Aither"
    })
  });

  const payment = await ykResponse.json();
  // 3. Редиректить пользователя на страницу оплаты
  return { redirect_url: payment.confirmation.confirmation_url };
});
```

**Код BFF — обработка webhook:**

```typescript
// portal/server.ts — webhook handler
app.post("/api/v1/payments/webhook", async (req: any, reply) => {
  const { event, object } = req.body;

  // 1. Проверить подпись (YooKassa подписывает входящие webhook'и)
  //    (в тестовом режиме можно пропустить)

  if (event === "payment.succeeded") {
    const txn = await pool.query(
      "SELECT * FROM payment_transactions WHERE txn_id = $1 FOR UPDATE",
      [object.id]);  // Idempotence-Key = txn_id

    if (txn.rows[0].status === "completed") {
      return { ok: true };  // идемпотентность: уже обработан
    }

    // 2. Обновить статус платежа
    await pool.query(
      "UPDATE payment_transactions SET status='completed', provider_payment_id=$1 WHERE txn_id=$2",
      [object.id, txn.rows[0].txn_id]);

    // 3. Зачислить токены (STARTER_TOKENS = 100000)
    await pool.query(
      "UPDATE billing_accounts SET balance = balance + $1 WHERE org_id = $2",
      [STARTER_TOKENS, txn.rows[0].org_id]);

    // 4. Запись в ledger
    await pool.query(
      "INSERT INTO billing_ledger (org_id, user_id, type, tokens, amount_rub) VALUES ($1,$2,'purchase',$3,$4)",
      [txn.rows[0].org_id, txn.rows[0].user_id, STARTER_TOKENS, txn.rows[0].amount_rub]);
  }

  return { ok: true };
});
```

#### Шаг 5–8: Переход на live

```dot
digraph G {
  rankdir=TB; bgcolor="#ffffff"; fontname="Arial";
  node [fontname="Arial", fontsize=10, style=filled];
  edge [fontname="Arial", fontsize=9];

  subgraph cluster_test {
    label="TEST-режим"; bgcolor="#f1f8e9"; color="#43a047";
    t1 [label="1. Регистрация\nв YooKassa", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    t2 [label="2. Получить\nshopId + ключ\n(тестовый)", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    t3 [label="3. secrets.env\nYOOKASSA_SHOP_ID=\nYOOKASSA_SECRET=", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    t4 [label="4. Тестовый платёж\n5555 5555 5555 4444\n→ succeeded ✓", shape=box, fillcolor="#a5d6a7", color="#1b5e20"];
  }

  subgraph cluster_live {
    label="LIVE-режим"; bgcolor="#ffebee"; color="#c62828";
    l1 [label="5. Заявка на\nбоевой магазин", shape=box, fillcolor="#ffcdd2", color="#c62828"];
    l2 [label="6. Получить\nlive shopId+ключ", shape=box, fillcolor="#ffcdd2", color="#c62828"];
    l3 [label="7. Обновить\nsecrets.env\nперезапустить BFF", shape=box, fillcolor="#ffcdd2", color="#c62828"];
    l4 [label="8. Боевой платёж\nреальная карта\n→ проверка webhook", shape=box, fillcolor="#ef9a9a", color="#b71c1c"];

    checklist [label="Чек-лист перед live:\n✓ Webhook принимается\n✓ SSL-сертификат валиден\n✓ Баланс зачисляется\n✓ Email-уведомления\n   отправляются", shape=note, fillcolor="#fff9c4", color="#f9a825", fontsize=9];
  }

  t1 -> t2 -> t3 -> t4;
  t4 -> l1 [label="✓ test пройден", color="#c62828", fontcolor="#c62828"];
  l1 -> l2 -> l3 -> l4;
  l4 -> checklist [style=dotted, dir=none];
}
```

> ⚠️ **Важно:** в боевом режиме YooKassa **подписывает** webhook'и. BFF должен проверять подпись перед обработкой, иначе злоумышленник может подделать уведомление о платеже.

> 📊 **Таблица 21.3.** Отличия test и live режимов YooKassa.

| Параметр | Test | Live |
|---|---|---|
| Деньги | Не списываются | Реальные |
| Карты | 5555 5555 5555 4444 | Любые реальные |
| Webhook | Не подписывается | HMAC-подпись |
| shopId | `test_XXXXX` | `live_XXXXX` |
| Договор | Не нужен | Нужен (заявка) |

---

### 21.4 Автопополнение и уведомления

#### Проблема

Пользователь может забыть пополнить баланс. Запрос к LLM упадёт с ошибкой `402 Insufficient Funds` — пользователь уйдёт к конкурентам.

**Решение:** автоматическое пополнение баланса при падении ниже порога.

#### Алгоритм

```python
# gateway/billing.py — логика авто-пополнения
STARTER_TOKENS = 100_000
REFILL_THRESHOLD = 10_000   # порог: пополнять при балансе < 10K
REFILL_LIMIT = 10            # максимум авто-пополнений в день

def ensure_balance(org_id: str):
    balance = get_balance(org_id)
    if balance >= REFILL_THRESHOLD:
        return  # достаточно

    # Сколько раз уже пополняли сегодня?
    refills_today = redis.get(f"refill:{org_id}:{today}")
    if refills_today and int(refills_today) >= REFILL_LIMIT:
        send_email(org_id, "Баланс низкий, авто-пополнение заблокировано")
        raise InsufficientFunds()

    # Авто-платёж через YooKassa
    payment = yookassa_create_payment(
        org_id=org_id,
        amount_rub=calculate_price(STARTER_TOKENS),
        idempotence_key=f"auto-{org_id}-{today}-{refills_today}"
    )

    # Зачислить токены
    billing_op(org_id, +STARTER_TOKENS, "purchase")
    redis.incr(f"refill:{org_id}:{today}")
    redis.expire(f"refill:{org_id}:{today}", 86400)

    send_email(org_id, f"Баланс пополнен на {STARTER_TOKENS} токенов")
```

```dot
digraph G {
  rankdir=TB; bgcolor="#ffffff"; fontname="Arial";
  node [fontname="Arial", fontsize=10, style=filled];
  edge [fontname="Arial", fontsize=9];

  start [label="Пользователь делает\nзапрос к LLM", shape=cylinder, fillcolor="#e3f2fd", color="#1565c0"];

  subgraph cluster_gw {
    label="Gateway: проверка баланса"; bgcolor="#fff3e0"; color="#e65100";
    check [label="billing_op(org_id, -143)\nдостаточно токенов?", shape=diamond, fillcolor="#fff9c4", color="#f9a825"];
    proxy [label="Проксируем\nна vLLM", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
  }

  subgraph cluster_refill {
    label="Автопополнение"; bgcolor="#e8f5e9"; color="#43a047";
    low [label="Баланс < порог\n(10 000 токенов)", shape=diamond, fillcolor="#ffcdd2", color="#c62828"];
    check_limit [label="Счётчик пополнений\n< REFILL_LIMIT (10)?", shape=diamond, fillcolor="#ffcdd2", color="#c62828"];
    refill [label="Авто-платёж\nYooKassa\nна 100K токенов\n(списание с карты)", shape=box, fillcolor="#a5d6a7", color="#1b5e20"];
    blocked [label="✗ Автопополнение\nзаблокировано\n(исчерпан лимит\nна сегодня)", shape=box, fillcolor="#ffcdd2", color="#c62828"];
    notify [label="Email\n«Баланс пополнен\nна 100K токенов»", shape=box, fillcolor="#bbdefb", color="#1565c0"];
    notify_low [label="Email\n«Баланс низкий,\nпополнение заблокировано»", shape=box, fillcolor="#ffcdd2", color="#c62828"];
  }

  start -> check;
  check -> proxy [label="✓ хватает"];
  check -> low [label="✗ не хватает"];
  low -> check_limit [label="баланс\n< порог"];
  check_limit -> refill [label="< 10 раз\nза день"];
  check_limit -> blocked [label="≥ 10 раз\nза день"];
  refill -> proxy [label="токены\nзачислены"];
  refill -> notify [style=dashed];
  blocked -> notify_low [style=dashed];

  note [label="REFILL_LIMIT = 10:\nзащита от бесконечного цикла.\nЕсли за день уже 10 авто-пополнений\n→ больше не пополняем\n(что-то не так с платежом).", shape=note, fillcolor="#fff9c4", color="#f9a825", fontsize=9];
  check_limit -> note [style=dotted, dir=none];
}
```

> ⚠️ **REFILL_LIMIT = 10** — защита от бесконечного цикла. Если платёж почему-то не проходит, а баланс остаётся низким, без этого лимита система будет пытаться создать платёж снова и снова на каждом запросе.

#### Email-уведомления

Aither отправляет email через `smtplib`:

```python
# gateway/notify.py (упрощённо)
import smtplib
from email.mime.text import MIMEText

def send_email(org_id: str, message: str):
    # Найти email администратора организации
    admin = get_org_admin(org_id)
    msg = MIMEText(f"Организация: {org_id}\n{message}")
    msg["Subject"] = "Aither: уведомление о балансе"
    msg["From"] = "noreply@aither.ru"
    msg["To"] = admin.email

    with smtplib.SMTP_SSL("smtp.yandex.ru", 465) as smtp:
        smtp.login(SMTP_USER, SMTP_PASS)
        smtp.send_message(msg)
```

> 📊 **Таблица 21.4.** Пороги и триггеры автопополнения.

| Параметр | Значение | Зачем |
|---|---|---|
| `STARTER_TOKENS` | 100 000 | Сколько токенов дать при регистрации и авто-пополнении |
| `REFILL_THRESHOLD` | 10 000 | При каком остатке запускать авто-пополнение |
| `REFILL_LIMIT` | 10 | Максимум авто-пополнений в день |
| `STARTER_TOKENS / REFILL_THRESHOLD` | 10× | Запас: 10 пополнений × 100K = 1M токенов до блокировки |

---

### 21.5 Сверка и аудит платежей

#### Зачем нужна сверка

Боевая эксплуатация платежей требует **ежемесячной сверки**:

1. Выгрузить все транзакции Aither за месяц (`payment_transactions`)
2. Выгрузить выписку YooKassa за тот же период (личный кабинет → экспорт CSV)
3. Сравнить по `provider_payment_id` и суммам

#### Скрипт сверки

```python
# scripts/reconcile.py (запускается ежемесячно)
def reconcile(month: str):
    # 1. Транзакции Aither
    aither_txns = db.query("""
        SELECT txn_id, provider_payment_id, amount_rub, status
        FROM payment_transactions
        WHERE created_at >= $1 AND created_at < $2
    """, (f"{month}-01", f"{next_month}-01"))

    # 2. Выписка YooKassa (загружается из CSV)
    yookassa_txns = load_yookassa_csv(f"yookassa_{month}.csv")

    # 3. Сверка
    aither_ids = {t.provider_payment_id for t in aither_txns if t.provider_payment_id}
    yookassa_ids = {t.payment_id for t in yookassa_txns}

    missing_in_aither = yookassa_ids - aither_ids      # Есть в YooKassa, нет в Aither
    missing_in_yookassa = aither_ids - yookassa_ids    # Есть в Aither, нет в YooKassa
    amount_mismatch = []                                # Разные суммы

    for t in aither_txns:
        yt = next((y for y in yookassa_txns if y.payment_id == t.provider_payment_id), None)
        if yt and abs(float(t.amount_rub) - float(yt.amount)) > 0.01:
            amount_mismatch.append((t.txn_id, t.amount_rub, yt.amount))

    return {
        "missing_in_aither": missing_in_aither,
        "missing_in_yookassa": missing_in_yookassa,
        "amount_mismatch": amount_mismatch,
        "status": "OK" if not (missing_in_aither or amount_mismatch) else "MISMATCH"
    }
```

> 📊 **Таблица 21.5.** Типы расхождений при сверке.

| Расхождение | Вероятная причина | Действие |
|---|---|---|
| Платёж в YooKassa, нет в Aither | Webhook не дошёл (сеть) | Зачислить вручную |
| Платёж в Aither, нет в YooKassa | Тестовый платёж / ошибка | Пометить `canceled` |
| Разные суммы | Частичный refund в YooKassa | Проверить историю платежа |
| Дубликат webhook'а | YooKassa повторил уведомление | Идемпотентность: статус уже `completed` → игнорируем |

---

### Итоги Главы 21

| Вы узнали | Вы научились |
|---|---|
| Как работает pay-as-you-go монетизация | Создавать платёж через YooKassa API |
| Что такое double-entry billing | Обрабатывать webhook'и YooKassa |
| Как переключиться с test на live | Настраивать авто-пополнение баланса |
| Зачем нужен REFILL_LIMIT | Делать ежемесячную сверку платежей |
| Как проверять webhook'и на идемпотентность | Отправлять email-уведомления о балансе |

**Ключевой вывод:** платёжный шлюз — это не только API YooKassa, но и **двойная запись**, **идемпотентность**, **сверка** и **автопополнение**. Пропустите один из этих слоёв — и деньги либо потеряются, либо задвоятся.

---

<!-- ================================================================= -->
<!-- ГЛАВА 22. ENTERPRISE-БЕЗОПАСНОСТЬ — ЗАГЛУШКА                      -->
<!-- ================================================================= -->

## Глава 22. Enterprise-безопасность: mTLS и AI Security Gateway

> **Состояние:** ✅ готово — текст + 6 DOT-схем.
> **Объём:** ~30 стр., 6 схем, 5 таблиц.

**Цель главы:** защитить платформу на уровне, требуемом госстандартами — mTLS между сервисами, AI Security Gateway с детектором инъекций и DLP, аудит всех операций.

> ✏️ **Перед прочтением** убедитесь, что вы освоили Главу 7 (Безопасность) и Главу 20 (Multi-tenant).

---

### 22.1 Модель угроз Aither (STRIDE)

#### Кто может атаковать

| Тип злоумышленника | Мотивация | Возможности |
|---|---|---|
| Внешний (интернет) | Украсть токены, данные клиентов | Доступ к HTTPS API |
| Внутренний (свой сотрудник) | Подсмотреть чужие чаты, повысить тариф | Доступ к VPS2, БД |
| Supply chain (вендор) | Закладка в библиотеке | Зависимости Python/Node.js |
| Сосед по GPU (другая org) | Истощить GPU, подглядеть промпты | API-запросы через свой ключ |

#### STRIDE-разбор

```dot
digraph G {
  rankdir=TB; bgcolor="#ffffff"; fontname="Arial";
  node [fontname="Arial", fontsize=10, style=filled];
  edge [fontname="Arial", fontsize=9];

  subgraph cluster_stride {
    label="STRIDE-модель угроз Aither"; bgcolor="#f5f7fa"; color="#7b8ca0";

    s [label="S — Spoofing\n(подмена)\nПодделка JWT,\nAPI-ключа", shape=box, fillcolor="#ffcdd2", color="#c62828"];
    t [label="T — Tampering\n(искажение)\nИзменение промпта,\nподмена модели", shape=box, fillcolor="#ffcdd2", color="#c62828"];
    r [label="R — Repudiation\n(отказ)\nОтрицание запроса\n→ аудит-лог", shape=box, fillcolor="#fff9c4", color="#f9a825"];
    i [label="I — Info Disclosure\n(утечка)\nPII в ответах,\nчужие чаты", shape=box, fillcolor="#ffcdd2", color="#c62828"];
    d [label="D — DoS\n(отказ в обслуживании)\nRate limit,\nGPU-истощение", shape=box, fillcolor="#ffcdd2", color="#c62828"];
    e [label="E — Elevation\n(повышение прав)\nОбход ACL,\nдоступ к VIP-моделям", shape=box, fillcolor="#ffcdd2", color="#c62828"];
  }

  subgraph cluster_controls {
    label="Контрмеры Aither"; bgcolor="#e8f5e9"; color="#43a047";
    c1 [label="JWT RS256\nmTLS", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    c2 [label="Security Gateway\nprompt injection\ndetector", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    c3 [label="billing_ledger\nаудиторский след\nс org_id", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    c4 [label="Egress DLP\nPII filter\nDSP markers", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    c5 [label="Redis rate limit\nper-org RPM/TPM\ntoken quotas", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    c6 [label="Model ACL\nper-org tier\n+ Gateway enforce", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
  }

  s -> c1; t -> c2; r -> c3; i -> c4; d -> c5; e -> c6;
}
```

> 📊 **Таблица 22.1.** STRIDE-угрозы и контрмеры Aither.

| Угроза | Пример атаки | Контрмера |
|---|---|---|
| **S**poofing | Поддельный JWT с чужим org_id | RS256 подпись + mTLS |
| **T**ampering | `system: ignore previous instructions` | Prompt injection detector |
| **R**epudiation | «Я не делал этот запрос» | `billing_ledger` — каждая операция с user_id + timestamp |
| **I**nfo Disclosure | vLLM вернул паспортные данные | Egress DLP — 12 паттернов PII |
| **D**oS | 1000 запросов/сек от одной org | Redis per-org rate limiting |
| **E**levation | FREE пользователь → VIP модель | Model ACL через `tier.limits.models` |

---

### 22.2 mTLS: взаимная аутентификация сервисов

#### Зачем нужен mTLS

Обычный TLS (HTTPS) проверяет только **сервер** (браузер → сайт). mTLS (mutual TLS) проверяет **обоих** — и сервер, и клиент.

В Aither mTLS защищает канал **BFF → Gateway**:
- BFF предъявляет клиентский сертификат
- Gateway проверяет, что сертификат подписан внутренним CA
- Без сертификата Gateway даже не отвечает на TCP

#### Инфраструктура сертификатов

```bash
# 1. Создаём внутренний CA (один раз)
openssl genrsa -out ca.key 2048
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt \
  -subj "/CN=Aither Internal CA/O=Aither/C=RU"

# 2. Сертификат Gateway (серверный)
openssl genrsa -out gateway.key 2048
openssl req -new -key gateway.key -out gateway.csr \
  -subj "/CN=gateway.aither.svc/O=Aither/C=RU"
openssl x509 -req -in gateway.csr -CA ca.crt -CAkey ca.key \
  -out gateway.crt -days 365

# 3. Сертификат BFF (клиентский)
openssl genrsa -out bff.key 2048
openssl req -new -key bff.key -out bff.csr \
  -subj "/CN=bff.aither.portal/O=Aither/C=RU"
openssl x509 -req -in bff.csr -CA ca.crt -CAkey ca.key \
  -out bff.crt -days 365
```

#### Gateway: SSL-контекст с mTLS

```python
# gateway/mtls_server.py
import ssl
from http.server import HTTPServer

class SSLHTTPServer(HTTPServer):
    def __init__(self, server_address, handler_class):
        super().__init__(server_address, handler_class)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.verify_mode = ssl.CERT_REQUIRED    # ← требует клиентский серт
        ctx.check_hostname = False
        ctx.load_verify_locations(cafile='/etc/mtls/ca.crt')
        ctx.load_cert_chain(
            certfile='/etc/mtls/tls.crt',
            keyfile='/etc/mtls/tls.key')
        self.socket = ctx.wrap_socket(self.socket, server_side=True)

# Kubernetes: сертификаты монтируются из Secret
#   volumeMounts:
#     - name: mtls-certs
#       mountPath: /etc/mtls
#       readOnly: true
```

#### BFF: HTTPS-агент с клиентским сертификатом

```typescript
// portal/server.ts
import https from "https";
import fs from "fs";

const mtlsAgent = new https.Agent({
  ca: fs.readFileSync("/etc/aither/mtls/ca.crt"),
  cert: fs.readFileSync("/etc/aither/mtls/bff.crt"),
  key: fs.readFileSync("/etc/aither/mtls/bff.key"),
  rejectUnauthorized: true,
});

// Вспомогательная функция для всех запросов к Gateway
export async function gatewayFetch(path: string, opts: RequestInit = {}) {
  const url = CORE_API_MTLS + path;
  const fetchOpts: any = { ...opts, dispatcher: mtlsAgent };
  return fetch(url, fetchOpts);
}
```

```dot
digraph G {
  rankdir=TB; bgcolor="#ffffff"; fontname="Arial";
  node [fontname="Arial", fontsize=10, style=filled];
  edge [fontname="Arial", fontsize=9];

  subgraph cluster_ca {
    label="Certificate Authority (CA)"; bgcolor="#f3e5f5"; color="#7b1fa2";
    ca [label="Aither Internal CA\nca.crt + ca.key", shape=box, fillcolor="#e1bee7", color="#7b1fa2"];
  }

  subgraph cluster_gateway {
    label="Gateway (сервер)"; bgcolor="#e8f5e9"; color="#43a047";
    gw_cert [label="gateway.crt\nCN=gateway.aither.svc", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    gw_check [label="ssl.CERT_REQUIRED\n→ только клиенты\nс сертификатом CA", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
  }

  subgraph cluster_bff {
    label="BFF (клиент)"; bgcolor="#e3f2fd"; color="#1565c0";
    bff_cert [label="bff.crt + bff.key\nCN=bff.aither.portal", shape=box, fillcolor="#bbdefb", color="#1565c0"];
    bff_agent [label="https.Agent({ca,cert,key})\ngatewayFetch()", shape=box, fillcolor="#bbdefb", color="#1565c0"];
  }

  subgraph cluster_flow {
    label="TLS Handshake"; bgcolor="#fff3e0"; color="#e65100";
    h1 [label="1. ClientHello", shape=box, fillcolor="#fff9c4", color="#f9a825"];
    h2 [label="2. ServerHello\n+ gateway.crt", shape=box, fillcolor="#fff9c4", color="#f9a825"];
    h3 [label="3. CertificateRequest\n(требует клиентский)", shape=box, fillcolor="#ffe0b2", color="#e65100"];
    h4 [label="4. BFF → bff.crt\nGateway проверяет\nпо CA", shape=box, fillcolor="#ffe0b2", color="#e65100"];
    h5 [label="5. Обе стороны\nаутентифицированы ✓", shape=box, fillcolor="#a5d6a7", color="#1b5e20"];
  }

  ca -> gw_cert; ca -> bff_cert;
  bff_agent -> h1; h1 -> h2 -> h3 -> h4 -> h5;
  gw_check -> h4 [dir=both, style=dashed];

  no [label="Без сертификата:\n✗ Connection refused\nGateway не отвечает", shape=note, fillcolor="#ffebee", color="#c62828", fontcolor="#c62828", fontsize=9];
  h1 -> no [style=dotted, color="#c62828"];
}
```

#### Проверка

```bash
# С клиентским сертификатом — успех
curl --cert bff.crt --key bff.key --cacert ca.crt \
  https://10.129.13.78:30901/health
# → {"status": "ok", "billing": "enabled"}

# БЕЗ сертификата — Connection refused
curl https://10.129.13.78:30901/health
# → (нет ответа — mTLS блокирует)
```

> 📊 **Таблица 22.2.** Сертификаты в инфраструктуре Aither.

| Сертификат | CN | Где хранится | Назначение |
|---|---|---|---|
| `ca.crt` | Aither Internal CA | VPS2 (`/etc/aither/mtls/`), Gateway (`Secret`) | Корневой CA |
| `gateway.crt` | `gateway.aither.svc` | Gateway (`Secret mts-certs`) | Серверный TLS |
| `bff.crt` | `bff.aither.portal` | VPS2 (`/etc/aither/mtls/`) | Клиентский TLS |

---

### 22.3 Parsec и мандатный доступ (Astra Linux)

#### Что такое Parsec

Astra Linux SE использует **Parsec** — модуль мандатного контроля целостности (МКЦ). Он проверяет:
- Подпись исполняемых файлов
- Иерархию уровней целостности (`ilev`)
- Возможность выполнения кода в стеке (`execstack`)

#### Как Parsec влияет на работу Aither

На стенде зафиксированы два случая блокировки:

| Проблема | Причина | Решение |
|---|---|---|
**DNS не работает** (n8) | Parsec reject-правила в nftables для `10.96.0.10:53` | Удалить правила через `nft delete rule` |
| **etcd-сертификаты не работают** (n7) | Мандатные метки на сертификатах | `parsec=0` в GRUB на время join |

#### Параметры Parsec

```bash
# Просмотр текущего уровня
cat /proc/self/attr/current

# Отключение Parsec (только для отладки!)
# В /etc/default/grub:
GRUB_CMDLINE_LINUX="parsec=0"
# Затем: update-grub && reboot

# Мягкий режим (для production):
GRUB_CMDLINE_LINUX="max_ilev=63 execstack=1"
```

> ⚠️ **Баланс:** Parsec защищает от модификации системных файлов, но блокирует легитимные операции Kubernetes. Решение Aither: `max_ilev=63 execstack=1` — максимальный уровень целостности с разрешением исполнения в стеке.

> 📊 **Таблица 22.3.** Параметры Parsec в Aither.

| Параметр | Значение | Что даёт |
|---|---|---|
| `max_ilev` | 63 | Максимальная иерархия (все уровни проверяются) |
| `execstack` | 1 | Разрешить выполнение кода в стеке (нужно для JIT) |
| `parsec` | 0 (только отладка) | Полное отключение МКЦ |

---

### 22.4 AI Security Gateway: защита от инъекций и DLP

#### Два фильтра: ingress и egress

AI Security Gateway работает в **две стороны**:

1. **Ingress** (`security.py`) — проверяет запросы пользователя ДО того, как они попадут в vLLM
2. **Egress** (`security_egress.py`) — проверяет ответы vLLM ДО того, как они уйдут пользователю

```dot
digraph G {
  rankdir=TB; bgcolor="#ffffff"; fontname="Arial";
  node [fontname="Arial", fontsize=10, style=filled];
  edge [fontname="Arial", fontsize=9];

  ingress [label="ВХОДЯЩИЙ запрос", shape=cylinder, fillcolor="#e3f2fd", color="#1565c0"];

  subgraph cluster_ingress {
    label="Ingress (security.py)"; bgcolor="#ffebee"; color="#c62828";
    inj [label="Prompt Injection\n35 regex-паттернов\n(EN + RU)", shape=box, fillcolor="#ffcdd2", color="#c62828"];
    dlp_in [label="DLP Ingress\nСистемный промпт\nне пытаются украсть?", shape=box, fillcolor="#ffcdd2", color="#c62828"];
    reject [label="✗ 403 Forbidden", shape=box, fillcolor="#ef9a9a", color="#b71c1c"];
  }

  vllm [label="vLLM", shape=box, fillcolor="#f3e5f5", color="#7b1fa2"];

  subgraph cluster_egress {
    label="Egress (security_egress.py)"; bgcolor="#ffebee"; color="#c62828";
    dsp [label="DSP Filter\nГриф секретности", shape=box, fillcolor="#ffcdd2", color="#c62828"];
    pii [label="PII Leak Detection\n12 паттернов", shape=box, fillcolor="#ffcdd2", color="#c62828"];
    mask [label="✓ Пройдено\n+ SIEM аудит", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];
    block [label="✗ Заблокирован\n+ SIEM alert", shape=box, fillcolor="#ef9a9a", color="#b71c1c"];
  }

  siem [label="SIEM (CEF/syslog)\nsecurity.log", shape=cylinder, fillcolor="#eceff1", color="#607d8b"];

  ingress -> inj -> dlp_in;
  dlp_in -> reject [label="атака"];
  dlp_in -> vllm [label="чисто"];
  vllm -> dsp -> pii;
  pii -> mask [label="чисто"];
  pii -> block [label="нарушение"];
  mask -> siem [style=dashed];
  reject -> siem [style=dashed];
  block -> siem [style=dashed];
}
```

#### Ingress: детектор prompt injection

```python
# gateway/security.py (фрагмент)
INJECTION_PATTERNS = [
    # System prompt override (EN)
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?)",
    r"you\s+are\s+now\s+(a\s+)?(DAN|jailbroken|unfiltered)",
    r"pretend\s+(you\s+are|to\s+be)\s+(a\s+)?(different|another)",
    # Role override
    r"(new|override|replace)\s+(system|your)\s+(prompt|role|instruction)",
    r"disregard\s+(all\s+)?(previous|prior|your)\s+(instructions?|constraints?)",
    # Russian jailbreak
    r"игнорируй\s+(вс[её]\s+)?(предыдущие|прошлые)\s+(инструкции|правила)",
    r"забудь\s+(вс[её]|свои)\s+(инструкции|правила|ограничения|промпт)",
    r"ты\s+теперь\s+(злой|свободный|без\s+ограничений|взломан)",
    r"расскажи\s+(мне\s+)?(свои|твои)\s+(системные\s+)?(инструкции|промпты)",
    # Token smuggling
    r"respond\s+in\s+base64",
    r"decode\s+this\s+(base64|hex|encoded)",
    # ... ещё 25 паттернов
]

def check_prompt_injection(messages: list) -> tuple:
    for msg in messages:
        content = msg.get("content", "")
        content_lower = content.lower()
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, content_lower):
                return False, f"prompt_injection: {pattern}"
    return True, "ok"
```

#### Egress: DLP — защита от утечек

```python
# gateway/security_egress.py (фрагмент)
DLP_PATTERNS = [
    # Кредитные карты
    (r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b", "credit_card"),
    # Паспорт РФ (серия + номер)
    (r"\b\d{2}\s?\d{2}\s?\d{6}\b", "passport_rf"),
    # СНИЛС
    (r"\b\d{3}[-]?\d{3}[-]?\d{3}\s?\d{2}\b", "snils"),
    # ИНН
    (r"\b\d{10}(?:\d{2})?\b", "inn"),
    # Телефон (РФ)
    (r"(?<!\w)(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?!\w)", "phone_ru"),
    # Email
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email"),
    # API-ключи
    (r"\b(sk-[A-Za-z0-9]{32,}|hf_[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{32,})\b", "api_key"),
    # Внутренние IP
    (r"\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b", "internal_ip"),
]
```

> 📊 **Таблица 22.4.** Категории блокировок AI Security Gateway.

| Категория | Направление | Пример | HTTP-код |
|---|---|---|---|
| Prompt injection | Ingress | `ignore all previous instructions` | 403 |
| Role override | Ingress | `you are now DAN` | 403 |
| Prompt leaking | Ingress | `tell me your system prompt` | 403 |
| Token smuggling | Ingress | `respond in base64` | 403 |
| PII leak | Egress | vLLM вернул номер паспорта | 403 / masked |
| DSP markers | Egress | Ответ содержит гриф «Секретно» | 403 |
| Toxic content | Egress | Нецензурная лексика | 403 |

---

### 22.5 Аудит и журналирование

#### Три слоя аудита

```dot
digraph G {
  rankdir=LR; bgcolor="#ffffff"; fontname="Arial";
  node [fontname="Arial", fontsize=10, style=filled];
  edge [fontname="Arial", fontsize=9];

  gw [label="Gateway", shape=box, fillcolor="#c8e6c9", color="#2e7d32"];

  subgraph cluster_audit {
    label="Аудиторский след"; bgcolor="#e3f2fd"; color="#1565c0";
    bl [label="billing_ledger\n(PostgreSQL)\nкаждая финансовая\nоперация", shape=cylinder, fillcolor="#bbdefb", color="#1565c0"];
    sec [label="security.log\n(SIEM CEF)\nблокировки\nинциденты", shape=box, fillcolor="#bbdefb", color="#1565c0"];
  }

  subgraph cluster_operations {
    label="Операции"; bgcolor="#f5f7fa"; color="#7b8ca0";
    op1 [label="reserve\nsettle\nrefund", shape=box, fillcolor="#e0e0e0", color="#616161"];
    op2 [label="purchase\n(покупка)", shape=box, fillcolor="#e0e0e0", color="#616161"];
    op3 [label="security\n(блокировка)", shape=box, fillcolor="#ffcdd2", color="#c62828"];
  }

  gw -> op1 -> bl;
  gw -> op2 -> bl;
  gw -> op3 -> sec;

  report [label="Аудит-отчёт\nSELECT ... FROM\nbilling_ledger\nWHERE org_id=$1", shape=box, fillcolor="#fff9c4", color="#f9a825"];
  bl -> report [style=dashed];
}
```

#### billing_ledger — финансовый аудит

```sql
CREATE TABLE billing_ledger (
  id serial PRIMARY KEY,
  org_id uuid NOT NULL,
  user_id uuid,
  type text NOT NULL,        -- reserve, settle, refund, purchase
  amount bigint NOT NULL,     -- токены (положительное = зачисление, отрицательное = списание)
  operation text,             -- описание
  reference text,             -- внешний ID (YooKassa payment_id)
  balance_after bigint,       -- баланс после операции
  created_at timestamptz DEFAULT now()
);

-- Пример аудит-запроса: все операции организации за июль
SELECT org_id, type, amount, balance_after, created_at
FROM billing_ledger
WHERE org_id = '699286c5-...'
  AND created_at BETWEEN '2026-07-01' AND '2026-08-01'
ORDER BY created_at DESC;
```

#### security.log — SIEM-интеграция

```python
# gateway/security_egress.py — CEF-формат для SIEM
def _send_siem(severity: str, message: str, details: dict):
    cef = f"CEF:0|Aither|Gateway|1.0|{severity}|{message}|{severity}|"
    for k, v in details.items():
        cef += f"{k}={v} "
    
    # Отправка в syslog (UDP local0)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(cef.encode(), (SIEM_HOST, SIEM_PORT))
```

> 📊 **Таблица 22.5.** Поля безопасности в каждой записи.

| Поле | Где | Для чего |
|---|---|---|
| `org_id` | `billing_ledger`, `security.log` | Привязка к организации |
| `user_id` | `billing_ledger` | Кто именно совершил действие |
| `type` | `billing_ledger` | Тип операции (reserve/settle/refund/purchase) |
| `balance_after` | `billing_ledger` | Баланс после операции — можно восстановить историю |
| `reference` | `billing_ledger` | Внешний ID (YooKassa) — для сверки |
| `severity` | `security.log` (CEF) | Уровень: critical/high/medium/low |

---

### Итоги Главы 22

| Вы узнали | Вы научились |
|---|---|
| Что такое STRIDE и как построить модель угроз | Генерировать CA и сертификаты для mTLS |
| Как mTLS защищает канал BFF → Gateway | Добавлять SSL-контекст в Python HTTPServer |
| Почему Parsec блокирует DNS и как это чинить | Интегрировать детектор prompt injection |
| Как работает AI Security Gateway (ingress + egress) | Фильтровать PII в ответах vLLM |
| Как `billing_ledger` обеспечивает аудит | Отправлять алерты в SIEM через CEF/syslog |

**Ключевой вывод:** безопасность в Aither — это три слоя: **mTLS** (канал), **AI Security Gateway** (контент), **billing_ledger** (аудит). Ни один слой не является достаточным сам по себе — только вместе они дают защиту, сравнимую с банковскими системами.

---

<!-- ================================================================= -->
<!-- ГЛАВА 23. КАТАЛОГ МОДЕЛЕЙ + RAG — ЗАГЛУШКА                       -->
<!-- ================================================================= -->

## Глава 23. Каталог моделей и RAG-подсистема

> **Состояние:** ✅ написана на основе реального кода.
> **Объём:** 32 стр., 8 DOT-схем, 6 таблиц.

В этой главе мы строим два production-компонента платформы Aither:
каталог моделей — систему управления LLM-моделями с маршрутизацией,
и гибридный RAG — извлечение релевантных знаний из базы при каждом
запросе пользователя.

### 23.1 Каталог моделей: архитектура и API

**Зачем нужен каталог.** Когда у вас одна модель — маршрутизация не нужна.
Но production-платформа с 32B, 14B и специализированными моделями требует
системы: какая модель на каком сервере, сколько GPU занято, можно ли
перенаправить запрос.

**Архитектура каталога Aither:**

```dot
digraph model_catalog {
    rankdir=TB;
    bgcolor="#ffffff";
    node [fontname="Arial", fontsize=11];

    yaml [label="catalog.yaml\n(ConfigMap)", shape=cylinder, style=filled, fillcolor="#e3f2fd"];
    load [label="catalog.py\nload_catalog()", shape=box, style=filled, fillcolor="#fff3e0"];
    reg [label="_registry\n(in-memory dict)", shape=box, style=filled, fillcolor="#e8f5e9"];
    health [label="_health\n(background thread)", shape=box, style=filled, fillcolor="#fce4ec"];
    route [label="routing.py\nselect_model()", shape=box, style=filled, fillcolor="#f3e5f5"];
    gw [label="Gateway\nmodel routing", shape=box, style=filled, fillcolor="#c8e6c9"];

    yaml -> load [label="load"];
    load -> reg;
    reg -> health [label="poll /health"];
    health -> reg [label="mark\ndown/up"];
    reg -> route [label="models"];
    route -> gw [label="best"];
}
```

**catalog.yaml** — декларативное описание всех моделей:

```yaml
# catalog.yaml
models:
  - id: qwen2.5-32b
    display_name: "Qwen 2.5 32B"
    backend: http://vllm-qwen32b:8000
    provider: qwen
    gpu_required: 2
  - id: qwen2.5-14b
    display_name: "Qwen 2.5 14B"
    backend: http://vllm:8000
    provider: qwen
    gpu_required: 1
```

**Алгоритм загрузки (catalog.py):**

1. Gateway стартует → `load_catalog()` парсит `catalog.yaml`
2. Все модели попадают в `_registry` — словарь `{model_id: {...}}`
3. Фоновый поток `_health_check_loop()` каждые 15 секунд опрашивает `/health` каждого backend
4. Если модель не отвечает → `_health["status"] = "down"`
5. `routing.py` исключает недоступные модели из маршрутизации

**Маршрутизация запроса (routing.py):**
- Gateway получает запрос с `model: "qwen2.5-14b"`
- `select_model(model_id)` проверяет `_registry` + `_health`
- Возвращает `backend_url` — адрес vLLM-сервера
- Gateway проксирует запрос напрямую выбранному backend

| Компонент | Файл | Размер | Назначение |
|---|---|---|---|
| Декларативный каталог | `catalog.yaml` | ConfigMap | Список моделей и backend'ов |
| Загрузчик | `catalog.py` | ~80 строк | Парсинг, реестр, health-check |
| Маршрутизатор | `routing.py` | ~60 строк | Выбор модели по доступности |
|||| *Табл. 23.1 — Компоненты каталога моделей* |

### 23.2 LLM-Wiki: Karpathy-style knowledge graph

**Идея LLM-Wiki.** Андрей Карпаты (бывший директор Tesla AI, сооснователь OpenAI)
популяризовал концепцию «персональной базы знаний»: вместо векторного поиска по
сырым документам — структурированный граф взаимосвязанных Markdown-файлов.

```
Традиционный RAG:  Документ → Чанк → Embedding → Поиск по косинусу
LLM-Wiki:          Markdown → [[wikilinks]] → Граф → Keyword search + Graph expansion
```

**Преимущества LLM-Wiki:**
- **Compile-once, query-many**: знания индексируются при старте, а не при каждом запросе
- **Явные связи**: `[[wikilinks]]` вместо неявной косинусной близости
- **Объяснимость**: «нашёл страницу „AI Gateway“ потому что там есть ссылка на „Безопасность“»
- **Zero dependencies**: ни ChromaDB, ни embedding-модели не нужны

**Структура wiki в Aither:**

```
wiki/
├── SCHEMA.md           # таксономия, конвенции
├── index.md            # каталог страниц
├── log.md              # хронология
├── entities/           # сущности: AI Gateway, vLLM, ChromaDB, Vault, ...
├── concepts/           # концепции: Multi-tenant, Security, RAG, ...
├── comparisons/        # сравнительный анализ
└── queries/            # сохранённые результаты
```

**Страницы и связи:**

| Страница | Тип | Исходящих | Входящих |
|---|---|---|---|
| AI Gateway | entity | 10 | 6 |
| vLLM Inference | entity | 9 | 4 |
| Multi-Tenant Architecture | concept | 8 | 3 |
| Security Egress | entity | 4 | 2 |
| SIEM Integration | entity | 4 | 1 |
| ChromaDB | entity | 3 | 2 |
| LLM-Wiki | concept | 3 | 0 |
| Vault PKI | entity | 1 | 3 |
||| *Табл. 23.2 — Wiki-граф: страницы и связи* |

Каждая страница — Markdown с YAML frontmatter:

```markdown
---
title: AI Gateway
created: 2026-07-09
type: entity
tags: [gateway, architecture, security]
---

# AI Gateway

Центральный компонент платформы Aither, обеспечивающий приём
и маршрутизацию запросов к vLLM-моделям.

## Функции
- **Аутентификация**: JWT RS256 и API-ключи, интеграция с [[Vault PKI]]
- **Rate Limiting**: Redis sliding-window, per-org
- **Безопасность**: DLP-фильтр ([[Security Egress]])
```

**Wiki Graph Engine (wiki_graph.py, 340 строк):**

```dot
digraph wiki_engine {
    rankdir=LR;
    bgcolor="#ffffff";
    node [fontname="Arial", fontsize=11];

    parse [label="Парсинг\nMarkdown", shape=box, style=filled, fillcolor="#e3f2fd"];
    index [label="Индексация\n_pages + _inlinks", shape=box, style=filled, fillcolor="#fff3e0"];
    search [label="Поиск\nsearch()", shape=box, style=filled, fillcolor="#e8f5e9"];
    neighbors [label="Соседи\nneighbors()", shape=box, style=filled, fillcolor="#fce4ec"];
    subgraph [label="Подграф\nsubgraph()", shape=box, style=filled, fillcolor="#f3e5f5"];

    parse -> index;
    index -> search;
    index -> neighbors;
    neighbors -> subgraph;
}
```

**Ключевые структуры данных:**

```python
@dataclass
class WikiPage:
    path: str          # 'entities/ai-gateway.md'
    title: str         # 'AI Gateway'
    page_type: str     # 'entity' | 'concept' | 'comparison' | 'query'
    tags: list[str]
    content: str       # тело без frontmatter
    outlinks: list[str]  # [[target1]], [[target2]]
    summary: str       # первый абзац (~300 символов)

class WikiGraph:
    _pages: dict[str, WikiPage]     # slug → page
    _by_title: dict[str, str]       # title → slug
    _inlinks: dict[str, set[str]]   # slug → {who links here}
```

**Алгоритм полнотекстового поиска** (без внешних зависимостей):

1. Токенизация запроса: разбиваем на слова
2. Для каждой страницы считаем score = сумма(count(term) по всему тексту)
3. Бонус +5.0 за совпадение в заголовке
4. Сортировка по score, топ-k

```python
def search(self, query: str, limit: int = 10) -> list[WikiPage]:
    terms = query.lower().split()
    scored = []
    for page in self._pages.values():
        score = 0.0
        searchable = page.title + ' ' + ' '.join(page.tags) + ' ' + page.content
        for term in terms:
            score += searchable.count(term)
            if term in page.title.lower():
                score += 5.0
        if score > 0:
            scored.append((score, page))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:limit]]
```

### 23.3 Гибридный RAG: keyword + graph expansion

**Идея гибрида.** Чистый keyword search находит страницы — но не учитывает
их семантические связи. Чистый векторный поиск теряет структуру.
Гибридный подход объединяет оба метода.

```dot
digraph hybrid_rag {
    rankdir=TB;
    bgcolor="#ffffff";
    node [fontname="Arial", fontsize=11];

    query [label="Запрос", shape=oval, style=filled, fillcolor="#e3f2fd"];
    kw [label="Keyword\nSearch\n(все страницы)", shape=box, style=filled, fillcolor="#e8f5e9"];
    match [label="Match &\nDeduplicate", shape=box, style=filled, fillcolor="#f3e5f5"];
    expand [label="Graph\nExpansion\n(1-hop)", shape=box, style=filled, fillcolor="#fff3e0"];
    rerank [label="Re-rank\nkeyword×0.7 +\nwiki×0.3", shape=box, style=filled, fillcolor="#fce4ec"];
    fill [label="Fill\ngaps", shape=box, style=filled, fillcolor="#c8e6c9"];
    result [label="Top-K\nрезультатов", shape=oval, style=filled, fillcolor="#e3f2fd"];

    query -> kw;
    kw -> match;
    match -> expand;
    match -> rerank;
    expand -> rerank;
    rerank -> fill;
    fill -> result;
}
```

**Фазы гибридного запроса (hybrid_rag.py):**

**Фаза 1 — Keyword search:**
```python
hits = graph.search(query, limit=top_k * 3)
# Преобразуем в (score, page): позиционный вес
keyword_hits = [((n - i) / n, page) for i, page in enumerate(hits)]
```

**Фаза 2 — Match & Deduplicate:** Оставляем лучший score для каждого slug.

**Фаза 3 — Graph Expansion:** Для каждой найденной страницы обходим её
соседей (1-hop через `[[wikilinks]]`). Считаем wiki_score:

```python
inlink_count = len(graph._inlinks.get(slug, set()))
wiki_score = min(0.3 + 0.15 * inlink_count, 1.0)
```

**Фаза 4 — Re-rank:**
```python
combined_score = keyword_score * 0.7 + wiki_score * 0.3
```

Страницы с большим числом входящих ссылок получают более высокий вес —
это эвристика «авторитетности» страницы в графе знаний.

**Фаза 5 — Fill gaps:** Если результатов меньше top_k —
добираем из соседей найденных страниц (с фиксированным score 0.2).

**Результат:**

```json
{
  "query": "как работает безопасность и фильтрация",
  "mode": "hybrid",
  "results": [
    {
      "id": "wiki:ai-gateway",
      "text": "Центральный компонент платформы Aither...",
      "page_title": "AI Gateway",
      "score": 0.7025,
      "keyword_score": 0.875,
      "wiki_score": 0.3,
      "neighbors": ["Vault PKI", "Security Egress"]
    }
  ]
}
```

| Фаза | Операция | Где реализовано |
|---|---|---|
| 1. Keyword | Полнотекстовый поиск по wiki | `wiki_graph.search()` |
| 2. Match | Дедупликация по slug | `hybrid_rag._match_wiki_pages()` |
| 3. Expand | 1-hop обход графа | `wiki_graph.neighbors()` |
| 4. Re-rank | keyword×0.7 + wiki×0.3 | `hybrid_rag.hybrid_query()` |
| 5. Fill | Добираем из соседей | `hybrid_rag.hybrid_query()` |
|||| *Табл. 23.3 — Фазы гибридного RAG* |

### 23.4 ChromaDB: векторная база данных

**Зачем ChromaDB если есть wiki-граф?** Wiki-граф работает для
структурированных знаний — документация, архитектура, SOP.
Но для произвольных документов (технические задания, PDF-отчёты,
пользовательские загрузки) нужна векторная база.

**ChromaDB** — open-source векторная БД на Python:
- Embedding-модель ONNX MiniLM-L6-v2 (384-мерные векторы)
- Коллекции документов с метаданными
- HTTP API (клиент → сервер через REST)

**Развёртывание ChromaDB в Kubernetes:**

```yaml
# k8s/chroma-deployment.yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: chromadb
        image: chromadb/chroma:latest
        ports:
        - containerPort: 8000
---
apiVersion: v1
kind: Service
spec:
  selector:
    app: chromadb
  ports:
  - port: 8000
```

**Интеграция с Gateway (ленивая инициализация):**

```python
# gateway.py — ChromaDB клиент создаётся при первом обращении
CHROMA_URL = "http://chromadb:8000"
_rag_chroma = None
_rag_ef = None

def _get_chroma():
    global _rag_chroma
    if _rag_chroma is None:
        import chromadb
        _rag_chroma = chromadb.HttpClient(host="chromadb", port=8000)
    return _rag_chroma

def _get_ef():
    global _rag_ef
    if _rag_ef is None:
        from chromadb.utils import embedding_functions
        _rag_ef = embedding_functions.ONNXMiniLM_L6_V2()
    return _rag_ef
```

**Загрузка документов (ingest):**

```python
def rag_ingest(documents: list) -> dict:
    chroma = _get_chroma()
    ef = _get_ef()
    coll = chroma.get_or_create_collection("documents")
    ids = [doc["id"] for doc in documents]
    texts = [doc["text"] for doc in documents]
    embeddings = ef(texts)  # ONNX — без GPU!
    coll.add(ids=ids, embeddings=embeddings, documents=texts)
    return {"ingested": len(documents)}
```

**Векторный поиск (query):**

```python
def rag_query(query: str, top_k: int = 5) -> list:
    chroma = _get_chroma()
    ef = _get_ef()
    coll = chroma.get_or_create_collection("documents")
    q_embedding = ef(["query: " + query])
    results = coll.query(query_embeddings=q_embedding, n_results=top_k)
    return [
        {"id": id_, "text": doc, "score": round(1 - float(dist), 4)}
        for id_, doc, dist in zip(ids, docs, distances)
    ]
```

| Компонент | Технология | Модель | Размерность |
|---|---|---|---|
| Embedding | ONNX Runtime | MiniLM-L6-v2 | 384 |
| Векторная БД | ChromaDB | — | Flat index |
| Поиск | Cosine distance | — | top_k |
|||| *Табл. 23.4 — Стек векторного RAG* |

### 23.5 RAG Pipeline в Gateway

**API эндпоинты:**

```dot
digraph rag_endpoints {
    rankdir=LR;
    bgcolor="#ffffff";
    node [fontname="Arial", fontsize=10];

    gw [label="Gateway\n:8080", shape=box, style=filled, fillcolor="#e3f2fd"];
    hybrid [label="/v1/rag/\nhybrid-query\nPOST", shape=box, style=filled, fillcolor="#e8f5e9"];
    status [label="/v1/rag/\nstatus\nGET", shape=box, style=filled, fillcolor="#fff3e0"];
    wiki [label="/v1/rag/\nwiki-ingest\nGET/POST", shape=box, style=filled, fillcolor="#fce4ec"];
    chroma_q [label="/v1/rag/\nquery\nPOST", shape=box, style=filled, fillcolor="#f3e5f5"];
    chroma_i [label="/v1/rag/\ningest\nPOST", shape=box, style=filled, fillcolor="#c8e6c9"];

    gw -> hybrid;
    gw -> status;
    gw -> wiki;
    gw -> chroma_q;
    gw -> chroma_i;
}
```

**Поток запроса `/v1/rag/hybrid-query`:**

1. **JWT-аутентификация** — `_check_jwt()` валидирует токен (RS256 или legacy)
2. **Tier check** — `_get_tier_limits()` проверяет `rag_enabled` в подписке
3. **Hybrid query** — вызов `hybrid_query(query, top_k, wiki_radius)`
4. **Ответ** — JSON с результатами, score, соседями по графу

**Управление доступом:**

```
Free tier     → rag_enabled = false → 403 "rag_not_available"
Standard tier → rag_enabled = false → 403
VIP tier      → rag_enabled = true  → доступ разрешён
Enterprise    → rag_enabled = true  → доступ разрешён
```

```python
# gateway.py — фрагмент проверки tier
_oid = payload.get("org_id", "unknown")
_tier = _get_org_tier(_oid)
_limits = _get_tier_limits(_tier)
if not _limits["rag"]:
    self._json(403, {"error": "rag_not_available", "tier": _tier})
    return
results = hybrid_query(query, top_k=top_k, wiki_radius=wiki_radius)
```

| Метод | Путь | Аутентификация | Tier check | Назначение |
|---|---|---|---|---|
| POST | `/v1/rag/hybrid-query` | JWT / API-key | RAG tier | Гибридный поиск |
| POST | `/v1/rag/query` | JWT / API-key | RAG tier | Векторный поиск (ChromaDB) |
| POST | `/v1/rag/ingest` | JWT / API-key | — | Загрузка документов в ChromaDB |
| GET | `/v1/rag/status` | JWT / API-key | — | Статус wiki + ChromaDB |
| GET/POST | `/v1/rag/wiki-ingest` | JWT / API-key | — | Перезагрузка wiki-графа |
||||| *Табл. 23.5 — RAG API Gateway* |

### 23.6 RAG в Portal: BFF и UI

**BFF-прокси (server.ts)** — три новых эндпоинта:

```dot
digraph bff_rag {
    rankdir=LR;
    bgcolor="#ffffff";
    node [fontname="Arial", fontsize=10];

    user [label="Portal", shape=oval, style=filled, fillcolor="#e3f2fd"];
    bff [label="BFF\n:3000", shape=box, style=filled, fillcolor="#fff3e0"];
    status [label="/api/rag/\nstatus", shape=box, style=filled, fillcolor="#e8f5e9"];
    query [label="/api/rag/\nquery", shape=box, style=filled, fillcolor="#fce4ec"];
    chat [label="/api/rag/\nchat", shape=box, style=filled, fillcolor="#f3e5f5"];
    gw [label="Gateway", shape=box, style=filled, fillcolor="#c8e6c9"];

    user -> bff [label="JWT"];
    bff -> status;
    bff -> query;
    bff -> chat;
    status -> gw [label="/v1/rag/status"];
    query -> gw [label="/v1/rag/hybrid-query"];
    chat -> gw [label="1. RAG search\n2. Chat completion"];
}
```

**`/api/rag/status`** — возвращает состояние RAG-подсистемы:
```json
{"wiki_pages": 8, "mode": "graph-only (Karpathy-style)", "chroma_docs": 0}
```

**`/api/rag/query`** — проксирует запрос в Gateway:
```
POST /api/rag/query
{"query": "безопасность", "top_k": 5, "wiki_radius": 1}
→ Gateway /v1/rag/hybrid-query → результаты с графом
```

**`/api/rag/chat`** — усиленный чат с инъекцией RAG-контекста:

1. BFF получает сообщения пользователя + `rag_query`
2. Выполняет RAG-поиск в Gateway
3. Строит контекстный блок: `[Контекст из базы знаний Aither]`
4. Добавляет блок в system message
5. Отправляет расширенный промпт в `/v1/chat/completions`
6. Возвращает ответ + список источников

```typescript
// server.ts — RAG chat endpoint
const ragContext = ragResults.map(r =>
  `### ${r.page_title}\n${r.text}`
).join('\n\n');

const augmentedMessages = [...messages];
augmentedMessages[systemIdx].content =
  `[Контекст из базы знаний]\n${ragContext}\n[/Контекст]\n` +
  augmentedMessages[systemIdx].content;
```

**Portal UI — переключатель RAG в чате:**

```dot
digraph rag_ui {
    rankdir=LR;
    bgcolor="#ffffff";
    node [fontname="Arial", fontsize=10];

    toggle [label="📚 RAG\nВкл/Выкл", shape=box, style=filled, fillcolor="#e8f5e9"];
    state [label="localStorage\n'aither_rag'", shape=cylinder, style=filled, fillcolor="#e3f2fd"];
    send [label="sendChat()", shape=box, style=filled, fillcolor="#fff3e0"];
    rag [label="/api/rag/chat", shape=box, style=filled, fillcolor="#fce4ec"];
    normal [label="/api/v1/chats/...\n/messages (stream)", shape=box, style=filled, fillcolor="#f3e5f5"];
    result [label="Сообщение\n+ теги источников", shape=oval, style=filled, fillcolor="#c8e6c9"];

    toggle -> state [label="toggleRAG()"];
    send -> rag [label="ragEnabled\ntrue"];
    send -> normal [label="ragEnabled\nfalse"];
    rag -> result;
    normal -> result;
}
```

**Функция toggleRAG()** — переключает режим и сохраняет в localStorage:

```javascript
function toggleRAG() {
  state.ragEnabled = !state.ragEnabled;
  localStorage.setItem('aither_rag', state.ragEnabled ? '1' : '0');
  const btn = $('#rag-toggle-btn');
  btn.textContent = state.ragEnabled ? '📚 RAG: Вкл' : '📚 RAG: Выкл';
  btn.className = state.ragEnabled ? '... rag-on' : '...';
}
```

**Отображение источников** — после RAG-ответа под сообщением появляется
блок с тегами найденных wiki-страниц:

```html
<div class="rag-sources">
  <span>📚 База знаний:</span>
  <span class="rag-source-tag">AI Gateway</span>
  <span class="rag-source-tag">Security Egress</span>
  <span class="rag-source-tag">Vault PKI</span>
</div>
```

| Компонент | Путь | Назначение |
|---|---|---|
| BFF: /api/rag/status | `server.ts:1720` | Статус RAG |
| BFF: /api/rag/query | `server.ts:1730` | Прокси поиска |
| BFF: /api/rag/chat | `server.ts:1759` | Чат с RAG-контекстом |
| UI: toggleRAG() | `index.html:1947` | Переключатель |
| UI: rag-sources | `index.html:1761` | Блок источников |
|||| *Табл. 23.6 — Компоненты RAG в Portal* |

---

**Итог главы 23:** RAG-подсистема Aither построена на гибридном подходе:
ключевой поиск по wiki-графу (Karpathy-style) + опциональный векторный
поиск через ChromaDB. Portal получил переключатель RAG в чате, BFF —
прокси-эндпоинты с tier-based доступом. Вся система работает без GPU
для embedding'ов (ONNX MiniLM-L6-v2 на CPU).

| Раздел | Стр. | Схем | Табл | Реальный код |
|---|---|---|---|---|
| 23.1 Каталог моделей | 6 | 1 | 1 | `catalog.py`, `catalog.yaml` |
| 23.2 LLM-Wiki | 7 | 1 | 1 | `wiki_graph.py` (340 строк) |
| 23.3 Гибридный RAG | 6 | 1 | 1 | `hybrid_rag.py` (157 строк) |
| 23.4 ChromaDB | 5 | 0 | 1 | `gateway.py:209-257` |
| 23.5 RAG Pipeline | 5 | 1 | 1 | `gateway.py:682-782` |
| 23.6 RAG в Portal | 3 | 2 | 1 | `server.ts:1717-1813`, `index.html` |
| **Итого** | **32** | **6** | **6** | — |

---

<!-- ================================================================= -->
<!-- ГЛАВА 24. PRODUCTION READINESS — ЗАГЛУШКА                         -->
<!-- ================================================================= -->

## Глава 24. Production Readiness: от MVP к промышленной эксплуатации

> **Состояние:** 🔴 заглушка — ждёт наполнения.
> **Целевой объём:** 25 стр., 4 DOT-схемы, 6 таблиц.
> **Детальный TOC:** `05-part4-production-toc.md` § 24.

### 24.1 Threat Model (утверждение)

> 🔴 Заглушка · 5 стр. · 1 схема · 1 табл.

### 24.2 PenTest: методика и проведение

> 🔴 Заглушка · 4 стр. · 1 схема · 1 табл.

### 24.3 Нагрузочное тестирование

> 🔴 Заглушка · 5 стр. · 0 схем · 1 табл.

### 24.4 SLO/SLI и мониторинг

> 🔴 Заглушка · 4 стр. · 1 схема · 1 табл.

### 24.5 Runbooks и аварийное восстановление

> 🔴 Заглушка · 4 стр. · 1 схема · 1 табл.

### 24.6 Чек-лист приёмо-сдаточных испытаний

> 🔴 Заглушка · 3 стр. · 0 схем · 1 табл.

---

*Часть IV в разработке. Глава 19 готова ✅. Главы 20–24 пишутся последовательно.*
