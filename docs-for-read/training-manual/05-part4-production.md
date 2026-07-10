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
- **Глава 23.** Каталог моделей и RAG-подсистема ✅
- **Глава 24.** Production Readiness: от MVP к промышленной эксплуатации ✅

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

![19.1 Зачем нужна отказоустойчивость](diagrams/05-part4-production-01.jpg)

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

![19.2 Теория RAFT и внешний etcd](diagrams/05-part4-production-02.jpg)

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

![19.2 Теория RAFT и внешний etcd](diagrams/05-part4-production-03.jpg)

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

![19.3 Multi-master Kubernetes: пошаговое развёртывание](diagrams/05-part4-production-04.jpg)

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

![19.4 Load Balancer для apiserver](diagrams/05-part4-production-05.jpg)

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

![19.5 Восстановление после сбоя](diagrams/05-part4-production-06.jpg)

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

![20.1 Модели изоляции: soft vs hard multi-tenancy](diagrams/05-part4-production-07.jpg)

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

![20.2 Per-org API keys и JWT delegation](diagrams/05-part4-production-08.jpg)

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

![20.3 Rate Limiting и квоты per-org](diagrams/05-part4-production-09.jpg)

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

![20.3 Rate Limiting и квоты per-org](diagrams/05-part4-production-10.jpg)

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

![20.4 Model ACL: кому какую модель можно](diagrams/05-part4-production-11.jpg)

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

![20.5 Изоляция данных: биллинг, чаты, DLP](diagrams/05-part4-production-12.jpg)

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

![20.5 Изоляция данных: биллинг, чаты, DLP](diagrams/05-part4-production-13.jpg)

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

![20.6 Итоговая схема: полный путь запроса с изоляцией](diagrams/05-part4-production-14.jpg)

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

![21.1 Модель монетизации Aither](diagrams/05-part4-production-15.jpg)

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

![21.2 Архитектура платёжного шлюза](diagrams/05-part4-production-16.jpg)

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

![21.3 Подключение YooKassa: test → live](diagrams/05-part4-production-17.jpg)

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

![21.4 Автопополнение и уведомления](diagrams/05-part4-production-18.jpg)

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

![22.1 Модель угроз Aither (STRIDE)](diagrams/05-part4-production-19.jpg)

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

![22.2 mTLS: взаимная аутентификация сервисов](diagrams/05-part4-production-20.jpg)

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

![22.4 AI Security Gateway: защита от инъекций и DLP](diagrams/05-part4-production-21.jpg)

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

![22.5 Аудит и журналирование](diagrams/05-part4-production-22.jpg)

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

![23.1 Каталог моделей: архитектура и API](diagrams/05-part4-production-23.jpg)

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

![Функции]([Схема — ошибка рендеринга])

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

### 23.3 Гибридный RAG: Wiki + ChromaDB через прокси

**Идея гибрида.** Wiki-граф даёт keyword-поиск по структурированным знаниям.
ChromaDB — векторный поиск по учебнику (322 чанка). Гибридный RAG объединяет
оба источника: keyword + vector → комбинированный ответ.

Проблема прямой интеграции ChromaDB в Gateway: REST API версий 0.5.x и 0.6.x
не принимает текстовые запросы — требует готовые эмбеддинги. Установка
Python-клиента ChromaDB в Gateway-под требует тяжёлых зависимостей (onnxruntime,
hnswlib) и увеличивает Docker-образ на 2+ ГБ.

**Решение — chroma-proxy:** отдельный под в Kubernetes, использующий
Python-клиент ChromaDB. Прокси принимает текстовые запросы, генерирует
эмбеддинги (ONNX MiniLM-L6-v2) и выполняет векторный поиск. Gateway
вызывает прокси по HTTP без chromadb-зависимостей.

![23.3 Гибридный RAG: Wiki + ChromaDB через прокси](diagrams/05-part4-production-25.jpg)

**Фазы гибридного запроса (hybrid_rag.py, 184 строки):**

**Фаза 1 — Wiki keyword search:**
```python
graph = get_wiki_graph()
wiki_pages = graph.search(query)[:top_k]
# Преобразуем в список: {page_title, slug, relevance=1.0, source="wiki"}
```

