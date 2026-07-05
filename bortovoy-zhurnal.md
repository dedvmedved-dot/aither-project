# Бортовой журнал — Aither Project

## 2026-07-03 — Старт проекта

### Контекст
- Hermes Agent v0.16.0 (VPS1) + v0.18.0 (VPS2, резерв)
- Провайдер: DeepSeek (deepseek-v4-pro, api.deepseek.com)
- Тестовая зона Cisco: доступна через VPS2 (Docker openconnect, tun1)
- HuaweiHP зона: доступна через VPS1 (tun0)
- WireGuard-мост VPS1↔VPS2: 10.99.0.0/24

### BMC серверы
- **10.129.40.50** — OpenBMC, Redfish 1.9.0, UUID c1b0a74d-...
- **10.129.40.51** — OpenBMC, Redfish 1.9.0, UUID 289530cf-...
- Доступ: web UI (https), учётка techvit (ограниченные права)
- SSH: недоступен (Permission denied)
- Redfish API: только root endpoint (/redfish/v1), остальное — 401

### Анализ доступа (2026-07-03 12:50 MSK)
- Проверены все Redfish endpoints: Systems, Chassis, Managers, SessionService
- Результат: 401 Unauthorized на всех, кроме корневого /redfish/v1
- SSH: ssh-rsa host key, permission denied (учётка без shell-доступа)
- Web UI: OpenBMC SPA, curl-логин через /login — Bad Request
- **Вывод:** учётка techvit = роль Operator/ReadOnly. Нужна Administrator.

### План после получения admin-доступа
1. `GET /redfish/v1/Systems/1` — модель, серийник, CPU, RAM
2. `GET /redfish/v1/Chassis/.../Thermal` — датчики, вентиляторы
3. `POST /redfish/v1/Managers/bmc/VirtualMedia/...` — mount ISO
4. `POST /redfish/v1/Systems/.../Reset` — reboot в boot once mode

### Задачи
- [ ] Получить admin-доступ к BMC
- [ ] Инвентаризация аппаратного обеспечения
- [ ] Настройка удалённого управления питанием
- [ ] Мониторинг температуры/вентиляторов
- [ ] Обновление прошивок

### Репозиторий
- https://github.com/dedvmedved-dot/aither-project (private)
- SSH Deploy Key: ~/.ssh/id_ed25519_aither

## 2026-07-03 14:00 — Анализ ТР и выбор ОС

### Технические решения
- **ТР №1 (Aither Architecture)**: Платформа Token-as-a-Service, 2× сервер, 4× Quadro RTX 6000, K3s + vLLM, Double-Entry биллинг (2998 строк)
- **ТР №2 (Портал Aither v6.0)**: Portal BFF (Fastify) + React SPA + Portal DB (PostgreSQL), OAuth, YooKassa/CloudPayments

### Выбор версии RED OS

| Параметр | RED OS 7.3.6 | RED OS 8.0.2 |
|---|---|---|
| Ядро Linux | 6.1.128 | **6.12.21** |
| NVIDIA driver | 535.113 | **570.144** |
| Docker | 24.x | **28.1** |
| Kubernetes | 1.28 | **1.32** |
| PostgreSQL | 15.x | **17.5** |

**Рекомендация: RED OS 8.0.2** — новейший драйвер NVIDIA 570.144, ядро 6.12 для GPU Operator, Docker 28.1 + K8s 1.32.

ISO: `redos-8-20250711.4-Everything-x86_64-DVD1.iso` (6.1 GB)

Альтернатива: RED OS 7.3.6 (`redos-MUROM-7.3.6-20250715.0-Everything-x86_64-DVD1.iso`, 5.1 GB) — если 8.0 несовместима.

### Задачи
- [x] Изучить оба ТР
- [x] Выбрать версию RED OS (8.0.2)
- [x] Проверить доступность ISO-образов
- [x] Получить admin-доступ к BMC
- [x] Инвентаризация аппаратного обеспечения
- [ ] Mount ISO → развёртывание RED OS 8.0

## 2026-07-03 15:30 — Полная инвентаризация

### Оборудование (подтверждено Redfish API)
- **2× YADRO VEGMAN S320** (серийные: 021222058D, 0202230575)
- **CPU:** 2× Intel Xeon Gold 6258R (56c/112t, 4.0 GHz Turbo) на сервер
- **RAM:** 768 GB DDR4-2934 ECC (12× Samsung 64GB) на сервер
- **GPU:** 2× NVIDIA Quadro RTX 6000 (24GB, NVLink Bridge) на сервер
- **Диски:** 12× SSD MegaRAID (2×1.7TB + 10×3.5TB) + 2× M.2 NVMe 480GB

