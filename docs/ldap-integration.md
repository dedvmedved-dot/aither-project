# LDAP-аутентификация — FreeIPA / ALD Pro

**#23a** — интеграция корпоративного LDAP для аутентификации пользователей портала.

## Архитектура

```
POST /auth/ldap { username, password }
  → ldap.ts: authenticateViaLDAP()
    → Шаг 1: bind service account → поиск пользователя по uid/email
    → Шаг 2: bind user DN + password → проверка учётных данных
    → Шаг 3: поиск LDAP-групп → маппинг на роли портала
  → server.ts: upsert portal_users → JWT
```

## Конфигурация (env vars)

| Переменная | Описание | Пример |
|---|---|---|
| `LDAP_URL` | URL LDAP-сервера | `ldap://freeipa.example.com:389` |
| `LDAP_BASE_DN` | Базовый DN домена | `dc=example,dc=com` |
| `LDAP_BIND_DN` | DN сервисной учётной записи | `uid=admin,cn=users,cn=accounts,dc=example,dc=com` |
| `LDAP_BIND_PASSWORD` | Пароль сервисной учётной записи | `changeme` |
| `LDAP_USER_BASE` | DN для поиска пользователей | `cn=users,cn=accounts,dc=example,dc=com` |
| `LDAP_GROUP_BASE` | DN для поиска групп (опционально) | `cn=groups,cn=accounts,dc=example,dc=com` |
| `LDAP_UID_ATTR` | Атрибут логина | `uid` (по умолчанию) |
| `LDAP_MAIL_ATTR` | Атрибут email | `mail` (по умолчанию) |
| `LDAP_NAME_ATTR` | Атрибут отображаемого имени | `displayName` (по умолчанию) |

### FreeIPA (стандартные настройки)

```yaml
LDAP_URL: "ldap://freeipa.example.com:389"
LDAP_BASE_DN: "dc=example,dc=com"
LDAP_BIND_DN: "uid=admin,cn=users,cn=accounts,dc=example,dc=com"
LDAP_BIND_PASSWORD: "password"
LDAP_USER_BASE: "cn=users,cn=accounts,dc=example,dc=com"
LDAP_GROUP_BASE: "cn=groups,cn=accounts,dc=example,dc=com"
```

### ALD Pro (Астра Linux)

```yaml
LDAP_URL: "ldap://ald-pro.example.com:389"
LDAP_BASE_DN: "dc=example,dc=com"
LDAP_BIND_DN: "cn=admin,dc=example,dc=com"
LDAP_USER_BASE: "ou=users,dc=example,dc=com"
```

### Active Directory

```yaml
LDAP_URL: "ldap://ad.example.com:389"
LDAP_BASE_DN: "dc=example,dc=com"
LDAP_BIND_DN: "CN=svc_aither,CN=Users,DC=example,DC=com"
LDAP_UID_ATTR: "sAMAccountName"
LDAP_USER_BASE: "CN=Users,DC=example,DC=com"
```

## Маппинг LDAP-групп → роли портала

| LDAP-группа | Роль портала |
|---|---|
| `aither-admins` | `owner` (полный доступ) |
| `aither-billing` | `billing_admin` |
| `aither-developers` | `developer` |
| Все остальные | `developer` (по умолчанию) |

## API

### POST /auth/ldap

**Запрос:**
```json
{
  "username": "ivanov",
  "password": "secret"
}
```

**Ответ (200):**
```json
{
  "access_token": "eyJhbG...",
  "user": {
    "user_id": "uuid",
    "login": "ivanov",
    "email": "ivanov@example.com"
  },
  "ldap_groups": ["aither-developers", "engineering"],
  "ldap_role": "developer"
}
```

**Ответ (401):**
```json
{ "error": "invalid ldap credentials" }
```

**Ответ (501) — LDAP не настроен:**
```json
{ "error": "LDAP not configured" }
```

## Проверка

```bash
# Без LDAP (LDAP_URL не задан)
curl -X POST http://localhost:3000/auth/ldap \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}'
# → 501 "LDAP not configured"

# С настроенным LDAP
curl -X POST http://localhost:3000/auth/ldap \
  -H "Content-Type: application/json" \
  -d '{"username":"ivanov","password":"correct_password"}'
# → 200 + JWT + ldap_groups
```

## Безопасность

1. **Пароль не хранится** — проверка через LDAP bind, пароль не попадает в БД портала
2. **Сервисная учётка** — отдельная учётная запись с минимальными правами (только search)
3. **Таймаут 5с** — защита от зависания при недоступности LDAP
4. **Экранирование LDAP-фильтра** — защита от LDAP-инъекций через `escapeLDAP()`
5. **Без LDAP_URL эндпоинт возвращает 501** — не создаёт ложных путей атаки