**Фаза 2 — ChromaDB vector search (через chroma-proxy):**
```python
result = _proxy_post("query", {"query": query, "top_k": top_k})
# Прокси сам генерирует эмбеддинги (ONNX MiniLM-L6-v2)
# Возвращает: {page_title, preview, relevance, source="chroma"}
```

**Фаза 3 — Combine & Deduplicate:**
```python
seen = set()
combined = []
for r in wiki_results + chroma_results:
    key = r["page_title"][:80]
    if key not in seen:
        seen.add(key)
        combined.append(r)
combined.sort(key=lambda x: x["relevance"], reverse=True)
```

**Фаза 4 — Результат:** топ-k уникальных страниц из обоих источников,
отсортированных по релевантности.

**HTTP API chroma-proxy:**
```
GET  /health          → {"status": "ok"}
GET  /status          → {"collection": "textbook", "documents": 322, ...}
POST /query           → {"query": "...", "top_k": 5} → {"results": [...]}
```

| Фаза | Операция | Источник | Где реализовано |
|---|---|---|---|
| 1. Wiki | Keyword search по графу | wiki_graph.search() | `hybrid_rag.py:hybrid_query()` |
| 2. Chroma | Текст → прокси → векторы → поиск | chroma-proxy:9000 | `hybrid_rag.py:_proxy_post()` |
| 3. Combine | Дедупликация по title[:80] | оба источника | `hybrid_rag.py:hybrid_query()` |
| 4. Sort | По relevance (убывание) | — | `hybrid_rag.py:hybrid_query()` |
||||| *Табл. 23.3 — Фазы гибридного RAG (актуальная архитектура)* |

### 23.4 ChromaDB: развёртывание и chroma-proxy

**ChromaDB 0.5.23** — стабильная версия с работающим REST API.
Версия 0.6.3 имела ошибки (coroutine object в /api/v1/collections,
несовместимость форматов запросов), поэтому был выполнен откат.
Данные (322 чанка учебника) успешно мигрированы.

**Развёртывание ChromaDB в Kubernetes (n7, nodeSelector):**

```yaml
# k8s/chroma-deployment.yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: chromadb
        image: chromadb/chroma:0.5.23
        ports:
        - containerPort: 8000
        env:
        - name: IS_PERSISTENT
          value: "TRUE"
        - name: PERSIST_DIRECTORY
          value: /chroma/chroma
        volumeMounts:
        - name: chroma-data
          mountPath: /chroma/chroma
      volumes:
      - name: chroma-data
        persistentVolumeClaim:
          claimName: chromadb-pvc
---
apiVersion: v1
kind: Service
spec:
  selector:
    app: chromadb
  ports:
  - port: 8000
```

**chroma-proxy — отдельный под с Python-клиентом ChromaDB:**

```yaml
# k8s/chroma-proxy.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chroma-proxy
spec:
  template:
    spec:
      nodeSelector:
        kubernetes.io/hostname: bootsmam-k8s-clnt01-n7-gpu  # PVC RWO
      containers:
      - name: proxy
        image: chromadb/chroma:0.5.23
        command: ["python3", "/scripts/proxy.py", "9000"]
        workingDir: /chroma
        env:
        - name: PYTHONPATH
          value: /chroma
        - name: IS_PERSISTENT
          value: "TRUE"
        - name: PERSIST_DIRECTORY
          value: /chroma/chroma
        volumeMounts:
        - name: chroma-data
          mountPath: /chroma/chroma
        - name: proxy-script
          mountPath: /scripts
      volumes:
      - name: chroma-data
        persistentVolumeClaim:
          claimName: chromadb-pvc
      - name: proxy-script
        configMap:
          name: chroma-proxy-script
---
apiVersion: v1
kind: Service
metadata:
  name: chroma-proxy
spec:
  selector:
    app: chroma-proxy
  ports:
  - port: 9000
```

**Почему PVC RWO и nodeSelector на n7:**
PVC `chromadb-pvc` имеет режим `ReadWriteOnce` — может быть смонтирован
только на одном узле одновременно. ChromaDB и chroma-proxy должны находиться
на одной ноде (n7, где находится PVC).

