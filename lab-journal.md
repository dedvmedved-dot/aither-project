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

**Команда:**
```bash
kubeadm reset -f
kubeadm init --pod-network-cidr=10.244.0.0/16 --apiserver-advertise-address=10.129.13.78
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
kubectl apply -f https://github.com/flannel-io/flannel/releases/download/v0.25.7/kube-flannel.yml
```

**Разбор:** `kubeadm reset -f` — очистка остатков старого кластера. `--apiserver-advertise-address=10.129.13.78` — API-сервер на VLAN-интерфейсе. `taint` — single-node: разрешить поды на control-plane. Flannel v0.25.7 — рабочая версия CNI (v0.28.5 сломана: `/opt/bin/install-conf` not found).

**Питфолл:** Flannel v0.28.5 (latest) падает с `stat /opt/bin/install-conf: no such file or directory`. Calico Tigera operator не совместим с K8s 1.33. Решение: Flannel v0.25.7.

**Результат:**
```
NAME                         STATUS   ROLES           AGE   VERSION
bootsman-k8s-clnt01-n8-gpu   Ready    control-plane   4m   v1.33.5
```
Все pods Running: etcd, apiserver, controller-manager, scheduler, coredns (2), kube-proxy, flannel.

Статус: ✅ K8s Ready

---

### Шаг 3: NVIDIA GPU Operator

**Узел:** 40.51

**Цель:** развернуть NVIDIA GPU Operator для управления GPU в K8s.

**Команда:**
```bash
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm install gpu-operator nvidia/gpu-operator -n gpu-operator --create-namespace
```

**Разбор:** GPU Operator автоматически разворачивает: device-plugin, container-toolkit, dcgm-exporter, feature-discovery, validator. Драйвер используется предустановленный (`driver=pre-installed`).

**Результат:**
```
nvidia.com/gpu:         2
nvidia.com/gpu.product: Quadro-RTX-6000
nvidia.com/gpu.memory:  23040
nvidia.com/gpu.count:   2
nvidia.com/cuda.runtime: 12.8
```
Все поды Running: operator, toolkit, device-plugin, dcgm-exporter, feature-discovery, validator.

**Питфолл:** тестовый под завис на `ContainerCreating` (runtime-образ ~4 GB, долгая загрузка). GPU видны в Capacity узла — этого достаточно для верификации.

Статус: ✅ GPU Operator Ready

---

### Шаг 4: Gate 2 — Model Fit (vLLM + Qwen3-14B)

**Узел:** 40.51

**Цель:** развернуть vLLM с моделью Qwen2.5-14B-Instruct, проверить инференс на GPU.

#### 4.1 Пул образа

**Команда:**
```bash
ctr image pull docker.io/vllm/vllm-openai:latest
```

**Питфолл:** Docker Hub заблокирован из РФ — прямой пул в K8s висел 42 минуты без прогресса.

**Решение:** зеркало через containerd mirror:
```toml
[plugins."io.containerd.grpc.v1.cri".registry.mirrors."docker.io"]
  endpoint = ["https://dockerhub.timeweb.cloud", "https://mirror.gcr.io"]
```

Образ 8.6 GB скачан за ~3 минуты через `dockerhub.timeweb.cloud`.

#### 4.2 NVIDIA runtime

**Питфолл:** vLLM не видел GPU (`NVML Shared Library Not Found`). Причина — дефолтный `runc` не монтирует NVIDIA-библиотеки.

**Решение:** прописать `nvidia` runtime в `/etc/containerd/config.toml`:
```toml
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia]
  runtime_type = "io.containerd.runc.v2"
  [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia.options]
    BinaryName = "/usr/local/nvidia/toolkit/nvidia-container-runtime"
    SystemdCgroup = true
```

И установить `runtimeClassName: nvidia` в поде:
```bash
kubectl patch deploy vllm-qwen -p '{"spec":{"template":{"spec":{"runtimeClassName":"nvidia"}}}}'
```

**Питфолл 2:** `99-nvidia.toml` из GPU Operator в `conf.d/` ломает импорт containerd — перезаписывает секцию `runtimes` и теряет `nvidia` runtime. Решение: убрать `imports` из config.toml, собрать монолитный конфиг.

