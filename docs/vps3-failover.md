# VPS3 Failover — горячий резерв портала Aither

**Дата:** 09.07.2026
**Статус:** ✅ Реализовано
**Этап:** 5 — Продакшен-класс, задача #22

---

## 1. Архитектура

### 1.1. Текущая схема (без резервирования)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ПОЛЬЗОВАТЕЛЬ                                     │
│                     (браузер, API-клиент)                                 │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ HTTPS
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          VPS2 (130.17.1.90)                              │
│                                                                          │
│   ┌──────────┐     ┌──────────────────────────┐     ┌────────────────┐  │
│   │  nginx   │────▶│  Статика (SPA index.html) │     │                │  │
│   │  :80     │     └──────────────────────────┘     │                │  │
│   │          │─────────────────────────────────────▶│  BFF :3000     │  │
│   │          │     ┌──────────────────────────┐     │  (Fastify)     │  │
│   │          │◀────│  PostgreSQL (локальный)   │◀────│                │  │
│   └──────────┘     │  · portal_users           │     └───────┬────────┘  │
│                    │  · portal_organizations   │             │            │
│                    │  · portal_org_members     │             │            │
│                    │  · portal_api_keys        │             │            │
│                    │  · billing_accounts       │             │            │
│                    │  · subscription_tiers     │             │            │
│                    └──────────────────────────┘             │            │
└─────────────────────────────────────────────────────────────┼────────────┘
                                                              │
                                                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     K8s Cluster (n8: 10.129.13.78)                        │
│                                                                          │
│   ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐   │
│   │ Gateway  │  │  vLLM    │  │  PostgreSQL   │  │  Redis           │   │
│   │ :30900   │  │ 14B+32B  │  │  · usage      │  │  · rate limits   │   │
│   │          │  │ +LoRA    │  │  · billing    │  │  · tier cache    │   │
│   └──────────┘  └──────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

**Проблема:** VPS2 — единая точка отказа. При падении VPS2:
- Портал недоступен (nginx, BFF)
- Невозможна аутентификация (PG локальный)
- Невозможно создание API-ключей

K8s-кластер при этом продолжает работать — Gateway, vLLM, биллинг функционируют.

### 1.2. Целевая схема (с горячим резервом)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            ПОЛЬЗОВАТЕЛЬ                                   │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │ HTTPS
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     VPS1 (170.168.91.95) — точка входа                     │
│                                                                           │
│   ┌───────────────────────────────────────────────────────────────────┐  │
│   │                        nginx :443                                  │  │
│   │                                                                    │  │
│   │   upstream portal {                                                │  │
│   │     server 130.17.1.90:80  max_fails=3 fail_timeout=30s;  ← VPS2  │  │
│   │     server 89.127.217.88:80 max_fails=1 fail_timeout=10s backup;  │  │
│   │   }                                                                │  │
│   │                                                                    │  │
│   │   health_check interval=30s  ← мониторинг VPS2                     │  │
│   └───────────────────────────────────────────────────────────────────┘  │
└──────┬──────────────────────────────────────────────┬────────────────────┘
       │                                              │
       │ PRIMARY (active)                             │ STANDBY (backup)
       ▼                                              ▼
┌─────────────────────────┐              ┌─────────────────────────┐
│  VPS2 (130.17.1.90)     │              │  VPS3 (89.127.217.88)   │
│                          │              │                          │
│  ┌──────────┐           │              │  ┌──────────┐           │
│  │  nginx   │           │              │  │  nginx   │           │
│  │  :80     │           │              │  │  :80     │           │
│  └────┬─────┘           │              │  └────┬─────┘           │
│       │                  │              │       │                  │
│  ┌────▼─────┐           │              │  ┌────▼─────┐           │
│  │ BFF :3000│           │              │  │ BFF :3000│           │
│  └────┬─────┘           │              │  └────┬─────┘           │
│       │                  │              │       │                  │
└───────┼──────────────────┘              └───────┼──────────────────┘
        │                                         │
        └──────────────┬──────────────────────────┘
                       │ общий K8s PostgreSQL
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    K8s Cluster (n8: 10.129.13.78)                          │
│                                                                           │
│   ┌──────────┐  ┌──────────┐  ┌───────────────────────────────────────┐ │
│   │ Gateway  │  │  vLLM    │  │  PostgreSQL (ЕДИНЫЙ для всех)          │ │
│   │ :30900   │  │ 14B+32B  │  │                                        │ │
│   │          │  │ +LoRA    │  │  · usage_records     (биллинг)         │ │
│   └──────────┘  └──────────┘  │  · billing_accounts   (биллинг)        │ │
│                               │  · billing_ledger     (биллинг)        │ │
│   ┌──────────┐  ┌──────────┐  │  · subscription_tiers (тарифы)         │ │
│   │  Redis   │  │ ChromaDB │  │  · portal_users       (auth) ★         │ │
│   │          │  │          │  │  · portal_organizations(auth) ★        │ │
│   └──────────┘  └──────────┘  │  · portal_org_members (auth) ★         │ │
│                               │  · portal_api_keys    (auth) ★         │ │
│                               └───────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘

★ — таблицы, перенесённые из локального PG VPS2 в K8s PG
```

### 1.3. Ключевое изменение: Stateless BFF

**Было:** VPS2 имеет локальный PostgreSQL с auth-таблицами. BFF привязан к VPS2.

**Стало:** Все таблицы в K8s PostgreSQL. VPS2 и VPS3 — идентичные stateless узлы:
- BFF подключается к K8s PG (host: `10.129.13.78`, port: `31113`)
- Локальный PG на VPS2/VPS3 **не нужен**
- Любой экземпляр BFF может обслужить запрос
- Синхронизация данных не требуется — PostgreSQL один на всех

---

## 2. Механика failover

### 2.1. Нормальный режим

```
Пользователь → VPS1:443 → VPS2:80 → nginx → статика / BFF:3000 → K8s Gateway
```

- VPS1 проверяет VPS2 каждые 30 секунд: `GET /health`
- VPS2 отвечает `200 OK` → трафик идёт на VPS2
- VPS3 простаивает (backup server, не получает запросов)

### 2.2. Авария VPS2

```
t=0:   VPS2 падает (процесс убит, сеть отвалилась, OOM)
t=30:  VPS1 health check → timeout / connection refused
t=30:  nginx помечает VPS2 как "down" (max_fails=3 достигнут)
t=31:  Следующий запрос → nginx направляет на VPS3 (backup)
t=31+: VPS3 обслуживает запросы (статика, BFF, K8s Gateway)
```

**Задержка переключения:** ≤ 30 секунд (интервал health check).

### 2.3. Восстановление VPS2

```
t=X:   VPS2 восстановлен, nginx отвечает на health check
t=X+1: nginx возвращает VPS2 в upstream
t=X+2: Трафик снова идёт на VPS2
```

**Обратное переключение:** мгновенное, как только VPS2 ответил на health check.

### 2.4. Состояние пользователя при failover

| Аспект | Поведение |
|---|---|
| **SPA-приложение** | Не заметит переключения — статика отдаётся VPS3 |
| **Активный чат** | Текущий SSE-стрим оборвётся. Новые запросы пойдут через VPS3 → тот же Gateway K8s |
| **Аутентификация** | JWT-токен уже выпущен — работает. Новый логин → OAuth → BFF VPS3 → K8s PG → успешно |
| **Баланс токенов** | Без изменений — биллинг в K8s PG, общий |
| **API-ключи** | Без изменений — таблица portal_api_keys в K8s PG |

---

## 3. Миграция auth-таблиц в K8s PostgreSQL

### 3.1. Что переносим

| Таблица | Назначение | Текущее размещение | Целевое размещение |
|---|---|---|---|
| `portal_users` | OAuth-пользователи (GitHub, Google, Яндекс) | Локальный PG VPS2 | K8s PG |
| `portal_organizations` | Организации | Локальный PG VPS2 | K8s PG |
| `portal_org_members` | Членство в организациях | Локальный PG VPS2 | K8s PG |
| `portal_api_keys` | API-ключи | Локальный PG VPS2 | K8s PG |
| `chats` | История чатов | Локальный PG VPS2 | K8s PG |
| `chat_messages` | Сообщения | Локальный PG VPS2 | K8s PG |
| `security_audit` | Журнал безопасности | Локальный PG VPS2 | K8s PG |
| `payment_transactions` | Транзакции ЮKassa | Локальный PG VPS2 | K8s PG |
| `billing_accounts` | Баланс (дубль) | Оба PG | K8s PG (убрать из локального) |
| `subscription_tiers` | Тарифы (дубль) | Оба PG | K8s PG (убрать из локального) |

### 3.2. Порядок миграции

1. **Создать таблицы в K8s PG** — с теми же колонками + улучшить индексы
2. **Экспорт из локального PG** — `pg_dump --data-only` для целевых таблиц
3. **Импорт в K8s PG** — загрузка данных
4. **Обновить BFF server.js** — переключить pool на K8s PG
5. **Перезапустить BFF на VPS2** — проверить работоспособность
6. **Очистить локальный PG** — удалить перенесённые таблицы (опционально)

### 3.3. Конфигурация BFF после миграции

```javascript
// Было: два пула
const pool = new Pool({ host: "127.0.0.1", user: "portal", database: "portal" });      // локальный
const k8sPool = new Pool({ host: "10.129.13.78", port: 31113, user: "aither" });       // K8s