**Интеграция с Gateway — без chromadb-зависимостей:**

```python
# hybrid_rag.py — Gateway вызывает chroma-proxy по HTTP
CHROMA_PROXY_URL = "http://chroma-proxy.default.svc.cluster.local:9000"

def _proxy_get(path: str) -> dict:
    """GET запрос к chroma-proxy."""
    url = f"{CHROMA_PROXY_URL}/{path}"
    resp = urlopen(Request(url), timeout=10)
    return json.loads(resp.read())

def _proxy_post(path: str, body: dict) -> dict:
    """POST запрос к chroma-proxy."""
    url = f"{CHROMA_PROXY_URL}/{path}"
    data = json.dumps(body).encode()
    req = Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    resp = urlopen(req, timeout=30)
    return json.loads(resp.read())
```

**Gateway не импортирует chromadb.** Все RAG-функции делегированы
в `hybrid_rag.py`, который общается с chroma-proxy через urllib.
Это устраняет зависимость от тяжёлых пакетов (onnxruntime, hnswlib)
и упрощает Docker-образ Gateway.

| Компонент | Технология | Модель | Размерность | Где |
|---|---|---|---|---|
| Embedding | ONNX Runtime | MiniLM-L6-v2 | 384 | chroma-proxy |
| Векторная БД | ChromaDB 0.5.23 | — | Flat index | n7 (PVC) |
| Прокси | Python HTTP | — | :9000 | chroma-proxy pod |
| Поиск | Cosine distance | — | top_k | chroma-proxy |
|||||| *Табл. 23.4 — Стек векторного RAG (актуальная архитектура)* |

### 23.5 RAG Pipeline в Gateway

**Архитектура:** Gateway → hybrid_rag.py → (wiki_graph + chroma-proxy).
Gateway не содержит chromadb-кода — весь RAG делегирован.

**Ключевое изменение (июль 2026):** удалены функции `_get_ef()`, `_get_chroma()`,
`rag_ingest()`, `rag_query()` из `gateway.py`. Вместо них — прямой импорт
из `hybrid_rag`:

```python
# gateway.py — импорт вместо chromadb-зависимостей
from hybrid_rag import chroma_status, hybrid_query, wiki_ingest, wiki_status
```

**API эндпоинты:**

![23.5 RAG Pipeline в Gateway](diagrams/05-part4-production-26.jpg)

**Поток запроса `/v1/rag/hybrid-query`:**

1. **JWT-аутентификация** — `_check_jwt()` валидирует токен
2. **Tier check** — `_get_tier_limits()` проверяет `rag_enabled`
3. **Hybrid query** — `hybrid_query()` выполняет параллельный поиск:
   - Wiki Graph: keyword search → топ-5 страниц
   - chroma-proxy: текст → векторы → поиск по учебнику → топ-5 чанков
4. **Combine & Dedup** — объединение результатов, удаление дублей
5. **Ответ** — JSON с wiki_results, chroma_results, combined

```python
# gateway.py — фрагмент RAG-обработчика
result = hybrid_query(query, top_k=top_k)
self._json(200, result)
```

**Управление доступом:**

```
Free tier     → rag_enabled = false → 403 "rag_not_available"
Standard tier → rag_enabled = false → 403
VIP tier      → rag_enabled = true  → доступ разрешён (322 чанка учебника)
Enterprise    → rag_enabled = true  → доступ разрешён
```

| Метод | Путь | Аутентификация | Tier | Назначение |
|---|---|---|---|---|
| POST | `/v1/rag/hybrid-query` | JWT / API-key | RAG | Гибридный поиск (wiki + ChromaDB) |
| POST | `/v1/rag/query` | JWT / API-key | RAG | Поиск (→ hybrid_query) |
| GET | `/v1/rag/status` | JWT / API-key | — | Статус: wiki_pages + documents |
| GET/POST | `/v1/rag/wiki-ingest` | JWT / API-key | — | Перезагрузка wiki-графа |
|||||| *Табл. 23.5 — RAG API Gateway (актуальная архитектура)* |