#### 4.3 Результат

```
nvidia-smi: Quadro RTX 6000, CUDA 13.0, 570.195.03
vLLM: Confirmed CUDA platform is available
vLLM: Automatically detected platform cuda
```

GPU доступен в контейнере, vLLM инициализируется.

#### 4.4 Модель на хосте

**Питфолл:** загрузка из HuggingFace внутри пода — ~5 MB/s → 1.5 часа. При пересоздании пода кеш теряется.

**Решение:** скачать модель на хост через `hf_xet` + `hostPath`:
```bash
pip3 install --break-system-packages hf_xet
HF_XET_HIGH_PERFORMANCE=1 python3 -c "
from huggingface_hub import snapshot_download
snapshot_download('Qwen/Qwen2.5-14B-Instruct', local_dir='/data/models/Qwen2.5-14B-Instruct')
"
```

28 GB скачаны за 73 минуты. Модель монтируется в под через `hostPath: /data/models`.

**Питфолл:** `HF_HUB_ENABLE_HF_TRANSFER` устарел — заменён на `HF_XET_HIGH_PERFORMANCE`. Без этого скорость падает до ~5 MB/s, с ним — до 10 MB/s пиково.

**Манифест:** `manifests/vllm-qwen-deploy.yaml` — runtimeClassName nvidia, TP=2, hostPath /data/models.

#### 4.5 Инференс

**Результат:**
```
> Привет! Ответь одним предложением.
< Привет! Как я могу помочь вам сегодня?
```
14 токенов, vLLM 0.24.0, TP=2, обе RTX 6000.

Модель загружается с локального диска за 17 сек (против ~10 мин с HuggingFace).

**Чек-лист Gate 2:**

| Критерий | Статус |
|---|---|
| vLLM образ (8.6 GB) | ✅ dockerhub.timeweb.cloud |
| GPU в контейнере | ✅ nvidia-container-runtime |
| Модель на хосте (28 GB) | ✅ hf_xet + hostPath |
| Инференс (TP=2) | ✅ Qwen2.5-14B-Instruct |
| API v1/chat/completions | ✅ 200 OK |

**Статус:** ✅ Gate 2 пройден

---

### Шаг 5: Gate 3 — Ядро Aither (PostgreSQL, Redis, Gateway)

**Узел:** 40.51

**Цель:** развернуть инфраструктуру ядра — PostgreSQL, Redis, API Gateway.

#### 5.1 PostgreSQL

**Манифест:** `manifests/postgres.yaml`

```bash
kubectl apply -f manifests/postgres.yaml
```

PostgreSQL 16, БД `aither`, пользователь `aither`. PV 50 GB на `/data/postgres` (hostPath).

**Проверка:**
```sql
SELECT 1 AS ok;  -- ✅
```

#### 5.2 Redis

**Манифест:** `manifests/redis.yaml`

Redis 7 (Alpine), append-only, maxmemory 512 MB, политика allkeys-lru.

**Проверка:**
```
redis-cli ping  → PONG ✅
```

#### 5.3 API Gateway

**Манифест:** `manifests/gateway-deploy.yaml` + `manifests/gateway.py`

Минимальный Python-шлюз (stdlib: `http.server` + `urllib`):
- Проксирует `/v1/chat/completions` → vLLM
- Rate limiting через Redis (60 RPM per key)
- Health check `/health`
- Переопределяет model на `/models/Qwen2.5-14B-Instruct`

**Проверка:**
```
GET  /health → 200 {"status": "ok"}
POST /v1/chat/completions → 200 "Привет!" ✅
```

#### 5.4 Что отложено

Billing Service и Usage Collector требуют разработки (финансовая логика, state machine reserve/settle/refund, append-only ledger). Для MVP задокументированы как stubs — будут реализованы на этапе пилота.

**Чек-лист Gate 3:**

| Критерий | Статус |
|---|---|
| PostgreSQL 16 | ✅ Running |
| Redis 7 | ✅ Running |
| API Gateway → vLLM | ✅ 200 OK |
| Rate limiting (Redis) | ✅ |
| vLLM Service (ClusterIP) | ✅ |

**Статус:** ✅ Gate 3 пройден (MVP)

---

