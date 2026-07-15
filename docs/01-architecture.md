# Aither Platform — Архитектура (v1.1)

**Дата:** 10.07.2026
**Версия:** v1.1.0 (день 6)

---

## Общая схема

```
┌──────────────────────────────────────────────────────────────────────┐
│                          ПОЛЬЗОВАТЕЛИ                                 │
│  Браузер (портал)              Внешний API-клиент (curl, Python)     │
└─────────────┬──────────────────────────┬─────────────────────────────┘
              │ HTTPS :10443              │ HTTPS :10443
              ▼                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    VPS1 (170.168.91.95)                               │
│  Nginx :10443 (SSL)                                                  │
│  ├── / → VPS2:80 (портал)                                            │
│  ├── /api/ → VPS2:80 (BFF API)                                       │
│  ├── /v1/ → Gateway K8s (модели)                                     │
│  └── /grafana/ → n8:30300                                            │
└─────────────┬────────────────────────────────────────────────────────┘
              │
    ┌─────────┴──────────────────────────────────────────┐
    │                                                     │
    ▼                                                     ▼
┌────────────────────────┐              ┌──────────────────────────────┐
│   VPS2 (130.17.1.90)    │              │   Тестовая зона VLAN 308      │
│   Docker + systemd      │              │   10.129.13.0/24              │
│                         │              │                               │
│  ┌─ portal-nginx-1 ──┐ │              │  ┌─ n8-gpu (.78) ──────────┐ │
│  │ Nginx :80          │ │              │  │ K8s control-plane       │ │
│  │ Статика портала    │ │              │  │ Gateway (ThreadingHTTP) │ │
│  │ /admin.html        │ │              │  │ Redis (rate limiting)   │ │
│  └────────────────────┘ │              │  │ PostgreSQL (billing)    │ │
│                         │              │  │ Prometheus + Grafana    │ │
│  ┌─ aither-bff ──────┐ │              │  └────────────────────────┘ │
│  │ systemd :3000      │ │              │                               │
│  │ Fastify/Node.js     │ │              │  ┌─ n7-gpu (.77) ──────────┐ │
│  │ OAuth + JWT         │ │              │  │ K8s worker              │ │
│  │ LDAP                │ │              │  │ vLLM 14B (:8000)        │ │
│  │ Admin API           │ │              │  │ vLLM 32B (:8001)        │ │
│  └────────────────────┘ │              │  │ vLLM Coder-14B (:8002)  │ │
│                         │              │  └────────────────────────┘ │
│  ┌─ portal-db-1 ─────┐ │              │                               │
│  │ PostgreSQL 16      │ │              │  Сеть: Cisco VPN + Huawei    │
│  │ portal_users       │ │              │  WireGuard-туннели           │
│  │ portal_orgs        │ │              └──────────────────────────────┘
│  │ portal_api_keys    │ │
│  │ portal_settings    │ │
│  │ subscription_tiers │ │
│  │ billing_accounts   │ │
│  └────────────────────┘ │
└────────────────────────┘
```

## Компоненты

| Компонент | Хост | Порт | Технология |
|---|---|---|---|
| Nginx (внешний) | VPS1 | 10443 | SSL, reverse proxy |
| Nginx (статика) | VPS2 Docker | 80 | Раздача SPA + прокси на BFF |
| Portal BFF | VPS2 systemd | 3000 | Node.js/Fastify |
| PostgreSQL | VPS2 Docker | 5432 | portal_users, orgs, keys, billing |
| Gateway | K8s n8 | 30900 | Python/ThreadingHTTPServer |
| Redis | K8s n8 | 6379 | Rate limiting |
| vLLM 14B | K8s n7 | 8000 | Qwen2.5-14B-Instruct |
| vLLM 32B | K8s n7 | 8001 | Qwen2.5-32B-Instruct |
| vLLM Coder | K8s n7 | 8002 | Qwen2.5-Coder-14B |
| Prometheus | K8s n8 | 9090 | Метрики |
| Grafana | K8s n8 | 30300 | Дашборды |

## Схема БД (portal)

| Таблица | Назначение |
|---|---|
| `portal_users` | Пользователи (OAuth/LDAP/email) |
| `portal_organizations` | Организации (имя = `{displayName}-организация`) |
| `portal_org_members` | Связь пользователь ↔ организация (роль) |
| `portal_api_keys` | API-ключи организаций |
| `billing_accounts` | Баланс токенов, резервирование, тариф |
| `subscription_tiers` | Тарифные планы (Free/Standard/VIP/Enterprise) |
| `portal_settings` | Настройки (LDAP и др.) |
| `payment_transactions` | История платежей |
| `portal_org_policies` | Политики безопасности организаций |
| `chats` / `chat_messages` | История чатов |

## Потоки данных

### Чат (streaming)
```
Браузер → VPS1:10443 → VPS2:80 → BFF:3000 → Gateway:30900 → vLLM:800x
                                              ↑ JWT-токен
```

### Админ-панель (11 вкладок)
```
Браузер → VPS1:10443 → VPS2:80 → BFF:3000 → Portal DB (локально)
                                             → Gateway:30900 (Health, Models, Queues, Reaper)
```

### Внешний API
```
Клиент → VPS1:10443/v1/ → Gateway:30900 → vLLM:800x
                           ↑ API-key (X-API-Key header)
```

## Аутентификация

| Метод | Провайдер | Статус |
|---|---|---|
| GitHub OAuth | github.com | ✅ |
| Google OAuth | accounts.google.com | ✅ |
| Яндекс OAuth | oauth.yandex.ru | ✅ |
| LDAP | FreeIPA/ALD Pro | ✅ (настраивается через админку) |
| Email/пароль | portal_users | ✅ |

## Админ-панель

11 вкладок управления платформой. Документация: `docs/03-admin-guide.md`.