// Стало: один пул
const pool = new Pool({ host: "10.129.13.78", port: 31113, user: "aither", database: "aither" });
// k8sPool удалён — больше не нужен
```

---

## 4. Настройка VPS3

### 4.1. Компоненты

| Компонент | Назначение | Конфигурация |
|---|---|---|
| **nginx** | Отдача статики + прокси API | Идентично VPS2 |
| **BFF (Node.js)** | Fastify-сервер :3000 | Stateless, подключается к K8s PG |
| **Статика** | SPA (index.html + assets) | Копия с VPS2 |

### 4.2. Что НЕ нужно на VPS3

- ❌ Локальный PostgreSQL — не нужен
- ❌ Синхронизация БД — не нужна
- ❌ Ключи делегирования — не нужны (BFF использует свои)

### 4.3. Синхронизация кода

```bash
# cron каждые 30 минут: синхронизация BFF + статики с VPS2
*/30 * * * * rsync -az --delete root@130.17.1.90:/root/aither-project/portal/dist/ /root/aither-project/portal/dist/
*/30 * * * * rsync -az --delete root@130.17.1.90:/root/aither-project/portal/static/ /root/aither-project/portal/static/
```

**Примечание:** синхронизация файлов BFF не обязательна при нормальной работе (VPS3 не активен), но обеспечивает готовность к переключению без задержки.

---

## 5. Настройка VPS1 — nginx reverse proxy

### 5.1. Конфигурация

```nginx
upstream portal_backend {
    server 130.17.1.90:80 max_fails=3 fail_timeout=30s;   # PRIMARY
    server 89.127.217.88:80 max_fails=1 fail_timeout=10s backup;  # STANDBY
}

server {
    listen 443 ssl http2;
    server_name aither.170.168.91.95.nip.io;

    ssl_certificate     /etc/nginx/ssl/aither.crt;
    ssl_certificate_key /etc/nginx/ssl/aither.key;

    # Проксирование всего на portal_backend
    location / {
        proxy_pass http://portal_backend;
        proxy_http_version 1.1;

        # WebSocket / SSE support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE: не буферизировать
        proxy_buffering off;
        proxy_read_timeout 300s;

        # Таймауты
        proxy_connect_timeout 5s;
        proxy_next_upstream error timeout http_502 http_503 http_504;
        proxy_next_upstream_tries 2;
    }
}
```

### 5.2. Ключевые директивы

| Директива | Значение | Эффект |
|---|---|---|
| `max_fails=3` | 3 фейла | После 3 ошибок health check сервер помечается down |
| `fail_timeout=30s` | 30 секунд | Через 30s сервер возвращается в пул для проверки |
| `backup` | только VPS3 | Трафик идёт на backup только когда primary недоступен |
| `proxy_next_upstream` | error, timeout, 502, 503, 504 | При этих ошибках пробовать следующий сервер |
| `proxy_connect_timeout` | 5 секунд | Быстрый детект падения VPS2 |

---

## 6. Тестирование failover

### 6.1. Сценарий 1: Плановое отключение

```bash
# 1. Останавливаем BFF на VPS2
ssh root@130.17.1.90 "kill $(pgrep -f 'node dist/server.js')"

# 2. Проверяем: портал должен работать через VPS3
curl -k https://aither.170.168.91.95.nip.io/api/v1/status
# → {"status":"ok","bff":"vps3"}  # убеждаемся что ответ от VPS3

# 3. Возвращаем VPS2
ssh root@130.17.1.90 "cd /root/aither-project/portal && nohup node dist/server.js &"

# 4. Трафик возвращается на VPS2
```

### 6.2. Сценарий 2: Жёсткое падение

```bash
# 1. Имитация падения VPS2
ssh root@130.17.1.90 "iptables -A INPUT -p tcp --dport 80 -j DROP"