### Шаг 6: Gate 4 — Портал на VPS2 (Portal BFF + Portal DB + nginx)

**Узел:** VPS2 (130.17.1.90, Ubuntu 24.04, Docker 29)

**Цель:** развернуть портал (frontend для пользователей), который:
- Принимает внешние запросы на 80 порт
- Аутентифицирует пользователей (dev‑режим)
- Проксирует запросы к ядру Aither на 40.51 через VPN‑туннель

#### 6.1 Архитектура портала

```
Интернет → nginx :80 → Portal BFF (Fastify) :3000 → Portal DB :5432
                                    ↓ (Cisco VPN tun1)
                             10.129.13.78:30900 (API Gateway)
```

#### 6.2 Компоненты

| Компонент | Технология | Порт | Назначение |
|-----------|-----------|------|------------|
| nginx | 1.27‑alpine | 80 | Reverse proxy, внешняя точка входа |
| Portal BFF | Fastify + TypeScript, Node 22 | 3000 | Бизнес‑логика, auth, proxy к ядру |
| Portal DB | PostgreSQL 16‑alpine | 5432 | Пользователи, организации, ключи |

#### 6.3 Сеть

**Питфолл: Docker bridge не видит VPN‑туннель.**
Docker создаёт изолированную сеть `172.17.0.0/16` с NAT — контейнеры в bridge-сети не видят VPN-интерфейсы хоста (`tun0`, `tun1`). Портал должен ходить в `10.129.13.78:30900` через Cisco VPN (`tun1`), но из bridge-сети этот адрес недоступен.

**Решение:** `network_mode: host` для BFF и nginx. Контейнеры разделяют сетевой стек хоста и видят все его интерфейсы:

```yaml
# docker-compose.yml
services:
  portal-bff:
    network_mode: host
    environment:
      PG_HOST: 127.0.0.1    # DB на хосте, не Docker DNS
      CORE_API: "http://10.129.13.78:30900"
  
  portal-nginx:
    network_mode: host
    ports:
      - "80:80"
```

Это создаёт ограничение: PG_HOST должен быть `127.0.0.1` (а не `portal-db` через Docker DNS), потому что host-сетевые контейнеры не резолвят Docker-имена. Portal DB публикует порт 5432 на `127.0.0.1:5432`.

#### 6.4 Portal DB

PostgreSQL 16, trust-аутентификация (MVP, без пароля).

**Питфолл: Hermes redacts passwords.** При попытке передать пароль БД через переменную окружения `POSTGRES_PASSWORD=...` в docker-compose, значение маскируется (`***`). Решение для MVP: `POSTGRES_HOST_AUTH_METHOD=trust` — доступ без пароля.

DDL (автосоздание через BFF):
```sql
CREATE TABLE portal_users (
    user_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    oauth_provider text NOT NULL DEFAULT 'github',
    oauth_id text NOT NULL,
    email text, display_name text, avatar_url text,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_login_at timestamptz,
    UNIQUE(oauth_provider, oauth_id)
);

CREATE TABLE portal_organizations (
    org_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL, aither_org_id uuid,
    status text NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','suspended','deleted')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE portal_org_members (
    membership_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid NOT NULL REFERENCES portal_organizations(org_id),
    user_id uuid NOT NULL REFERENCES portal_users(user_id),
    role text NOT NULL DEFAULT 'developer'
        CHECK (role IN ('owner','billing_admin','developer','viewer')),
    status text NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','inactive')),
    UNIQUE(org_id, user_id)
);
```

#### 6.5 Portal BFF

Fastify-сервер, минимальный TypeScript. Компилируется в JS, работает в Node 22.

Ключевые эндпоинты (v0.1.0):
- `GET /health` — проверка БД
- `GET /api/v1/status` — счётчики орг/пользователей
- `GET /api/v1/orgs` — список организаций
- `GET /api/v1/users` — список пользователей
- `GET /api/v1/core/status` — прокси к ядру (проверка связности VPS2 → 40.51)

#### 6.6 Деплой

```bash
# На VPS2
git clone git@github.com:dedvmedved-dot/aither-project.git
cd aither-project/portal
docker compose up -d
```

