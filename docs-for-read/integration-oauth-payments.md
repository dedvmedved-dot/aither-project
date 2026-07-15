# Интеграция Aither Platform: OAuth-провайдеры и платёжные системы

> Статус: реализовано (OAuth) / проект (платежи)  
> Дата: 7 июля 2026  
> Репозиторий: `aither-project`

---

## Часть 1. OAuth-аутентификация

### 1.1 Зачем это нужно

Портал Aither изначально использовал **dev-логин** — пользователь вводил любое имя и получал доступ. Это подходит только для отладки. В продакшене нужна настоящая идентификация: платформа должна знать, *кто именно* тратит токены, и вести раздельный учёт по организациям.

**OAuth решает эту задачу** — пользователь доказывает свою личность через доверенного провайдера (GitHub, Google, Яндекс), не передавая пароль порталу.

### 1.2 Как работает OAuth (единый паттерн)

Все три провайдера следуют одному протоколу **Authorization Code Grant (PKCE опционально)**:

```
Пользователь         Портал Aither         OAuth-провайдер
    │                     │                      │
    │ 1. ──«Войти через X»──→                    │
    │                     │ 2. ────redirect────→ │ (authorize)
    │ 3. ←───consent screen───────────────────   │
    │ 4. ──«Разрешить»───────────────────────→   │
    │                     │ 5. ←──code─────────  │ (callback)
    │                     │ 6. ──code──────────→ │ (token endpoint)
    │                     │ 7. ←──access_token── │
    │                     │ 8. ──access_token──→ │ (userinfo endpoint)
    │                     │ 9. ←──профиль─────── │
    │                     │                      │
    │                     │ 10. ──генерирует JWT──→ (свой токен)
    │ 11. ←──веб-приложение с JWT──────────────  │
    │                     │                      │
    │ 12. ──API-запросы с JWT────────────────→   │ (авторизован)
```

**Шаги 1–9** — стандартный OAuth 2.0. **Шаг 10** — портал выпускает *свой* JWT, чтобы не ходить к провайдеру при каждом запросе.

### 1.3 GitHub OAuth

#### Регистрация приложения

1. Идём в **Settings → Developer settings → OAuth Apps → New OAuth App**
2. Заполняем:
   - **Application name**: `Aither Platform`
   - **Homepage URL**: `http://130.17.1.90` (или ваш домен)
   - **Authorization callback URL**: `http://130.17.1.90/auth/github/callback`
3. Получаем **Client ID** (публичный) и **Client Secret** (секретный)

#### Код: BFF-эндпоинты (`bff/app.py`)

```python
# Константы
GITHUB_CLIENT_ID = os.environ["GITHUB_CLIENT_ID"]
GITHUB_CLIENT_SECRET = os.environ["GITHUB_CLIENT_SECRET"]
GITHUB_REDIRECT_URI = "http://130.17.1.90/auth/github/callback"

# Шаг 2: редирект на GitHub
@app.get("/auth/github")
async def github_login():
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": GITHUB_REDIRECT_URI,
        "scope": "read:user user:email",
        "state": secrets.token_urlsafe(16),  # защита от CSRF
    }
    url = "https://github.com/login/oauth/authorize?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)

# Шаг 5–10: callback — получаем code → access_token → профиль → JWT
@app.get("/auth/github/callback")
async def github_callback(code: str, state: str):
    # 6–7: обмен code на access_token
    token_resp = await http_client.post(
        "https://github.com/login/oauth/access_token",
        json={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
        },
        headers={"Accept": "application/json"},
    )
    access_token = token_resp.json()["access_token"]

    # 8–9: получаем профиль
    user_resp = await http_client.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    profile = user_resp.json()

    # 10: выпускаем JWT
    jwt_token = create_jwt({
        "sub": f"github:{profile['id']}",
        "name": profile.get("name") or profile["login"],
        "email": profile.get("email"),
        "avatar": profile["avatar_url"],
    })
    return RedirectResponse(f"/?token={jwt_token}")
```

#### Права (scopes)

| Scope | Что даёт |
|---|---|
| `read:user` | Логин, имя, аватар |
| `user:email` | Email (нужен для биллинга) |

#### Фронтенд: кнопка входа

```html
<button onclick="location.href='/auth/github'">
    🐙 Войти через GitHub
</button>
```

---

### 1.4 Google OAuth

#### Регистрация приложения

