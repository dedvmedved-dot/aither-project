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

![Архитектура до HA — SPOF](diagrams/part4/19-01-spof-before.svg)

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

![RAFT: роли и поток записи](diagrams/part4/19-02-raft-state-machine.svg)

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

![RAFT: выборы лидера](diagrams/part4/19-03-raft-election.svg)

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

![Пошаговое присоединение control-plane](diagrams/part4/19-05-kubeadm-join.svg)

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

![nginx LB для apiserver](diagrams/part4/19-06-nginx-lb.svg)

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

![Восстановление etcd из снапшота](diagrams/part4/19-07-snapshot-restore.svg)

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

![Soft vs Hard multi-tenancy](diagrams/part4/20-01-soft-vs-hard.svg)

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

![API key → JWT flow](diagrams/part4/20-02-api-key-jwt-flow.svg)

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

![Redis rate limiting](diagrams/part4/20-03-rate-limiting.svg)

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

![Token quota tracking](diagrams/part4/20-06-token-quota.svg)

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

![Model ACL — tier × model matrix](diagrams/part4/20-04-model-acl.svg)

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

![Chat isolation — per-org SQL](diagrams/part4/20-08-chat-isolation.svg)

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

![SQL — per-org изоляция всех таблиц](diagrams/part4/20-05-sql-isolation.svg)

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

![End-to-end — полный путь с изоляцией](diagrams/part4/20-07-end-to-end.svg)

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

> **Состояние:** 🔴 заглушка — ждёт наполнения.
> **Целевой объём:** 25 стр., 4 DOT-схемы, 5 таблиц.
> **Детальный TOC:** `05-part4-production-toc.md` § 21.

### 21.1 Модель монетизации Aither

> 🔴 Заглушка · 4 стр. · 1 схема · 1 табл.

### 21.2 Архитектура платёжного шлюза

> 🔴 Заглушка · 6 стр. · 1 схема · 1 табл.

### 21.3 Подключение YooKassa: test → live

> 🔴 Заглушка · 6 стр. · 1 схема · 1 табл.

### 21.4 Автопополнение и уведомления

> 🔴 Заглушка · 5 стр. · 1 схема · 1 табл.

### 21.5 Сверка и аудит платежей

> 🔴 Заглушка · 4 стр. · 0 схем · 1 табл.

---

<!-- ================================================================= -->
<!-- ГЛАВА 22. ENTERPRISE-БЕЗОПАСНОСТЬ — ЗАГЛУШКА                      -->
<!-- ================================================================= -->

## Глава 22. Enterprise-безопасность: mTLS и AI Security Gateway

> **Состояние:** 🔴 заглушка — ждёт наполнения.
> **Целевой объём:** 30 стр., 6 DOT-схем, 5 таблиц.
> **Детальный TOC:** `05-part4-production-toc.md` § 22.

### 22.1 Модель угроз Aither (STRIDE)

> 🔴 Заглушка · 5 стр. · 1 схема · 1 табл.

### 22.2 mTLS: взаимная аутентификация сервисов

> 🔴 Заглушка · 8 стр. · 2 схемы · 1 табл.

### 22.3 Parsec и мандатный доступ (Astra Linux)

> 🔴 Заглушка · 5 стр. · 1 схема · 1 табл.

### 22.4 AI Security Gateway: защита от инъекций и DLP

> 🔴 Заглушка · 7 стр. · 1 схема · 1 табл.

### 22.5 Аудит и журналирование

> 🔴 Заглушка · 5 стр. · 1 схема · 1 табл.

---

<!-- ================================================================= -->
<!-- ГЛАВА 23. КАТАЛОГ МОДЕЛЕЙ + RAG — ЗАГЛУШКА                       -->
<!-- ================================================================= -->

## Глава 23. Каталог моделей и RAG-подсистема

> **Состояние:** 🔴 заглушка — ждёт наполнения.
> **Целевой объём:** 35 стр., 8 DOT-схем, 6 таблиц.
> **Детальный TOC:** `05-part4-production-toc.md` § 23.

### 23.1 Каталог моделей: архитектура и API

> 🔴 Заглушка · 6 стр. · 2 схемы · 1 табл.

### 23.2 Hot-reload моделей в vLLM

> 🔴 Заглушка · 6 стр. · 1 схема · 1 табл.

### 23.3 Теория RAG: Retrieval-Augmented Generation

> 🔴 Заглушка · 6 стр. · 1 схема · 1 табл.

### 23.4 ChromaDB: векторная база данных

> 🔴 Заглушка · 7 стр. · 2 схемы · 1 табл.

### 23.5 RAG Pipeline в Gateway

> 🔴 Заглушка · 5 стр. · 1 схема · 1 табл.

### 23.6 Сценарии использования

> 🔴 Заглушка · 5 стр. · 1 схема · 1 табл.

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
