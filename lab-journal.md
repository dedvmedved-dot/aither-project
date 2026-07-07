# Lab Journal — Aither Pilot Configuration Snapshot

> **Дата:** 2026-07-07  
> **Цель:** Полная конфигурация системы для возможности отката  
> **Статус:** Пилотный показ (неделя 1)

---

## 1. Топология

```
Интернет
  │
  ▼
VPS1 (170.168.91.95) — Hermes Agent
  │ WG: wg0 (.2 ↔ .1)
  ▼
VPS2 (130.17.1.90) — Портал + VPN-туннели
  │
  ├─ WG: wg0 (.1) — связь с VPS1
  ├─ WG: wg1 (.2) — BMC-туннель (.3 → .2:53587)
  │
  ├─ tun0 (Cisco815) — зона 10.129.11.0/24, 10.129.13.0/24
  │   ├─ .21  (10.129.11.21) — рабочая станция Astra Linux
  │   ├─ .50  (10.129.40.50) — BMC сервера 40.50 (НЕ ПОДНЯТ)
  │   ├─ .51  (10.129.40.51) — BMC сервера 40.51
  │   └─ .78  (10.129.13.78) — сервер 40.51 (ОС Astra Linux)
  │
  ├─ tun2 (HuaweiHP) — зона VPN
  │
  └─ socat-пробросы:
       ├─ :9443 → 10.129.40.50:443  (BMC 40.50)
       ├─ :9444 → 10.129.40.51:443  (BMC 40.51)
       ├─ :3389 → 10.129.11.21:3389 (RDP .21)
       └─ :5901 → 10.129.40.55:5901 (VNC)
```

---

## 2. Сервер 40.51 (10.129.13.78)

### 2.1 ОС и железо

| Параметр | Значение |
|---|---|
| **ОС** | Astra Linux 1.8 x86-64 |
| **Ядро** | 6.6.28-1-generic |
| **CPU** | 2× (модель уточнить) |
| **GPU** | 2× RTX 6000 24 GB (48 GB VRAM total) |
| **RAM** | (уточнить) |
| **Системный диск** | sda 447 GB (LV ubuntu-vg/root), свободно 328 GB |
| **Модели** | LV ubuntu-vg/models 1007 GB → /data/models, занято 58 GB |
| **NVMe** | 11 дисков sdb–sdm (1.7–3.5 TB), не задействованы |

### 2.2 NFS

```
Сервер:  10.129.13.43:/var/lib/docker/NFS
Монт-е:  /mnt/nfs43 (vers=3, tcp)
ISO:     alse-1.8.1.iso (5.6G), redos-* (4.8G, 4.8G, 1.3G), zvirt-node (3.7G)
```

### 2.3 Модели

| Модель | Путь | Размер | Статус |
|---|---|---|---|
| Qwen2.5-14B-Instruct | /data/models/Qwen2.5-14B-Instruct | 28 GB | ✅ готов |
| Saiga Llama3 8B | /data/models/saiga_llama3_8b | 15 GB | ✅ готов |
| Qwen2.5-Coder-14B-Instruct | /data/models/Qwen2.5-Coder-14B-Instruct | 15/29 GB | 🔄 качается |
| Qwen2.5-32B-GPTQ | /data/models/Qwen2.5-32B-GPTQ | 20M/19 GB | 🔄 качается |

### 2.4 vLLM

**Запущен как процесс (не Docker, не systemd):**

```bash
python3 -m vllm.entrypoints.openai.api_server \
  --model /models/Qwen2.5-14B-Instruct \
  --dtype half \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.90 \
  --tensor-parallel-size 2 \
  --enforce-eager
```

- Порт: **8000** (стандартный)
- Эндпоинт: `http://localhost:8000/v1`
- PID: 1507418 (плюс EngineCore + 2× Worker)

### 2.5 Gateway

**Запущен как процесс:**

```bash
python3 /app/gateway.py
```

Конфигурация (из env):
- `VLLM_URL=http://vllm:8000`
- `REDIS_URL=redis`
- `RATE_LIMIT=60`
- `PG_URL=<из K8s secret>`
- `TOKEN_COST=1`
- `PORT=8080`
- JWT: RS256 (публичный ключ из /app/delegation/public.pem)

Эндпоинты Gateway:
- `GET  /health` — статус
- `GET  /v1/models` — список моделей (прокси в vLLM)
- `GET  /v1/billing/` — баланс организации
- `GET  /v1/usage/` — статистика использования
- `POST /v1/chat/completions` — чат (прокси в vLLM с биллингом)

Порт: **30900** (проброшен через K8s NodePort или socat)

Проверка JWT:
```python
payload = pyjwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])
org_id = payload.get("org_id", "unknown")  # ← ПРОБЛЕМА: default="unknown"
```

### 2.6 Доступ