1. Идём в [Google Cloud Console](https://console.cloud.google.com) → создаём проект
2. **APIs & Services → Credentials → Create Credentials → OAuth client ID**
3. Выбираем **Web application**
4. **Authorized redirect URIs**: `http://130.17.1.90.nip.io/auth/google/callback`

> **Важно**: Google **не принимает IP-адреса** в redirect URI. Используем сервис `nip.io`, который резолвит `130.17.1.90.nip.io` → `130.17.1.90`.

#### Права (scopes)

| Scope | Что даёт |
|---|---|
| `openid` | OpenID Connect (обязательно) |
| `profile` | Имя, фамилия, аватар |
| `email` | Email |

Токены Google — **JWT**, поэтому для получения профиля достаточно декодировать `id_token` без дополнительного запроса к userinfo.

```python
# Google возвращает id_token — JWT, который можно декодировать локально
import jwt

id_token = token_resp.json()["id_token"]
profile = jwt.decode(id_token, options={"verify_signature": False})

jwt_token = create_jwt({
    "sub": f"google:{profile['sub']}",
    "name": profile["name"],
    "email": profile["email"],
    "avatar": profile.get("picture"),
})
```

**Эндпоинты Google**:
- Authorize: `https://accounts.google.com/o/oauth2/v2/auth`
- Token: `https://oauth2.googleapis.com/token`

---

### 1.5 Яндекс OAuth (Яндекс ID)

#### Регистрация приложения

1. Идём в [oauth.yandex.ru](https://oauth.yandex.ru) → **Создать приложение**
2. Платформа: **Веб-сервисы**
3. **Callback URL**: `http://130.17.1.90.nip.io/auth/yandex/callback`
4. Права:
   - `login:email` — email
   - `login:info` — имя, фамилия
   - `login:avatar` — аватар

#### Код

Яндекс использует **POST** на token endpoint (в отличие от GET для GitHub):

```python
YANDEX_CLIENT_ID = os.environ["YANDEX_CLIENT_ID"]
YANDEX_CLIENT_SECRET = os.environ["YANDEX_CLIENT_SECRET"]
YANDEX_REDIRECT_URI = "http://130.17.1.90.nip.io/auth/yandex/callback"

@app.get("/auth/yandex")
async def yandex_login():
    params = {
        "client_id": YANDEX_CLIENT_ID,
        "redirect_uri": YANDEX_REDIRECT_URI,
        "response_type": "code",
    }
    url = "https://oauth.yandex.ru/authorize?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)

@app.get("/auth/yandex/callback")
async def yandex_callback(code: str):
    # Обмен code на access_token (Яндекс требует POST)
    token_resp = await http_client.post(
        "https://oauth.yandex.ru/token",
        data={
            "grant_type": "authorization_code",
            "client_id": YANDEX_CLIENT_ID,
            "client_secret": YANDEX_CLIENT_SECRET,
            "code": code,
        },
    )
    access_token = token_resp.json()["access_token"]

    # Получаем профиль
    user_resp = await http_client.get(
        "https://login.yandex.ru/info?format=json",
        headers={"Authorization": f"OAuth {access_token}"},
    )
    profile = user_resp.json()

    jwt_token = create_jwt({
        "sub": f"yandex:{profile['id']}",
        "name": profile.get("real_name") or profile["display_name"],
        "email": profile.get("default_email"),
        "avatar": f"https://avatars.yandex.net/get-yapic/{profile['default_avatar_id']}/islands-retina",
    })
    return RedirectResponse(f"/?token={jwt_token}")
```

#### Права Яндекса

| Scope | Что даёт |
|---|---|
| `login:email` | Email пользователя |
| `login:info` | Имя, фамилия, пол, страна |
| `login:avatar` | Ссылка на аватар (по умолчанию включено) |

---

### 1.6 Унификация OAuth: единый шаблон

Все три провайдера используют одну и ту же функцию `create_jwt`:

```python
import jwt
import time

JWT_SECRET = os.environ["JWT_SECRET"]  # минимум 256 бит

def create_jwt(claims: dict) -> str:
    payload = {
        **claims,
        "iat": int(time.time()),
        "exp": int(time.time()) + 86400 * 7,  # 7 дней
        "iss": "aither-platform",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")
```

JWT затем сохраняется на фронтенде (`localStorage`) и отправляется в заголовке `Authorization: Bearer <JWT>` при каждом API-запросе.

---

### 1.7 Сравнительная таблица OAuth-провайдеров

| Провайдер | Authorize URL | Token endpoint | Userinfo endpoint | Формат токена | Callback требует домен? |
|---|---|---|---|---|---|
| **GitHub** | `github.com/login/oauth/authorize` | `github.com/login/oauth/access_token` (POST) | `api.github.com/user` (Bearer) | `access_token` | ❌ IP-адрес ОК |
| **Google** | `accounts.google.com/o/oauth2/v2/auth` | `oauth2.googleapis.com/token` (POST) | встроен в `id_token` (JWT) | `id_token` + `access_token` | ✅ Только домен (используем nip.io) |
| **Яндекс** | `oauth.yandex.ru/authorize` | `oauth.yandex.ru/token` (POST) | `login.yandex.ru/info` (OAuth) | `access_token` | ❌ IP-адрес ОК |

---

## Часть 2. Платёжные системы

### 2.1 Модель интеграции

Платёжная система подключается как **внешний сервис** — портал Aither не хранит деньги. Он только управляет **внутренним балансом организации**:

```
Платёжка         Портал Aither (BFF)         БД (billing_accounts)
   │                    │                           │
   │ 1. Пользователь платит на стороне платёжки      │
   │                    │                           │
   │ 2. ────webhook────→│ (уведомление об оплате)    │
   │                    │ 3. ──UPDATE balance─────→ │
   │                    │ 4. ←──OK────────────────  │
   │ 5. ←──200 OK───────│                           │
   │                    │                           │
   │                    │ 6. Пользователь тратит     │
   │                    │    токены через Gateway    │
   │                    │    (reserve → settle)      │
```

Платёжка отвечает только за **приём денег**. Всё остальное — тарификация, учёт токенов, резервирование — делает сама платформа Aither.

### 2.2 Какие платёжные системы можно подключить

#### 🇷🇺 Российские

| Платёжка | Способы приёма | Комиссия | Для кого |
|---|---|---|---|
| **ЮKassa** (Яндекс) | Карты РФ (Visa/MC/Мир), SberPay, СБП, ЮMoney | 3.5% | Самый быстрый старт |
| **CloudPayments** | Карты, рекуррентные платежи | 3.5–4% | Подписки (ежемесячное списание) |
| **Тинькофф Касса** | Карты, интернет-эквайринг | 3.5% | Быстрый онбординг физлиц |
| **Сбербанк** | Карты, счета юрлиц, СБП | 1.5–3% | B2B-клиенты |
| **Робокасса** | Карты, QIWI, ЮMoney, WebMoney, терминалы | 3–5% | Максимальный охват способов |

#### 🌍 Международные

| Платёжка | Для кого | Особенности |
|---|---|---|
| **Stripe** | Не РФ | Карты, подписки, инвойсы — мировой стандарт |
| **Prodamus** | РФ + международные | Альтернатива Stripe для российских юрлиц |

### 2.3 ЮKassa — подробная схема

ЮKassa — лучший выбор для старта. Поддерживает все популярные способы оплаты в РФ.

#### Способы оплаты

| Способ | Как выглядит для пользователя |
|---|---|
| **Банковская карта** | Ввод номера карты в виджете на портале (Mir, Visa, MasterCard) |
| **СБП** | На экране появляется QR-код → пользователь сканирует камерой телефона → подтверждает в приложении банка |
| **SberPay** | Пуш в СберБанк Онлайн → подтверждение одним касанием |
| **ЮMoney** | Кошелёк Яндекса — баланс пополняется мгновенно |
| **T-Pay** | Аналог SberPay для Т-Банка |

#### Схема интеграции

```
                ПОЛЬЗОВАТЕЛЬ
                     │
    ┌────────────────┼────────────────┐
    │                │                │
    ▼                ▼                ▼
┌────────┐    ┌────────────┐    ┌──────────┐
│ Карта   │    │ СБП (QR)   │    │ SberPay  │
└───┬────┘    └─────┬──────┘    └────┬─────┘
    │               │                │
    └───────────────┼────────────────┘
                    │
                    ▼
           ┌────────────────┐
           │   ЮKassa API   │
           │  (yookassa.ru)  │
           └───────┬────────┘
                   │
            webhook (POST)
                   │
                   ▼
           ┌────────────────┐
           │  Портал Aither  │
           │  POST /api/v1/  │
           │  billing/webhook│
           └───────┬────────┘
                   │
                   ▼
           ┌────────────────┐
           │  Billing DB     │
           │  + баланс орг.  │
           └────────────────┘
```

#### Серверный код (BFF)

```python
import hashlib
import hmac

YOOKASSA_SHOP_ID = os.environ["YOOKASSA_SHOP_ID"]
YOOKASSA_SECRET_KEY = os.environ["YOOKASSA_SECRET_KEY"]

@app.post("/api/v1/billing/webhook/yookassa")
async def yookassa_webhook(request: Request):
    body = await request.body()
    
    # Проверка подписи — защита от поддельных уведомлений
    signature = request.headers.get("X-YooKassa-Signature")
    expected = hmac.new(
        YOOKASSA_SECRET_KEY.encode(), body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(400, "Invalid signature")
    
    event = json.loads(body)
    
    # Только успешные платежи
    if event["event"] != "payment.succeeded":
        return {"status": "ignored"}
    
    payment = event["object"]
    amount_rub = float(payment["amount"]["value"])
    description = payment.get("description", "")
    
    # Из description или metadata извлекаем ID организации
    org_id = extract_org_id(description, payment.get("metadata", {}))
    
    # Пополняем баланс: 1 рубль = N токенов
    tokens = rub_to_tokens(amount_rub)
    
    async with db.transaction():
        await db.execute(
            "UPDATE billing_accounts SET balance = balance + $1 WHERE org_id = $2",
            tokens, org_id,
        )
        await db.execute(
            """INSERT INTO billing_transactions 
               (org_id, type, amount_rub, tokens, provider, provider_tx_id) 
               VALUES ($1, 'deposit', $2, $3, 'yookassa', $4)""",
            org_id, amount_rub, tokens, payment["id"],
        )
    
    return {"status": "ok"}
```

#### Фронтенд: форма пополнения

```html
<div class="payment-widget">
    <h3>Пополнение баланса</h3>
    
    <label>Сумма (₽):</label>
    <input type="number" id="amount" min="100" max="100000" value="1000">
    
    <label>Способ оплаты:</label>
    <select id="method">
        <option value="card">💳 Банковская карта</option>
        <option value="sbp">📱 СБП (QR-код)</option>
        <option value="sberpay">🏦 SberPay</option>
    </select>
    
    <button onclick="createPayment()">Оплатить</button>
</div>

<script>
async function createPayment() {
    const amount = document.getElementById('amount').value;
    const method = document.getElementById('method').value;
    const token = localStorage.getItem('aither_token');
    
    // Создаём платёж через BFF → ЮKassa
    const resp = await fetch('/api/v1/billing/create-payment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ amount_rub: Number(amount), method })
    });
    
    const { confirmation_url } = await resp.json();
    
    // Редиректим на страницу оплаты ЮKassa
    window.location.href = confirmation_url;
}
</script>
```

### 2.4 CloudPayments — рекуррентные платежи

Для подписочной модели: пользователь привязывает карту один раз, дальше токены списываются автоматически.

```python
# Привязка карты
@app.post("/api/v1/billing/bind-card")
async def bind_card(token: str):  # токен из CloudPayments Checkout
    resp = await http_client.post(
        "https://api.cloudpayments.ru/payments/cards/charge",
        json={
            "Amount": 1.0,   # 1 рубль для верификации (вернётся)
            "Currency": "RUB",
            "IpAddress": request.client.host,
            "CardCryptogramPacket": token,
        },
        auth=(CLOUDPAYMENTS_PUBLIC_ID, CLOUDPAYMENTS_API_KEY),
    )
    
    if resp.json()["Success"]:
        # Сохраняем токен карты для будущих списаний
        card_token = resp.json()["Model"]["Token"]
        await db.execute(
            "UPDATE orgs SET payment_token = $1 WHERE id = $2",
            card_token, current_org_id,
        )
    return resp.json()
```

### 2.5 Маршрутизация платежей: единый webhook-роутер

Для поддержки нескольких платёжных систем одновременно:

```python
@app.post("/api/v1/billing/webhook/{provider}")
async def billing_webhook(provider: str, request: Request):
    if provider == "yookassa":
        return await yookassa_webhook(request)
    elif provider == "cloudpayments":
        return await cloudpayments_webhook(request)
    elif provider == "stripe":
        return await stripe_webhook(request)
    raise HTTPException(404, f"Unknown provider: {provider}")
```

Все провайдеры пишут в одни и те же таблицы — `billing_accounts` и `billing_transactions`.

### 2.6 Структура БД для платежей

```sql
-- Справочник платёжных провайдеров
CREATE TABLE payment_providers (
    id      TEXT PRIMARY KEY,  -- 'yookassa', 'cloudpayments', 'stripe'
    name    TEXT NOT NULL,
    enabled BOOLEAN DEFAULT true
);

-- Транзакции
CREATE TABLE billing_transactions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID REFERENCES orgs(id),
    type            TEXT NOT NULL,          -- 'deposit', 'refund', 'usage'
    amount_rub      DECIMAL(12,2),          -- сумма в рублях
    tokens          BIGINT,                 -- эквивалент в токенах
    provider        TEXT NOT NULL,          -- 'yookassa', 'cloudpayments', etc.
    provider_tx_id  TEXT,                   -- ID транзакции в платёжной системе
    status          TEXT DEFAULT 'completed',
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Баланс организации (дополняем существующую таблицу)
ALTER TABLE billing_accounts ADD COLUMN payment_token TEXT;  -- для рекуррентов
```

### 2.7 Безопасность платёжных интеграций

| Угроза | Защита |
|---|---|
| Поддельный webhook | HMAC-подпись (ЮKassa: `X-YooKassa-Signature`, Stripe: `Stripe-Signature`) |
| Повторная обработка | Идемпотентность по `provider_tx_id` — UNIQUE constraint в БД |
| MitM при передаче | HTTPS + проверка сертификата |
| Утечка API-ключей | `os.environ`, никогда не коммитить в Git |
| CSRF на создание платежа | JWT в заголовке `Authorization` |

### 2.8 Рекомендации по выбору платёжной системы

```
┌──────────────────────────────────────────────────────────┐
│                    Дерево решений                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Вы работаете с РФ-клиентами?                             │
│  ├── Да ── Нужны подписки?                               │
│  │         ├── Да ── CloudPayments (рекуррентные)        │
│  │         └── Нет ── Нужен максимальный охват?           │
│  │                    ├── Да ── Робокасса                 │
│  │                    └── Нет ── ЮKassa (быстрый старт)   │
│  │                                                       │
│  └── Нет ── Stripe (международный стандарт)              │
│                                                          │
│  B2B-клиенты (юрлица, счета)?                             │
│  └── Сбербанк Бизнес (интернет-эквайринг + счета)        │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Часть 3. Сводная архитектура

```
┌────────────────────────────────────────────────────────────────┐
│                         ПОРТАЛ AITHER                          │
│                                                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                     │
│  │  GitHub  │  │  Google  │  │  Яндекс  │   ← OAuth (вход)    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                     │
│       │              │              │                           │
│       └──────────────┼──────────────┘                           │
│                      │                                          │
│                      ▼                                          │
│              ┌──────────────┐                                   │
│              │   BFF /auth  │  ← JWT-токены                    │
│              └──────┬───────┘                                   │
│                     │                                           │
│                     ▼                                           │
│              ┌──────────────┐     ┌──────────────────┐         │
│              │  Aither API  │────→│  vLLM Gateway    │         │
│              │  (баланс)    │     │  (reserve/settle) │         │
│              └──────┬───────┘     └──────────────────┘         │
│                     │                                           │
│    ┌────────────────┼────────────────┐                          │
│    │                │                │                          │
│    ▼                ▼                ▼                          │
│ ┌────────┐   ┌────────────┐   ┌──────────┐                     │
│ │ЮKassa  │   │CloudPayments│   │  Stripe  │  ← Платежи (ввод)  │
│ └────────┘   └────────────┘   └──────────┘                     │
│                                                                │
│  Все пишут в единую БД:                                        │
│  ┌──────────────────────────────────────────────────────┐     │
│  │  billing_accounts (баланс)                            │     │
│  │  billing_transactions (история: депозиты + списания)  │     │
│  └──────────────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────────────┘
```

---

## Приложение: быстрый старт для разработчика

### 1. OAuth за 5 минут

```bash
# 1. Регистрируем приложения на GitHub, Google, Яндекс (см. разделы выше)

# 2. Кладём ключи в .env (НЕ коммитить!)
cat >> .env << 'EOF'
GITHUB_CLIENT_ID=Ov23li...
GITHUB_CLIENT_SECRET=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
YANDEX_CLIENT_ID=...
YANDEX_CLIENT_SECRET=...
JWT_SECRET=$(openssl rand -hex 32)
EOF

# 3. Проверяем редирект
curl -v http://130.17.1.90/auth/github 2>&1 | grep location
# → https://github.com/login/oauth/authorize?...
```

### 2. ЮKassa за 15 минут

```bash
# 1. Регистрация на yookassa.ru → получаем shopId + секретный ключ

# 2. Добавляем в .env
cat >> .env << 'EOF'
YOOKASSA_SHOP_ID=123456
YOOKASSA_SECRET_KEY=test_...
EOF

# 3. Тестовый платёж через API
curl https://api.yookassa.ru/v3/payments \
  -u "${YOOKASSA_SHOP_ID}:${YOOKASSA_SECRET_KEY}" \
  -H "Idempotence-Key: test-$(date +%s)" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": {"value": "10.00", "currency": "RUB"},
    "confirmation": {"type": "redirect", "return_url": "http://130.17.1.90/"},
    "description": "Тест Aither"
  }'

# 4. Открыть confirmation_url в браузере → оплатить тестовой картой
```