### Сеть
- VLAN 308, подсеть 10.129.13.0/24, шлюз 10.129.13.1, DNS 10.129.13.65
- IP: node01=10.129.13.171, node02=10.129.13.172

### Принятые решения
- **RED OS 8.0.2** (ядро 6.12, NVIDIA 570)
- **K8s (kubeadm)** вместо K3s из ТР — полный Kubernetes для production GPU Operator, etcd, аудита
- **2× RTX 6000** на сервер (не 4×, как в ТР) — NVLink bridge, 48 GB VRAM/сервер
- **Диски:** RAID1 (2×1.7TB) под ОС, RAID10 (10×3.5TB) под данные, M.2 (2×480GB) под кэш Docker
- [ ] Mount ISO → развёртывание RED OS 8.0

### Важно
- **Имя пользователя на BMC**: `techvirt` (а не `techvit`!)
- Роль уже была `Administrator` на обоих BMC
- Все Redfish-эндпоинты теперь доступны (200 OK)
- 2026-07-03 14:47 — запущена полная инвентаризация обоих BMC

### 2026-07-03 15:55 — Подготовка Kickstart и блокировка BMC
- ✅ ISO RedOS 8.0.2 скачан на VPS2: `/var/www/iso/redos8.iso` (5.7 GB)
- ✅ HTTP-сервер на VPS2:8888 (python3 http.server), раздаёт ISO + Kickstart
- ✅ Kickstart-файлы: `ks-node01.cfg` (10.129.13.171) и `ks-node02.cfg` (10.129.13.172)
- ❌ BMC доступ потерян: `techvirt` → `Invalid username or password`. Пароль изменён.
- ❌ Redfish API недоступен → монтирование ISO через API невозможно
- 📋 **Ожидание:** новые креды от BMC для продолжения развёртывания
- 📋 Kickstart включает: разметку (M.2 под ОС, SSD под данные), K8s-модули, firewalld, chrony

### Kickstart-схема разметки
| Устройство | Файловая система | Назначение |
|-----------|-----------------|------------|
| nvme0n1 (M.2 480GB) | XFS | `/`, `/var`, `/var/lib/docker`, swap |
| sda (2×1.7TB SSD, RAID1) | XFS | `/data/fast` — быстрые данные |
| sdb (10×3.5TB SSD, RAID10) | XFS | `/data/bulk` — холодные данные |

---

## 2026-07-05 — Gate 3: Ядро Aither на 40.51

**Узел:** 40.51 (10.129.13.78, Astra 1.8, K8s single-node)

### Компоненты

| Компонент | Статус | Детали |
|-----------|--------|--------|
| PostgreSQL 16 | ✅ | `postgres-5889b67958-gxvmz`, ClusterIP 10.105.226.47:5432 |
| Redis 7 | ✅ | `redis-775d4dcffd-khwpw`, ClusterIP 10.100.7.0:6379 |
| API Gateway | ✅ | `gateway-5f89fbc585-f8sx7`, Python-прокси → vLLM, ClusterIP 10.98.238.242:8080 |
| vLLM (инференс) | ✅ | `vllm-qwen-758c944688-zsvp2`, Qwen2.5-14B, TP=2, ClusterIP 10.96.31.74:8000 |
| Port-forward | ✅ | `kubectl port-forward svc/gateway 30900:8080` для доступа извне |

**Доступ:** Gateway доступен на `10.129.13.78:30900`, проксирует `/v1/*` → vLLM.

---

## 2026-07-05 — Gate 4: Портал на VPS2

**Узел:** VPS2 (130.17.1.90, Ubuntu 24.04, Docker 29)

### Компоненты

| Компонент | Статус | Детали |
|-----------|--------|--------|
| PostgreSQL 16 | ✅ | `portal-db`, trust-аутентификация, порт 127.0.0.1:5432 |
| Portal BFF | ✅ | Fastify/TypeScript, Node 22, `network_mode: host`, :3000 |
| nginx | ✅ | `network_mode: host`, reverse proxy :80 → BFF:3000 |
| Core proxy | ✅ | `/api/v1/core/status` → `10.129.13.78:30900` через Cisco VPN (tun1) |

### Архитектурное решение: network_mode: host

Docker bridge-сеть изолирует контейнеры — они не видят VPN-интерфейсы хоста (tun1). Портал должен проксировать запросы к ядру на 40.51 (10.129.13.78:30900) через VPN, но из bridge это невозможно. Решение: `network_mode: host`.