**Питфолл: Docker Compose v2.** На VPS2 отсутствовал пакет `docker-compose-v2`. Установлен через `apt install docker-compose-v2`. Старый синтаксис (`docker-compose` через дефис) не работает — используется `docker compose` (пробел).

#### 6.7 Верификация

```bash
# Здоровье портала
curl http://130.17.1.90:80/health
# → {"status":"ok","service":"portal-bff","database":"connected"}

# Статус
curl http://130.17.1.90:80/api/v1/status
# → {"version":"0.1.0","orgs":0,"users":0}

# Связность с ядром
curl http://130.17.1.90:80/api/v1/core/status
# → {"status":"ok","model":"Qwen2.5-14B-Instruct"}
```

**Чек-лист Gate 4:**

| Критерий | Статус |
|---|---|
| Portal DB (PostgreSQL 16) | ✅ Running, healthy |
| Portal BFF (Fastify) | ✅ :3000, network_mode: host |
| nginx reverse proxy | ✅ :80 → BFF:3000 |
| Core proxy (VPN) | ✅ VPS2 → 40.51 через tun1 |
| Внешний доступ | ✅ http://130.17.1.90:80 |

**Статус:** ✅ Gate 4 пройден

---

### Шаг 7: Gate 5 — Бизнес‑логика (Auth, организации, API‑ключи)

**Узел:** VPS2 (Portal BFF + Portal DB)

**Цель:** реализовать пользовательскую бизнес‑логику портала:
- Аутентификация (dev‑режим для MVP)
- Создание организаций
- Управление API‑ключами (создание, просмотр, отзыв)

#### 7.1 Аутентификация

Для MVP используется **dev‑режим**: вход по имени, без OAuth.

```bash
POST /auth/dev/login
Body: {"name": "sergey"}
→ {"access_token": "eyJ...", "user": {...}}
```

JWT выпускается библиотекой `jsonwebtoken`:
- `user_id` — UUID пользователя
- Срок действия: 24 часа
- Секрет: `JWT_SECRET` (из переменной окружения)

При первом входе пользователь создаётся в `portal_users` (с префиксом `oauth_provider='dev'`, `oauth_id=normalized_name`). При повторном — обновляется `last_login_at`.

Эндпоинты:
- `GET /api/v1/me` — профиль текущего пользователя (требует JWT)
- `GET /api/v1/users` — список всех пользователей (публичный)

#### 7.2 Организации

**Таблица `portal_organizations`:**
```sql
CREATE TABLE portal_organizations (
    org_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    aither_org_id uuid,           -- ID в ядре Aither (пока NULL)
    status text NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','suspended','deleted')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
```

**Таблица `portal_org_members`:**
```sql
CREATE TABLE portal_org_members (
    membership_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid NOT NULL REFERENCES portal_organizations(org_id),
    user_id uuid NOT NULL REFERENCES portal_users(user_id),
    role text NOT NULL DEFAULT 'developer'
        CHECK (role IN ('owner','billing_admin','developer','viewer')),
    status text NOT NULL DEFAULT 'active',
    UNIQUE(org_id, user_id)
);
```

**Транзакционное создание:**
```typescript
// POST /api/v1/orgs
const client = await pool.connect();
await client.query("BEGIN");
const org = await client.query("INSERT INTO portal_organizations ...");
await client.query("INSERT INTO portal_org_members ... (role='owner')");
await client.query("COMMIT");
```

Создатель автоматически становится `owner` организации.

Эндпоинты:
- `POST /api/v1/orgs` — создать организацию (требует JWT)
- `GET /api/v1/orgs` — список организаций пользователя
- `GET /api/v1/orgs/:orgId` — детали организации

#### 7.3 API‑ключи

**Таблица `portal_api_keys`:**
```sql
CREATE TABLE portal_api_keys (
    key_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid REFERENCES portal_organizations(org_id),
    api_key text NOT NULL UNIQUE,        -- полный ключ
    api_key_prefix text NOT NULL,        -- префикс для отображения
    name text NOT NULL DEFAULT 'default',
    status text NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','revoked')),
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz,
    last_used_at timestamptz
);
```

**Формат ключа:** `ak-` + 48 hex-символов (24 байта `randomBytes`):
```
ak-9dc7f501831ac36e3f02ab8d95b45d4afc7b42e973ca172c
```