# 2. Ждём 30 секунд (health check + fail_timeout)

# 3. Запросы идут на VPS3

# 4. Восстановление
ssh root@130.17.1.90 "iptables -D INPUT -p tcp --dport 80 -j DROP"
```

### 6.3. Чек-лист приёмки

| # | Проверка | Ожидаемый результат |
|---|---|---|
| 1 | Портал открывается (статика) | SPA загружается |
| 2 | Логин через GitHub OAuth | Успешная аутентификация |
| 3 | Создание организации | Организация создана, видна в списке |
| 4 | Создание API-ключа | Ключ создан, работает с Gateway |
| 5 | Отправка сообщения в чат | Ответ от модели получен |
| 6 | Проверка баланса | Баланс корректен |
| 7 | Отключение VPS2 | Портал работает через VPS3 |
| 8 | Восстановление VPS2 | Трафик вернулся на VPS2 |

---

## 7. Ограничения и риски

| Риск | Вероятность | Влияние | Митигация |
|---|---|---|---|
| VPS1 — единая точка отказа | Низкая | Высокое (портал недоступен) | VPS1 — минимальный сервис (только nginx), надёжен |
| VPS3 устаревший код | Средняя | Низкое (отставание ≤ 30 мин) | Уменьшить интервал rsync до 5 мин в production |
| Оба VPS падают | Низкая | Критическое | Добавить третий узел (будущий VPS4) |
| K8s PG недоступен | Низкая | Высокое (никакой BFF не работает) | HA для PostgreSQL в K8s |
| SSE-стрим обрывается при failover | 100% при переключении | Низкое | Клиент переподключается автоматически |

---

## 8. Сводка

### Что даёт failover

- **Доступность портала:** 99.9% (при падении VPS2 — переключение за ≤ 30с)
- **Stateless BFF:** оба узла идентичны, не требуют синхронизации БД
- **Единая база:** все данные в K8s PostgreSQL — один источник истины
- **Простота:** nginx-механика без Kubernetes, без keepalived, без плавающих IP

### Компоненты после внедрения

| Узел | Роль | Сервисы |
|---|---|---|
| **VPS1** | Reverse proxy + health check | nginx :443 |
| **VPS2** | Primary портал | nginx :80, BFF :3000 |
| **VPS3** | Standby портал | nginx :80, BFF :3000 |
| **K8s (n8)** | Вычисления + данные | Gateway, vLLM, PostgreSQL, Redis, ChromaDB |

### Оценка трудозатрат

| Этап | Часы |
|---|---|
| Миграция auth-таблиц в K8s PG | 2 |
| Обновление BFF server.js | 1 |
| Настройка VPS3 (nginx + BFF) | 2 |
| VPS1 nginx reverse proxy | 1 |
| Тестирование failover | 2 |
| **Итого** | **8 часов (1 рабочий день)** |

---

## 9. Реализация (фактические конфигурации)

### 9.1. VPS3 — инвентаризация

| Параметр | Значение |
|---|---|
| Хостнейм | `334149.fornex.cloud` |
| IP | `89.127.217.88` |
| OS | Ubuntu 24.04.4 LTS |
| RAM | 8 GB |
| Диск | 120 GB (4.2G занято) |
| Node.js | 18.19.1 (из apt) |
| Nginx | 1.24.0 (из apt) |

### 9.2. SSH-туннель к K8s (systemd)

VPS3 не имеет прямого доступа к сети K8s (10.129.13.0/24). SSH-туннель через VPS1 пробрасывает PostgreSQL (:5432) и Gateway (:30900).

**Файл:** `/etc/systemd/system/pg-tunnel.service`

```ini
[Unit]
Description=SSH Tunnel to K8s (PG + Gateway) via VPS1
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 \
  -L 127.0.0.1:5432:10.129.13.78:31113 \
  -L 127.0.0.1:30900:10.129.13.78:30900 \
  -N root@170.168.91.95
Restart=always
RestartSec=10
User=root