### 23.6 RAG в Portal: BFF и UI

**BFF-прокси (server.ts)** — три новых эндпоинта:

![23.6 RAG в Portal: BFF и UI](diagrams/05-part4-production-27.jpg)

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

![23.6 RAG в Portal: BFF и UI](diagrams/05-part4-production-28.jpg)

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
ключевой поиск по wiki-графу (Karpathy-style, 8 страниц) + векторный
поиск через ChromaDB 0.5.23 (322 чанка учебника). Gateway делегирует
RAG в `hybrid_rag.py`, который вызывает chroma-proxy по HTTP — без
chromadb-зависимостей. chroma-proxy работает на n7 (PVC RWO), генерирует
эмбеддинги через ONNX MiniLM-L6-v2. Portal получил переключатель RAG
в чате, админ-панель — вкладку с мониторингом. Вся система работает
без GPU для embedding'ов.

| Раздел | Стр. | Схем | Табл | Реальный код |
|---|---|---|---|---|
| 23.1 Каталог моделей | 6 | 1 | 1 | `catalog.py`, `catalog.yaml` |
| 23.2 LLM-Wiki | 7 | 1 | 1 | `wiki_graph.py` (340 строк) |
| 23.3 Гибридный RAG | 7 | 1 | 1 | `hybrid_rag.py` (184 строки) |
| 23.4 ChromaDB + chroma-proxy | 8 | 0 | 1 | `chroma_proxy.py`, `chroma-proxy.yaml` |
| 23.5 RAG Pipeline | 5 | 1 | 1 | `gateway.py` (импорт hybrid_rag) |
| 23.6 RAG в Portal | 3 | 2 | 1 | `server.ts`, `index.html` |
| **Итого** | **36** | **6** | **6** | — |

---

<!-- ================================================================= -->
<!-- ГЛАВА 24. PRODUCTION READINESS — ЗАГЛУШКА                         -->
<!-- ================================================================= -->

## Глава 24. Production Readiness: от MVP к промышленной эксплуатации

> **Состояние:** ✅ написана на основе реального опыта эксплуатации.
> **Объём:** 28 стр., 4 DOT-схемы, 6 таблиц.
> **Смысл:** не новый код, а превращение MVP в систему, которой можно доверить деньги и данные.

Главы 19–23 построили компоненты. Теперь финальный шаг: доказываем
(себе и заказчику), что система **готова к промышленной эксплуатации**.

### 24.1 Threat Model: модель угроз

**Зачем.** В госсекторе РФ формальная модель угроз — обязательный артефакт
приёмо-сдаточных испытаний. Но и для коммерческой эксплуатации она даёт
структурированное понимание: *что именно мы защищаем и от кого*.

**Методология:** STRIDE (Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege) — отраслевой стандарт Microsoft, принятый в ФСТЭК России.

**Карта угроз платформы Aither:**

![24.1 Threat Model: модель угроз](diagrams/05-part4-production-29.jpg)

**Реестр угроз (STRIDE-матрица):**

| ID | Угроза | STRIDE | Вектор | Текущая защита | Остаточный риск |
|---|---|---|---|---|---|
| T1 | Подделка JWT | Spoofing | BFF → Gateway | RS256 + публичный ключ | Низкий |
| T2 | SQL-инъекция через portal_users | Tampering | BFF → PostgreSQL | Параметризованные запросы (`$1`, `$2`) | Низкий |
| T3 | Prompt injection через chat | Tampering | Пользователь → Gateway | DLP-фильтр (DDL в `security.py`) | Средний |
| T4 | Брутфорс API-ключей | Spoofing | Внешний → Gateway | Rate limit 5 попыток/мин | Низкий |
| T5 | Model inversion (извлечение данных) | Information Disclosure | Gateway → vLLM | Egress-фильтр ДСП/ПДн | Средний |
| T6 | Adversarial prompt (обход цензуры) | Tampering | Пользователь → vLLM | Egress-сканер `security_egress.py` | Средний |
| T7 | Эскалация доступа через BFF | Elevation of Privilege | BFF → PostgreSQL | `checkOrgOwner()` на каждую операцию | Низкий |
| T8 | DoS через исчерпание лимитов | Denial of Service | Множество → Gateway | Redis sliding-window + tier-based | Средний |
| T9 | Утечка данных через etcd API | Information Disclosure | Внешний → etcd | mTLS + сертификаты в Secret | Низкий |
|||||| *Табл. 24.1 — STRIDE-матрица угроз* |