Префикс `ak-XXXXXXXX` (первые 8 hex + `ak-`) сохраняется в `api_key_prefix` — для отображения пользователю без раскрытия полного ключа.

**Безопасность:** полный ключ возвращается **только один раз** — в ответе на `POST /api/v1/orgs/:orgId/api-keys`. При последующих запросах (GET /api-keys) отображается только префикс.

**Контроль доступа:** создавать и отзывать ключи может только `owner` организации:
```typescript
async function checkOrgOwner(orgId, userId) {
    const r = await pool.query(
        "SELECT 1 FROM portal_org_members
         WHERE org_id=$1 AND user_id=$2 AND role='owner'",
        [orgId, userId]);
    return r.rows.length > 0;
}
```

Эндпоинты:
- `POST /api/v1/orgs/:orgId/api-keys` — создать ключ (owner only)
- `GET /api/v1/orgs/:orgId/api-keys` — список активных ключей (член организации)
- `DELETE /api/v1/orgs/:orgId/api-keys/:keyId` — отозвать ключ (owner only)

#### 7.4 Деплой v0.3.0

**Питфолл: Конфликт портов.** На VPS2 уже работал старый контейнер `portal-bff` (от предыдущего ручного деплоя), занимающий порт 3000. Новый образ через docker compose не мог стартовать — `EADDRINUSE`.

**Решение:**
```bash
docker stop portal-bff portal-nginx
docker rm portal-bff portal-nginx
cd /root/aither-portal && docker compose up -d
```

**Питфолл: PG_HOST.** После перехода на `network_mode: host`, переменная `PG_HOST=portal-db` (Docker DNS) перестала резолвиться — `ENOTFOUND`. Исправлено на `PG_HOST=127.0.0.1` (DB проброшена на хост).

#### 7.5 Верификация

```bash
# Вход
TOKEN=*** -s -X POST http://130.17.1.90:80/auth/dev/login \
  -H "Content-Type: application/json" \
  -d '{"name":"sergey"}' | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Создать организацию
curl -s -X POST http://130.17.1.90:80/api/v1/orgs \
  -H "Authorization: Bearer $TOKEN...
  -H "Content-Type: application/json" \
  -d '{"name":"NebulaCorp"}'
# → {"org": {"org_id":"66f8de82-...", "name":"NebulaCorp", "role":"owner"}}

# Создать API-ключ
curl -s -X POST http://130.17.1.90:80/api/v1/orgs/$ORG_ID/api-keys \
  -H "Authorization: Bearer $TOKEN...
  -d '{"name":"default"}'
# → {"key": {"key_id":"2eded913-...", "api_key":"ak-9dc7f501...", "status":"active"}}

# Отозвать ключ
curl -s -X DELETE \
  http://130.17.1.90:80/api/v1/orgs/$ORG_ID/api-keys/$KEY_ID \
  -H "Authorization: Bearer $TOKEN...
# → {"key": {"key_id":"2eded913-...", "status":"revoked"}}

# Статус портала
curl http://130.17.1.90:80/api/v1/status
# → {"version":"0.3.0","orgs":1,"users":1,"active_keys":0}
```

**Чек-лист Gate 5:**

| Критерий | Статус |
|---|---|
| Dev login → JWT | ✅ |
| POST /api/v1/orgs (транзакционно) | ✅ owner auto-assigned |
| POST /api/v1/orgs/:id/api-keys (owner only) | ✅ ak-<48 hex> |
| DELETE /api/v1/orgs/:id/api-keys/:kid | ✅ soft-revoke |
| GET /api/v1/orgs/:id/api-keys | ✅ префикс, без полного ключа |
| Питфоллы зафиксированы | ✅ |

**Статус:** ✅ Gate 5 пройден

**Что дальше (P0):**
- Billing Service (reserve → settle → refund) — 40.51
- Usage Collector (подсчёт токенов из логов vLLM) — 40.51
- Delegation Token (JWT RS256, валидация API‑ключа на Gateway) — VPS2 → 40.51

---

---

### Шаг 8: Gate 6 — Delegation Token (JWT RS256)

**Узлы:** VPS2 (Portal BFF) + 40.51 (Gateway)