Побочный эффект: Docker DNS не работает → PG_HOST должен быть `127.0.0.1`, не `portal-db`. Portal DB публикует порт 5432 на хосте.

### Эндпоинты (v0.1.0)
- `GET /health` — проверка БД
- `GET /api/v1/status` — счётчики
- `GET /api/v1/orgs` — организации
- `GET /api/v1/users` — пользователи
- `GET /api/v1/core/status` — прокси → 40.51

### Верификация
```bash
curl http://130.17.1.90:80/health
# → {"status":"ok","database":"connected"}

curl http://130.17.1.90:80/api/v1/core/status
# → связь VPS2 → 40.51 работает
```

### Питфоллы
- **Docker bridge не видит VPN-туннель** — решение: `network_mode: host`
- **Hermes redacts passwords** — `POSTGRES_HOST_AUTH_METHOD=trust`
- **Docker Compose v2** — отсутствовал на VPS2, установлен через apt

### Файлы
```
portal/
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── package.json
├── tsconfig.json
└── server.ts
```

---

## 2026-07-05 — Gate 5: Бизнес-логика (v0.3.0)

### 5.1 Аутентификация (dev-режим)

POST `/auth/dev/login` — вход по имени, выпуск JWT (jsonwebtoken, 24h).
Первый вход создаёт пользователя в `portal_users` (oauth_provider='dev').

### 5.2 Организации

POST `/api/v1/orgs` — транзакционное создание (BEGIN → INSERT org + member → COMMIT). Создатель становится `owner`.

Роли: `owner`, `billing_admin`, `developer`, `viewer`.

### 5.3 API-ключи

Таблица `portal_api_keys`: `key_id`, `org_id`, `api_key`, `api_key_prefix`, `name`, `status`.

Ключ формата `ak-<48 hex>` (randomBytes 24). Полный ключ возвращается **один раз** при создании. Далее — только префикс.

POST/DELETE — owner only (проверка через `portal_org_members.role`).

### 5.4 Деплой v0.3.0

Старый контейнер `portal-bff` (ручной деплой) конфликтовал с docker compose — `EADDRINUSE` на порту 3000. Решено остановкой и удалением.

PG_HOST=portal-db (Docker DNS) → ENOTFOUND. Исправлено на 127.0.0.1.

### Верификация
```bash
# Вход
curl -X POST .../auth/dev/login -d '{"name":"sergey"}'
# → access_token (JWT)

# Org
curl -X POST .../api/v1/orgs -d '{"name":"NebulaCorp"}'
# → {"org":{"org_id":"...","role":"owner"}}

# Ключ
curl -X POST .../api/v1/orgs/$ID/api-keys
# → {"key":{"api_key":"ak-9dc7f501..."}}

# Отзыв
curl -X DELETE .../api/v1/orgs/$ID/api-keys/$KID
# → {"key":{"status":"revoked"}}
```

**Осталось (P0):**
- Billing Service (reserve → settle → refund) — ✅ 40.51

---

## 2026-07-05 — Gate 7: Billing Service

### Double-entry биллинг
- `billing_accounts` (balance, reserved) + `billing_ledger` (reserve/settle/refund)
- PostgreSQL `SELECT FOR UPDATE` — транзакционная целостность
- 1 000 000 токенов при создании организации

### Поток
```
reserve → proxy vLLM → 200? settle(actual) : refund(reserved)
```

### Результат
Balance 1 000 000 → inference (40 tokens) → 999 960 ✅

### Питфоллы
- Hermes redacts passwords → Kubernetes Secret с base64
- PyJWT требует `cryptography` для RS256 (иначе «Algorithm not supported»)

---
- Usage Collector (подсчёт токенов из vLLM) — 40.51
- Rate Limiter (per-key) — 40.51
- Delegation Token (JWT RS256) — ✅ VPS2 → 40.51

---

## 2026-07-05 — Gate 6: Delegation Token (JWT RS256)

### Поток
```
POST /api/v1/orgs/:id/delegate → delegation_jwt (RS256, 5 min)
       ↓
Gateway проверяет signature → extract org_id → rate limit → proxy vLLM
```

### Ключи
- RSA 2048: `private.pem` (Portal BFF, только VPS2), `public.pem` (Gateway, ConfigMap)
- `pyjwt` на Gateway (чистый Python)
- Rate limit: `per-org_id` через Redis

### Результат
e2e: login → org → api-key → delegation → Gateway → vLLM → «Привет!» ✅

---

*Журнал ведётся ассистентом Hermes в хронологическом порядке*