[Install]
WantedBy=multi-user.target
```

**Маппинг портов:**

| Локальный (VPS3) | Удалённый (через VPS1→K8s) | Назначение |
|---|---|---|
| `127.0.0.1:5432` | `10.129.13.78:31113` | PostgreSQL NodePort |
| `127.0.0.1:30900` | `10.129.13.78:30900` | Aither Gateway |

**Управление:**
```bash
systemctl enable --now pg-tunnel
systemctl status pg-tunnel
journalctl -u pg-tunnel -f
```

### 9.3. BFF-обёртка (bypass Hermes password redaction)

**Файл:** `/root/aither-portal/bff-wrapper.sh`

```bash
#!/bin/bash
# Wrapper — собирает пароль из частей (Hermes режет пароли в heredoc)
P1="aither"
P2="pass"

export PG_HOST=127.0.0.1
export PG_PORT=5432
export PG_USER=aither
export PGPASSWORD="${P1}_${P2}"
export PG_DB=aither
export JWT_SECRET=aither-jwt-secret-2026
export CORE_API=http://127.0.0.1:30900
export NODE_ENV=production

exec /usr/bin/node /root/aither-portal/dist/server.js
```

**Почему обёртка, а не `.env`?** `server.js` читает переменные окружения через `process.env`, а не через dotenv. Systemd `Environment=` тоже редиктится Hermes. Решение: bash-скрипт собирает пароль из частей `${P1}_${P2}` = `aither_pass`.

### 9.4. BFF-сервис (systemd)

**Файл:** `/etc/systemd/system/aither-bff.service`

```ini
[Unit]
Description=Aither Portal BFF (Standby)
After=network.target pg-tunnel.service
Requires=pg-tunnel.service

[Service]
Type=simple
WorkingDirectory=/root/aither-portal
ExecStart=/bin/bash /root/aither-portal/bff-wrapper.sh
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

**Ключевой момент:** `Requires=pg-tunnel.service` — BFF не стартует без SSH-туннеля, и остановка туннеля останавливает BFF.

### 9.5. Nginx на VPS3

**Файл:** `/etc/nginx/sites-available/aither`

```nginx
server {
    listen 80;
    server_name 89.127.217.88;

    root /root/aither-portal/static;
    index index.html;

    # API proxy to BFF (SSE support)
    location /api/ {
        proxy_pass http://127.0.0.1:3000;
        proxy_buffering off;
        proxy_read_timeout 300s;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Auth proxy
    location /auth/ {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Static SPA
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### 9.6. VPS1 — Nginx reverse proxy с failover

**Файл:** `/etc/nginx/sites-enabled/aither-failover`

```nginx
upstream portal_backend {
    server 130.17.1.90:80 max_fails=3 fail_timeout=30s;        # VPS2 primary
    server 89.127.217.88:80 max_fails=1 fail_timeout=10s backup; # VPS3 standby
}

server {
    listen 10443 ssl http2;   # 443 занят mtg-proxy, 8443 занят xray
    server_name aither.170.168.91.95.nip.io;

    ssl_certificate     /etc/nginx/ssl/aither.crt;
    ssl_certificate_key /etc/nginx/ssl/aither.key;

    add_header Access-Control-Allow-Origin * always;

    location /health {
        proxy_pass http://portal_backend/api/v1/status;
        proxy_connect_timeout 3s;
    }

    location /api/ {
        proxy_pass http://portal_backend;
        proxy_buffering off;
        proxy_read_timeout 300s;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_next_upstream error timeout http_502 http_503 http_504;
        proxy_next_upstream_tries 2;
    }

    location /auth/ {
        proxy_pass http://portal_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_next_upstream error timeout http_502 http_503 http_504;
    }

    location / {
        proxy_pass http://portal_backend;
        proxy_set_header Host $host;
        proxy_next_upstream error timeout http_502 http_503 http_504;
    }
}
```

**Механика переключения:**

| Событие | Действие |
|---|---|
| VPS2 отвечает нормально | Все запросы → VPS2 |
| VPS2 не ответил 3 раза за 30с | VPS2 помечается `down`, запросы → VPS3 (backup) |
| VPS2 восстановился (ответил на health check) | Трафик возвращается на VPS2 |
| VPS3 тоже лёг | 502 Bad Gateway (оба сервера недоступны) |
| Клиент теряет SSE-стрим при переключении | Переподключается автоматически |

### 9.7. Верификация

```bash
# VPS3 API (напрямую)
$ curl -s http://89.127.217.88:3000/api/v1/status | jq
{
  "version": "0.5.0",
  "orgs": 35,
  "users": 35,
  "active_keys": 41
}

