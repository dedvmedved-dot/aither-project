# Security Hardening — Portal (экстренный фикс)

**Дата:** 09.07.2026  
**Инцидент:** Получен отчёт пентеста — 47 пользователей слиты через открытый API  
**Срочность:** Критическая — эксплуатация подтверждена

---

## Карта атаки (реализовано пентестером)

```
GET /api/v1/users (без авторизации)
  → 47 пользователей с email, user_id, oauth_provider
  → Найден admin@dev.local (oauth_provider: "dev")

POST /auth/dev/login {"name":"admin"}
  → JWT-токен с правами owner
  → Полный доступ: orgs, billing, api-keys, chats всех пользователей
```

Вектор: **0-click** — даже регистрация не нужна.

## Выполненные исправления

### 🔴 CRITICAL (эксплуатируемые)

| # | Уязвимость | Фикс |
|---|---|---|
| 1 | `/api/v1/users` без авторизации | `auth(req, reply)` — обязательный JWT |
| 2 | `/auth/dev/login` без пароля | `IS_PRODUCTION` guard → 403 |
| 3 | Внутренний IP в клиентском JS | `window.location.origin` вместо хардкода |

### 🟠 HIGH

| # | Уязвимость | Фикс |
|---|---|---|
| 4 | CORS `origin: *` | `CORS_ORIGIN` из env → `http://130.17.1.90` |
| 5 | Нет security-заголовков | X-Frame-Options, X-Content-Type, X-XSS-Protection, CSP, Referrer-Policy |
| 6 | Порт 3000 в интернет | BFF → `127.0.0.1:3000` (только localhost) |

### 🟡 MEDIUM

| # | Уязвимость | Фикс |
|---|---|---|
| 7 | SHA256 + статическая соль | `scrypt` + `timingSafeEqual` |
| 8 | JWT secret `"dev-jwt-secret-change-me"` | `JWT_SECRET` env (required) |
| 9 | Нет rate limiting | `@fastify/rate-limit`: 100 req/min |
| 10 | IP Gateway в nginx-конфиге | Убран из дефолтов |

## Изменённые файлы

| Файл | Изменения |
|---|---|
| `portal/server.ts` | auth на users, dev-login guard, scrypt, rate limit, CORS origin, 127.0.0.1 bind |
| `portal/static/index.html` | Убран IP Gateway из JS |
| `portal/nginx.conf` | Security headers (CSP, X-Frame, etc.) |
| `portal/package.json` | + `@fastify/rate-limit` |
| `portal/docker-compose.yaml` | `NODE_ENV=production`, `JWT_SECRET`, `CORS_ORIGIN` |

## Результаты верификации

| Тест | Ожидание | Результат |
|---|---|---|
| `/api/v1/users` без токена | 401 | ✅ 401 |
| `/auth/dev/login` в продакшене | 403 | ✅ `"dev login disabled in production"` |
| Порт 3000 извне | Connection refused | ✅ 000 |
| X-Frame-Options | DENY | ✅ |
| CORS origin | `http://130.17.1.90` | ✅ (было `*`) |

## Что НЕ сделано (требует апрува)

- 🔲 **HTTPS** — Let's Encrypt + certbot (нужен домен или nip.io)
- 🔲 **Удаление dev-аккаунтов из БД** — 25 dev-пользователей @dev.local
- 🔲 **API-ключи в хешированном виде** — требуют миграции БД и проверки существующих
- 🔲 **WAF** — Cloudflare или ModSecurity
- 🔲 **HSTS** — после включения HTTPS