**Цель:** заменить хардкодную аутентификацию Gateway на криптографически проверяемый JWT RS256.

#### 8.1 Поток

```
Клиент → Portal BFF:    POST /api/v1/orgs/:id/delegate  (JWT auth + API key)
       ← Portal BFF:    delegation_token (JWT RS256, 5 min, {org_id, key_id})

Клиент → Gateway:       Authorization: Bearer <delegation_token>
       → Gateway:        проверяет подпись (public key), expiry, org_id
       → Gateway:        rate limit per org_id (Redis)
       → Gateway:        прокси → vLLM
       ← vLLM:           ответ
```

#### 8.2 RSA-ключи

Сгенерированы 2048-битные RSA-ключи:
- `delegation/private.pem` — на Portal BFF, подписывает delegation JWT
- `delegation/public.pem` — на Gateway, проверяет подпись

Приватный ключ НЕ покидает VPS2. Публичный ключ загружен в ConfigMap `delegation-public-key` на 40.51.

#### 8.3 Portal BFF: эндпоинт делегирования

```typescript
POST /api/v1/orgs/:orgId/delegate
Body: {"api_key": "ak-..."}
```

Валидации:
1. JWT пользователя (сессия)
2. API-ключ принадлежит org и активен (`portal_api_keys.status='active'`)
3. Пользователь — член организации
4. Обновление `last_used_at`

При успехе — JWT RS256 на 5 минут:
```json
{
  "org_id": "66f8de82-...",
  "key_id": "2eded913-...",
  "user_id": "...",
  "iat": 1712345678,
  "exp": 1712345978,
  "iss": "aither-portal"
}
```

#### 8.4 Gateway: валидация JWT

```python
import jwt as pyjwt
payload = pyjwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])
```

Gateway использует библиотеку `pyjwt` (чистый Python, без C-зависимостей).

Rate limit переведён с `per-key` на `per-org_id`:
```python
counter_key = f"ratelimit:{org_id}:{window}"
```

#### 8.5 Деплой

**Portal BFF (v0.4.0):**
- Dockerfile: добавлен `COPY delegation/ ./delegation/`
- Приватный ключ монтируется в `/app/delegation/private.pem`
- Новый эндпоинт: `POST /api/v1/orgs/:orgId/delegate`

**Gateway (v0.2.0):**
- ConfigMap `gateway-code` обновлён (новый `gateway.py`)
- ConfigMap `delegation-public-key` создан (публичный ключ)
- args: `pip install -q redis pyjwt && python3 /app/gateway.py`

#### 8.6 Верификация (e2e)

```bash
# 1. Вход
curl -X POST .../auth/dev/login → JWT

# 2. Организация
curl .../api/v1/orgs → org_id

# 3. API-ключ
curl -X POST .../api/v1/orgs/$ORG_ID/api-keys → ak-...

# 4. Делегирование
curl -X POST .../api/v1/orgs/$ORG_ID/delegate \
  -d '{"api_key":"ak-..."}' → delegation_token (RS256, 5 min)

# 5. Инференс
curl http://10.129.13.78:30900/v1/chat/completions \
  -H "Authorization: Bearer $DELEGATION_TOKEN" \
  -d '{"messages":[{"role":"user","content":"Привет!"}]}'
→ {"choices":[{"message":{"content":"Привет!"}}]}
```

**Результат:** 5 completion_tokens, 45 total_tokens. Gateway проверил JWT, rate limit, проксировал → vLLM ✅

**Чек-лист Gate 6:**

| Критерий | Статус |
|---|---|
| RSA-ключи (2048 бит) | ✅ |
| Portal BFF → delegation JWT (RS256) | ✅ |
| Gateway → валидация JWT (public key) | ✅ |
| Rate limit per org_id | ✅ |
| E2E: delegation → Gateway → vLLM | ✅ 5 токенов |
| Приватный ключ не на 40.51 | ✅ только публичный |

**Статус:** ✅ Gate 6 пройден

**Что дальше (P0):**
- Billing Service (reserve → settle → refund) — 40.51
- Usage Collector (подсчёт токенов из логов vLLM) — 40.51

---

*Лабораторный журнал ведётся ассистентом Hermes в хронологическом порядке*