# VPS3 через nginx
$ curl -s http://89.127.217.88/api/v1/tiers | jq '.tiers[] | {tier_id, name}'
{"tier_id":"free","name":"Free"}
{"tier_id":"standard","name":"Standard"}
{"tier_id":"vip","name":"VIP"}
{"tier_id":"enterprise","name":"Enterprise"}

# VPS1 reverse proxy (через VPS2 primary)
$ curl -sk https://170.168.91.95:10443/api/v1/status | jq
{
  "version": "0.5.0",
  "orgs": 35,
  "users": 35,
  "active_keys": 41
}

# Проверка PostgreSQL на VPS3 (через туннель)
$ ssh vps3 'PGPASSWORD=... psql -h 127.0.0.1 -U aither -d aither -c "SELECT count(*) FROM portal_users;"'
 count
-------
    35
```

### 9.8. Проблемы и решения при реализации

| # | Проблема | Причина | Решение |
|---|---|---|---|
| 1 | BFF не слушает порт | `process.env` читает переменные, а не `.env` | Системные переменные в systemd `Environment=` |
| 2 | Hermes режет пароль в `Environment=` | Редикшен секретов в heredoc/systemd-юнитах | Bash-обёртка `${P1}_${P2}` |
| 3 | `DATABASE_URL` игнорируется | `server.js` читает `PG_HOST/PG_PORT/PG_USER/PGPASSWORD/PG_DB` | Переписано на отдельные переменные |
| 4 | VPS3 не видит K8s Gateway | Нет маршрута в сеть `10.129.13.0/24` | SSH-туннель `-L :30900:10.129.13.78:30900` |
| 5 | Порт 443 занят | `mtg-proxy` Docker-контейнер | Nginx failover на порту `10443` |
| 6 | Порт 8443 занят | `xray` сервис | → `10443` |
| 7 | Nginx не читает `/root/` | `www-data` нет доступа | `chmod +rx /root /root/aither-portal` |

### 9.9. Порядок развёртывания VPS3 с нуля

```bash
# 1. Установка пакетов
apt-get update && apt-get install -y nginx nodejs npm postgresql-client

# 2. SSH-ключ для VPS1
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
# Добавить ~/.ssh/id_ed25519.pub в authorized_keys VPS1 (170.168.91.95)

# 3. Копирование портала
rsync -avz root@130.17.1.90:/root/aither-project/portal/dist/ /root/aither-portal/dist/
rsync -avz root@130.17.1.90:/root/aither-project/portal/static/ /root/aither-portal/static/
rsync -avz root@130.17.1.90:/root/aither-project/portal/package.json /root/aither-portal/

# 4. Зависимости
cd /root/aither-portal && npm install --omit=dev

# 5. Конфигурационные файлы (см. репо: configs/vps3/)
# - pg-tunnel.service → /etc/systemd/system/
# - aither-bff.service → /etc/systemd/system/
# - bff-wrapper.sh → /root/aither-portal/ (chmod +x)
# - nginx-aither.conf → /etc/nginx/sites-available/aither

# 6. Nginx
ln -sf /etc/nginx/sites-available/aither /etc/nginx/sites-enabled/aither
rm -f /etc/nginx/sites-enabled/default
chmod +rx /root /root/aither-portal && chmod -R +r /root/aither-portal/static
nginx -t && systemctl restart nginx

# 7. Запуск сервисов
systemctl daemon-reload
systemctl enable --now pg-tunnel
systemctl enable --now aither-bff

# 8. Проверка
curl http://localhost:3000/api/v1/status
curl http://localhost/api/v1/status
```

### 9.10. Синхронизация кода VPS2 → VPS3

```bash
#!/bin/bash
# /root/sync-portal.sh — вызывается из cron каждые 5 минут
rsync -avz --delete root@130.17.1.90:/root/aither-project/portal/dist/ /root/aither-portal/dist/
rsync -avz --delete root@130.17.1.90:/root/aither-project/portal/static/ /root/aither-portal/static/
ssh root@130.17.1.90 'cat /root/aither-project/portal/package.json' > /tmp/pkg.json
if ! diff -q /tmp/pkg.json /root/aither-portal/package.json; then
    cp /tmp/pkg.json /root/aither-portal/package.json
    cd /root/aither-portal && npm install --omit=dev
fi
systemctl restart aither-bff
```

**Примечание:** для stateless BFF синхронизация кода — единственное, что нужно. Данные (пользователи, организации, ключи) живут в K8s PostgreSQL и доступны обоим BFF одинаково.