**Вывод:** платформа имеет контрмеры против 9 из 9 идентифицированных угроз.
Остаточный риск «Средний» для T3, T5, T6 и T8 требует дополнительного
мониторинга (алерты на аномальные паттерны промптов) — но не блокирует
production-эксплуатацию.

### 24.2 PenTest: методика и OWASP LLM Top 10

**Зачем PenTest если есть Threat Model.** Модель угроз — теория.
Penetration test — практика: реальные атаки на реальную систему.

**Методика пентеста Aither:**
1. **Reconnaissance** — сбор информации: открытые порты (nmap), версии сервисов
2. **Vulnerability scanning** — автоматическое сканирование (OWASP ZAP)
3. **Exploitation** — ручные атаки на критические векторы
4. **Post-exploitation** — оценка ущерба от успешной атаки
5. **Reporting** — формальный отчёт с CVSS-оценками

**Чек-лист: OWASP Top 10 for LLM Applications (v1.1):**

![24.2 PenTest: методика и OWASP LLM Top 10](diagrams/05-part4-production-30.jpg)

**Результаты пентеста Aither (самооценка):**

| OWASP | Описание | Статус в Aither | Контрмера |
|---|---|---|---|
| LLM01: Prompt Injection | Внедрение команд в промпт | ⚠️ Частично | DLP-фильтр + egress |
| LLM02: Insecure Output | XSS/инъекция в ответе | ✅ Защищено | `security_egress.py` |
| LLM03: Data Poisoning | Отравление обучающих данных | ✅ Не применимо | Мы не файнтюним |
| LLM04: Model DoS | Перегрузка модели запросами | ⚠️ Частично | Rate limiting + tier |
| LLM05: Supply Chain | Уязвимости в зависимостях | ✅ Защищено | Docker-образы закреплены |
| LLM06: Info Disclosure | Утечка ПДн/ДСП в ответе | ⚠️ Частично | Egress-сканер |
| LLM07-09 | Плагины, агенты, доверие | ✅ Не применимо | Архитектура без плагинов |
| LLM10: Model Theft | Кража модели через API | ⚠️ Частично | Rate limit + аудит |
|||| *Табл. 24.2 — OWASP LLM Top 10: статус в Aither* |

**План устранения «частично»:**
- LLM01/LLM06: алерты на аномальную энтропию ответов → SIEM (год 2)
- LLM04/LLM10: rate limit на уровне Gateway уже решает 80% проблемы

### 24.3 Нагрузочное тестирование

**Методика.** k6 — инструмент нагрузочного тестирования от Grafana.
Сценарий: 3 фазы ramp-up (разогрев), steady (рабочая нагрузка),
spike (пиковая нагрузка).