```bash
# Прямой SSH (быстрее, 0.5ms ping)
sshpass -p 'root' ssh root@10.129.13.78

# Через цепочку VPS2 → .21 → 40.51
ssh -J svlkravchuk@10.129.11.21 root@10.129.13.78
```

---

## 3. VPS2 (130.17.1.90) — Портал

### 3.1 Docker Compose

Файл: `/root/aither-project/portal/docker-compose.yml`

```yaml
services:
  portal-db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: portal
      POSTGRES_PASSWORD: portal
      POSTGRES_DB: portal
    volumes: [portal_pgdata:/var/lib/postgresql/data]
    healthcheck: pg_isready -U portal -d portal

  portal-bff:
    build: .
    environment:
      PG_HOST: 127.0.0.1
      PG_PORT: "5432"
      PG_USER: portal
      PG_PASSWORD: portal
      PG_DB: portal
      JWT_SECRET: "dev-jwt-secret-change-me"
      CORE_API: "http://10.129.13.78:30900"
    network_mode: host

  portal-nginx:
    image: nginx:1.27-alpine
    ports: ["80:80"]
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./static:/usr/share/nginx/html:ro
    network_mode: host
```

### 3.2 Nginx

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location /health { proxy_pass http://127.0.0.1:3000/health; }
    location /auth/  { proxy_pass http://127.0.0.1:3000; }
    location /api/   { proxy_pass http://127.0.0.1:3000; }
    location /       { try_files $uri $uri/ /index.html; }
}
```

### 3.3 BFF (Node.js + Fastify)

**Порт:** 3000  
**Фреймворк:** Fastify + CORS  
**JWT:** HS256, секрет `dev-jwt-secret-change-me`, срок 24h

**Конфигурация:**
```
CORE_API = "http://10.129.13.78:30900"
PG: 127.0.0.1:5432, user=portal, db=portal
```

**Схема БД (DDL при старте):**
- `portal_users` — пользователи (OAuth GitHub)
- `portal_organizations` — организации (aither_org_id → UUID в Gateway)
- `portal_org_members` — членство (owner/billing_admin/developer/viewer)
- `portal_api_keys` — API-ключи организаций

**Проблема `org_id: "unknown"`:**  
Фронтенд не отправляет org_id при создании сообщения → BFF не передаёт → Gateway получает `"unknown"` → биллинг падает с ошибкой UUID.

### 3.4 Фронтенд

`/root/aither-project/portal/static/index.html` — SPA, раздаётся через nginx.

### 3.5 Другие контейнеры на VPS2

| Контейнер | Назначение |
|---|---|
| `portal-db` | PostgreSQL (порт 5432 наружу НЕ открыт) |
| `vpn-cisco815` | VPN-туннель Cisco 815 |

---

## 4. Базы данных

### 4.1 Портал (portal-db, VPS2)

- **Хост:** 127.0.0.1:5432
- **Пользователь:** portal
- **Пароль:** portal
- **БД:** portal
- **Таблицы:** portal_users, portal_organizations, portal_org_members, portal_api_keys

### 4.2 Биллинг (PostgreSQL, 40.51)

- **Хост:** (через PG_URL из K8s secret)
- **Таблицы:** billing_accounts (org_id, balance, reserved), billing_ledger (ledger)

---

## 5. Сеть и доступ

| Маршрут | Путь | Задержка |
|---|---|---|
| VPS2 → 40.51 | прямой | 0.5 ms |
| VPS2 → 40.51 | через .21 | 0.9 ms |
| .21 → NFS (10.129.13.43) | Cisco 815 | 0.1 ms |
| .21 → BMC 40.51 (10.129.40.51) | Cisco 815 → 10.129.0.1 | 0.5 ms |
| 40.51 → BMC (10.129.40.51) | через 10.129.13.1 | 0.5 ms |

**Проблема:** BMC (10.129.40.51) может не иметь обратного маршрута к NFS/HTTP (10.129.13.0/24). Специалисты проверяют.

---

## 6. Текущие задачи

| Задача | Статус |
|---|---|
| Загрузка моделей (Coder 14B, 32B GPTQ) | 🔄 в процессе |
| BMC: ISO-подключение | ⏳ ждём специалистов |
| org_id "unknown" в Gateway | 📋 roadmap день 1 |
| Rate limiter, usage collector | 📋 roadmap неделя 1 |
| OAuth, платежи, Grafana | 📋 roadmap неделя 2 |

---

## 7. Полезные команды

```bash
# Проверка статуса закачки моделей
sshpass -p 'root' ssh root@10.129.13.78 "du -sh /data/models/*/"

# Проверка vLLM
sshpass -p 'root' ssh root@10.129.13.78 "curl -s http://localhost:8000/v1/models"

# Проверка Gateway
sshpass -p 'root' ssh root@10.129.13.78 "curl -s http://localhost:8080/health"

# Проверка портала
curl -s http://130.17.1.90/health

# Перезапуск портала
ssh root@130.17.1.90 "cd /root/aither-project/portal && docker compose up -d"
```
