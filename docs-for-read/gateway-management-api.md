# API Gateway Management API (#39)

**Дата:** 09.07.2026
**Статус:** ✅ Реализовано
**Компоненты:** Gateway (Python), Portal BFF (TypeScript)

---

## Обзор

Management API позволяет администраторам и владельцам организаций управлять и мониторить Gateway: очереди запросов, состояние моделей, drain/undrain, детальную статистику по организациям.

Доступ:
- **Gateway** (`:8080/admin/*`) — через `ADMIN_KEY` из env или JWT с `role=admin`
- **Portal** (`/api/v1/admin/*`) — прокси для org-owner'ов через BFF

---

## Эндпоинты

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| GET | `/admin/queues` | Admin | Активные очереди (RPM/TPM per org) |
| GET | `/admin/models` | Admin | Каталог моделей + health + drain |
| POST | `/admin/models/{name}/drain` | Admin | Отключить модель |
| POST | `/admin/models/{name}/undrain` | Admin | Вернуть модель |
| GET | `/admin/health` | Admin | Полный health-check (Redis, PG, backends, reaper) |
| GET | `/admin/orgs/{org_id}` | Admin | Детальная статистика организации |
| GET | `/admin/reaper` | Admin | Статус Reaper (возврат подвисших резерваций) |

---

### GET /admin/queues

Топ-50 организаций по RPM в текущем минутном окне.

```json
{
  "window": "minute_860937",
  "active_orgs": 12,
  "orgs": [
    {
      "org_id": "uuid",
      "rpm": 45,
      "tpm": 12300,
      "daily": 2340,
      "tier": "standard"
    }
  ]
}
```

### GET /admin/models

```json
{
  "models": [
    {
      "name": "qwen2.5-14b",
      "display_name": "Qwen 2.5 14B",
      "backend": "http://vllm:8000",
      "model_path": "/models/Qwen2.5-14B-Instruct",
      "max_tokens": 4096,
      "status": "active",
      "health": "healthy",
      "drained": false
    }
  ]
}
```

### POST /admin/models/qwen2.5-14b/drain

```json
{
  "model": "qwen2.5-14b",
  "drained": true,
  "drained_models": ["qwen2.5-14b"]
}
```

После drain модель возвращает `503 model_drained` на все запросы.

### GET /admin/health

```json
{
  "status": "ok",
  "timestamp": "2026-07-09T19:30:00Z",
  "components": {
    "redis": {"status": "healthy"},
    "postgresql": {"status": "healthy"},
    "backends": {
      "total": 2,
      "healthy": 2,
      "unhealthy": 0,
      "details": {
        "http://vllm:8000": {"healthy": true, "models": ["qwen2.5-14b"]},
        "http://vllm-32b:8000": {"healthy": true, "models": ["qwen2.5-32b"]}
      }
    },
    "reaper": {
      "last_run": "2026-07-09T19:29:00Z",
      "last_refunded": 0
    }
  }
}
```

---

## Архитектура

```
Portal (BFF) :3000                 Gateway :8080
┌─────────────────────┐           ┌─────────────────┐
│ /api/v1/admin/*     │──proxy──▶│ /admin/*         │
│                     │   +       │                  │
│ Auth: JWT owner     │ ADMIN_KEY │ Auth: ADMIN_KEY  │
│ or X-Admin-Key      │           │ or JWT role=admin│
└─────────────────────┘           └─────────────────┘
```

---

## Файлы

| Файл | Описание |
|---|---|
| `gateway/admin.py` | Модуль: очереди, модели, drain, health, reaper |
| `gateway/gateway.py` | Маршруты `/admin/*`, `_check_admin()`, drain-check в completion flow |
| `portal/server.ts` | Прокси `/api/v1/admin/*` → Gateway |

---

## Переменные окружения

| Переменная | Назначение |
|---|---|
| `ADMIN_KEY` | API-ключ администратора (одинаковый на Gateway и Portal) |

---

## Примеры использования

### Проверить очереди через Portal API
```bash
curl -H "Authorization: Bearer $JWT" \
  http://portal/api/v1/admin/queues
```

### Drain модели
```bash
curl -X POST -H "Authorization: Bearer $ADMIN_KEY" \
  http://gateway:8080/admin/models/qwen2.5-14b/drain
```

### Полный health-check
```bash
curl -H "Authorization: Bearer $ADMIN_KEY" \
  http://gateway:8080/admin/health
```

---

## Следующие шаги

- 🔲 Admin UI в портале (дашборд очередей, кнопки drain/undrain)
- 🔲 Автоматический drain при health-check failure
- 🔲 WebSocket для real-time мониторинга очередей