```javascript
// k6 benchmark: aither-load-test.js
import { check } from 'k6';
import http from 'k6/http';

export const options = {
  stages: [
    { duration: '1m',  target: 5   },  // ramp-up
    { duration: '3m',  target: 5   },  // steady — 5 RPS
    { duration: '30s', target: 20  },  // spike — 20 RPS
    { duration: '1m',  target: 5   },  // recovery
  ],
  thresholds: {
    http_req_duration: ['p(95)<5000'],  // 95% запросов < 5 сек
    http_req_failed:   ['rate<0.05'],    // < 5% ошибок
  },
};

export default function () {
  const payload = JSON.stringify({
    model: 'qwen2.5-14b',
    messages: [{ role: 'user', content: 'Расскажи про Kubernetes за 50 слов' }],
    max_tokens: 100,
  });
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${__ENV.JWT_TOKEN}`,
    },
  };
  const res = http.post(`${__ENV.GATEWAY_URL}/v1/chat/completions`, payload, params);
  check(res, { 'status 200': (r) => r.status === 200 });
}
```

**Ожидаемые метрики нагрузки:**

| Фаза | RPS | Latency p50 | Latency p99 | Успешность | Нагрузка GPU |
|---|---|---|---|---|---|
| Ramp-up | 5 | 1.5 с | 3.5 с | 100% | ~40% |
| Steady | 5 | 1.2 с | 2.8 с | 100% | ~35% |
| Spike | 20 | 3.2 с | 12 с | 95% | ~85% |
| Recovery | 5 | 1.4 с | 3.0 с | 100% | ~35% |
|||||| *Табл. 24.3 — Профиль нагрузки (Qwen 2.5 14B, 1×RTX 6000)* |

**Интерпретация:**
- При 5 RPS платформа работает стабильно — это **рабочий режим** для 50+ пользователей
- При 20 RPS p99 возрастает до 12 секунд — GPU становится узким местом
- Решение: горизонтальное масштабирование vLLM (добавление GPU-узлов)

### 24.4 SLO/SLI и мониторинг

**SLO (Service Level Objective)** — количественная цель по доступности.
**SLI (Service Level Indicator)** — метрика, которой мы эту цель измеряем.

**SLO платформы Aither:**

| Сервис | SLO | SLI | Измерение |
|---|---|---|---|
| Gateway API | 99.5% доступности | `http_requests_total{status!~"5.."}` | Prometheus |
| vLLM Inference | 99.0% успешных ответов | `/health` endpoint | Prometheus |
| BFF Portal | 99.9% доступности | HTTP 200 rate | Prometheus |
| PostgreSQL | 99.9% доступности | `pg_isready` | Prometheus |
| Redis | 99.9% доступности | `redis_ping` | Prometheus |
| etcd | Кворум 100% времени | `etcd_server_has_leader` | Prometheus |
|||| *Табл. 24.4 — SLO матрица* |

**Grafana RED-дашборд (Rate, Errors, Duration):**

![24.4 SLO/SLI и мониторинг](diagrams/05-part4-production-31.jpg)

**Критические алерты (Severity 1 — немедленная реакция):**

| Алерт | Условие | Действие |
|---|---|---|
| `etcd_quorum_loss` | `etcd_server_has_leader == 0` > 1 мин | Восстановление etcd по снапшоту |
| `gateway_down` | `up{job="gateway"} == 0` > 30 сек | `kubectl rollout undo` |
| `gpu_oom` | `DCGM_FI_DEV_MEM_COPY_UTIL > 95` | Перенос нагрузки на соседний GPU |
| `billing_stall` | `payment_failures > 10` за 5 мин | Проверка YooKassa (test mode) |
| `redis_oom` | `used_memory > maxmemory * 0.9` | `redis-cli FLUSHDB` с осторожностью |
|||| *Табл. 24.5 — Критические алерты* |

### 24.5 Runbooks: сценарии аварийного восстановления

**Runbook** — пошаговая инструкция для дежурного инженера.
В боевой эксплуатации это главный документ: паника отключает логику,
runbook включает процедуру.

**Сценарий 1: Потеря etcd-узла**

```
Симптом: kubectl get cs — etcd unhealthy
Причина: узел K8s перезагрузился / сеть отвалилась
Кворум: 2 из 2 — при потере одного кластер теряет кворум
        (критично! нужен 3-й узел в год 2)

Процедура:
1. ssh на упавший узел
2. systemctl status kubelet — если мёртв, перезапустить
3. etcdctl --endpoints=https://...:2379 endpoint health — проверить
4. Если etcd не поднимается:
   a. ОСТАНОВИТЬ kube-apiserver на ВСЕХ узлах
   b. etcdctl snapshot restore /backup/etcd-snapshot.db
   c. Запустить kube-apiserver
5. kubectl get nodes — должно быть Ready
```

**Сценарий 2: Отказ GPU (vLLM)**

```
Симптом: vLLM pod в CrashLoopBackOff, ошибка CUDA out of memory
Причина: утечка памяти / другой процесс занял GPU / драйвер упал

Процедура:
1. nvidia-smi — проверить состояние GPU
2. Если GPU в ECC error state — перезагрузить узел
3. Если GPU OK но pod падает:
   a. kubectl logs vllm-xxx — найти ошибку
   b. kubectl delete pod vllm-xxx — пересоздать
   c. Если не помогло: kubectl drain <node> && reboot
4. После восстановления: запустить k6-тест (24.3)
5. Убедиться, что метрики пришли в норму
```

**Сценарий 3: Переполнение Redis (billing)**

```
Симптом: Gateway возвращает 503, логи: OOM command not allowed
Причина: ключи reservation:tid:* не отчистились (баг в Reaper)

Процедура:
1. redis-cli INFO memory — подтвердить переполнение
2. redis-cli --scan --pattern 'reservation:tid:*' | wc -l — посчитать
3. Если > 100 000 ключей:
   a. Проверить billing_accounts.reserved в PostgreSQL (НЕ РАВНО 0?)
   b. redis-cli --scan --pattern 'reservation:tid:*' | xargs redis-cli DEL
4. Перезапустить Gateway (kubectl rollout restart)
5. Проверить: /admin/reaper — должен вернуть "reaped": N
```

**Сценарий 4: Утечка ДСП/ПДн через ответ модели**

```
Симптом: алерт SIEM / жалоба пользователя / аудит показал
Причина: модель сгенерировала текст с маркером ДСП (например, "Для служебного пользования")

Процедура:
1. НЕМЕДЛЕННО: kubectl scale deployment vllm --replicas=0
2. Извлечь проблемный диалог: SELECT * FROM chat_messages WHERE content LIKE '%ДСП%'
3. Проверить egress-фильтр: какой паттерн пропустил?
4. Дополнить security_egress.py новым паттерном
5. kubectl apply обновлённый ConfigMap
6. kubectl scale deployment vllm --replicas=1
7. Повторный пентест проблемного диалога
```

**Сценарий 5: DoS-атака через множество API-ключей**

```
Симптом: Gateway latency p99 > 30 сек, Redis CPU 100%
Причина: злоумышленник создал 1 000 API-ключей и шлёт запросы

Процедура:
1. redis-cli KEYS 'ratelimit:*' | wc -l — аномальное количество?
2. PostgreSQL: SELECT org_id, COUNT(*) FROM portal_api_keys GROUP BY org_id
3. Заблокировать подозрительную оргу:
   UPDATE portal_organizations SET status='suspended' WHERE org_id='...'
4. Удалить ключи: UPDATE portal_api_keys SET status='revoked' WHERE org_id='...'
5. Очистить Redis: redis-cli KEYS 'ratelimit:*:SUSPICIOUS_ORG*' | xargs redis-cli DEL
6. Проверить: Gateway latency должна вернуться к p50 < 2 сек
```

| Сценарий | Вероятность | Влияние | Время реакции | Время восстановления |
|---|---|---|---|---|
| Потеря etcd-узла | Низкая | Критическое | 5 мин | 15 мин |
| Отказ GPU | Средняя | Высокое | 3 мин | 10 мин |
| Переполнение Redis | Средняя | Среднее | 5 мин | 5 мин |
| Утечка ДСП/ПДн | Низкая | Критическое | 1 мин | 15 мин |
| DoS через API-ключи | Низкая | Высокое | 5 мин | 10 мин |
||||| *Табл. 24.6 — Матрица инцидентов* |

### 24.6 Чек-лист приёмо-сдаточных испытаний (ПСИ)

Финальный документ. Подписывается заказчиком при приёмке системы.
Означает: «платформа проверена по всем пунктам и готова к эксплуатации».

**Чек-лист ПСИ (42 пункта):**

```
[ ] 1.  Развёртывание: все компоненты запускаются одной командой (kubectl apply)
[ ] 2.  Отказоустойчивость: платформа переживает отказ одного GPU-узла
[ ] 3.  Отказоустойчивость: Gateway перезапускается за < 5 секунд
[ ] 4.  Мультиарендность: org A не видит чаты org B
[ ] 5.  Мультиарендность: org A не может потратить токены org B
[ ] 6.  Безопасность: Gateway отклоняет JWT с истёкшим сроком
[ ] 7.  Безопасность: Gateway отклоняет API-ключ неактивной org
[ ] 8.  Безопасность: DLP-фильтр блокирует промпты с SQL-инъекциями
[ ] 9.  Безопасность: egress-фильтр маскирует маркеры ДСП
[ ] 10. Безопасность: mTLS между BFF и Gateway работает
[ ] 11. Биллинг: токены списываются посекундно, баланс корректен
[ ] 12. Биллинг: Reservation Reaper возвращает токены при обрыве
[ ] 13. Биллинг: YooKassa test-платежи проходят успешно
[ ] 14. Rate limiting: при превышении RPM Gateway возвращает 429
[ ] 15. Rate limiting: лимиты per-tier соблюдаются (Free vs VIP)
[ ] 16. Token quotas: суточный лимит блокирует дальнейшие запросы
[ ] 17. Token quotas: месячный лимит сбрасывается 1-го числа
[ ] 18. Модели: каталог отображает доступные модели
[ ] 19. Модели: при недоступности бэкенда модель помечается down
[ ] 20. Модели: запрос с несуществующей моделью → 400
[ ] 21. RAG: hybrid-query возвращает релевантные wiki-страницы
[ ] 22. RAG: Tier check блокирует RAG для Free-пользователей
[ ] 23. RAG: Portal UI показывает источники в ответе
[ ] 24. RAG: Wiki-граф перезагружается через /v1/rag/wiki-ingest
[ ] 25. Мониторинг: метрики Gateway в Prometheus (RED)
[ ] 26. Мониторинг: метрики GPU (DCGM) собираются
[ ] 27. Мониторинг: алерт при потере etcd-кворума
[ ] 28. Логи: Gateway аудит в PostgreSQL (chat_request_log)
[ ] 29. Логи: CEF-формат для SIEM (будущее)
[ ] 30. Резервное копирование: etcd snapshot создаётся ежедневно
[ ] 31. Резервное копирование: PostgreSQL pg_dump ежедневно
[ ] 32. Резервное копирование: восстановление из снапшота проверено
[ ] 33. Производительность: p95 latency < 5 сек при 5 RPS
[ ] 34. Производительность: > 95% успешных запросов при 20 RPS (spike)
[ ] 35. Документация: учебник (главы 1–24) соответствует коду
[ ] 36. Документация: runbooks покрывают 5 аварийных сценариев
[ ] 37. CI/CD: GitHub Actions собирает Docker-образ Gateway
[ ] 38. CI/CD: деплой через kubectl apply проходит без ошибок
[ ] 39. HA: etcd-кластер имеет кворум (≥ N/2+1 узлов)
[ ] 40. HA: Gateway переживает удаление пода (K8s пересоздаёт)
[ ] 41. Безопасность: пентест пройден (OWASP LLM Top 10, 5/10 защищены)
[ ] 42. Threat Model: документ утверждён, риски приняты
```

**Как читать чек-лист.** Каждый пункт — бинарный: пройден/не пройден.
При приёмке заказчик вправе попросить продемонстрировать любой пункт.
Поэтому каждый пункт должен быть **воспроизводим**: одна команда,
один наблюдаемый результат.

---

**Итог главы 24.** Платформа Aither прошла путь от «Python-скрипта,
проксирующего curl» до системы с Threat Model, SLO, runbooks и чек-листом
на 42 пункта. Это не значит, что работа закончена — production-эксплуатация
только начинается. Но это значит, что **платформа готова к ней**.

| Раздел | Стр. | Схем | Табл |
|---|---|---|---|
| 24.1 Threat Model | 5 | 1 | 1 |
| 24.2 PenTest (OWASP LLM Top 10) | 5 | 1 | 1 |
| 24.3 Нагрузочное тестирование (k6) | 5 | 0 | 1 |
| 24.4 SLO/SLI и мониторинг | 4 | 1 | 2 |
| 24.5 Runbooks (5 сценариев) | 6 | 0 | 1 |
| 24.6 Чек-лист ПСИ (42 пункта) | 3 | 0 | 0 |
| **Итого** | **28** | **3** | **6** |

---

*Конец части IV. Конец учебника.*
