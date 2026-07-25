# CB-WEBUI-01 — Список изменённых файлов

## Изменённые файлы

| # | Файл | Тип изменения | Описание |
|---|------|---------------|----------|
| 1 | `aither-v2/services/portal-frontend/app.js` | ✏️ Изменён | Полная переработка SPA-логики для CB-WEBUI-01 |
| 2 | `aither-v2/services/portal-frontend/index.html` | ✏️ Изменён | Обновлена разметка страниц, добавлены русские метки |
| 3 | `aither-v2/services/portal-frontend/styles.css` | ✏️ Изменён | Обновлены стили, тёмная тема, стили чата |

## Связанные конфигурационные файлы

| # | Файл | Тип изменения | Описание |
|---|------|---------------|----------|
| 4 | `/root/nginx-failover.conf` | ✏️ Изменён | VPS2 nginx: маршрутизация `/` → k8s NodePort 30080 |
| 5 | K8s ConfigMap `aither-portal-frontend-config` | ✏️ Изменён | Обновлён HTML/CSS/JS контент в ConfigMap |

## Детальный diff

### 1. `app.js` — основные изменения

```
Файл: /root/aither-project/aither-v2/services/portal-frontend/app.js
Размер: 509 строк (было ~430 строк в Stage 15)
```

**Добавлено:**
- Функция автоопределения зоны `detectZone()` (строки 14-21)
- Константы `ZONE`, `ZONE_CLASS` (строки 21-22)
- `credentials: 'same-origin'` в `api()` (строка 32)
- Функция `modal()` для модальных окон (строки 61-68)
- Функция `escHtml()` для XSS-защиты (строки 70-74)
- `updateNav()` с зонным бейджем (строки 76-90)
- Страница чата: `updateModelInfo()`, `addChatMessage()`, `sendChatMessage()`, `clearChat()` (строки 175-304)
- Страница API-ключей: `loadApiKeys()`, `_revokeToken()`, `showCreateTokenModal()`, `_createToken()` (строки 306-410)
- Страница статуса: `loadStatusPage()` с русскими метками (строки 412-436)
- Страница профиля: `loadProfile()` с зоной (строки 438-449)
- `checkSession()` с `loadDashboardInfo()` (строки 452-468)
- Обработчики событий для чата и API-ключей (строки 471-502)

**Удалено (относительно Stage 15):**
- Статический inline JS из ConfigMap заменён на внешний `app.js`
- Английские сообщения заменены на русские
- Упрощённая навигация (4 страницы → 6 страниц)

### 2. `index.html` — основные изменения

```
Файл: /root/aither-project/aither-v2/services/portal-frontend/index.html
Размер: 178 строк
```

**Добавлено:**
- `lang="ru"` в теге `<html>`
- CSS подключается внешним файлом: `<link rel="stylesheet" href="styles.css">`
- JS подключается внешним файлом: `<script src="app.js"></script>`
- Навигация: «Панель», «💬 Чат», «🔑 API Ключи», «Статус», «Профиль», «Выход»
- Зонный бейдж: `<span class="zone-badge" id="zone-badge">`
- Страница чата: `#page-chat` с выбором модели, полем ввода, историей
- Страница API-ключей: `#page-api-keys` с таблицей и кнопкой создания
- Модальное окно: `#modal-overlay` + `#modal-content`
- Русские метки на всех элементах формы

**Удалено:**
- Inline CSS и JS (вынесены в отдельные файлы)
- Английские метки (Dashboard, Profile, System Status)

### 3. `styles.css` — основные изменения

```
Файл: /root/aither-project/aither-v2/services/portal-frontend/styles.css
Размер: 213 строк
```

**Добавлено:**
- CSS-переменные для тёмной темы (строки 2-20)
- Стили для навигации (строки 30-51)
- Стили для чата: `.chat-container`, `.chat-messages`, `.chat-msg`, `.chat-input-row` и др.
- Стили для зонных бейджей: `.zone-badge`, `.zone-internet`, `.zone-test`
- Стили для API-ключей: `.data-table`, `.badge-enabled`, `.badge-revoked`
- Стили для модальных окон: `.modal-overlay`, `.modal-content`
- Стили для кнопок: `.btn-primary`, `.btn-outline`, `.btn-sm`, `.btn-block`
- Стили для алертов: `.alert`, `.alert-danger`, `.alert-success`, `.alert-info`
- Стили для копирования: `.msg-actions`, `.copy-field`

### 4. `/root/nginx-failover.conf` — основные изменения

```
Файл: /root/nginx-failover.conf
Размер: 127 строк
```

**Изменено:**
- Добавлен `location /api/` для проксирования Portal BFF (строки 41-49)
- Добавлен `location /auth/` для проксирования Portal Auth (строки 51-59)
- `location /` маршрутизирует на `http://10.129.13.78:30080` (Portal Web UI) вместо прежнего бэкенда (строки 61-69)
- Серверный блок `:10443` добавлен для выделенного доступа к 32B (строки 72-106)
- Сохранён прокси для AI Platform API (`/v1/` → upstream `ai_platform`)
- Сохранён upstream `ai_platform` для K8s NodePort 30902

### 5. K8s ConfigMap `aither-portal-frontend-config`

```
Ресурс: ConfigMap/aither-portal-frontend-config
Namespace: aither-inference
Применён через: kubectl apply -f services/portal-frontend/k8s/portal-frontend.yaml
```

**Изменено:**
- `index.html` — полная замена с Stage 15 (английский) на CB-WEBUI-01 (русский, 6 страниц)
- `nginx.conf` — маршрутизация API к BFF и AI Platform сохранена

## Статистика

| Метрика | Значение |
|---------|----------|
| Файлов изменено | 5 |
| Файлов создано (evidence) | 13 |
| Добавлено строк кода | ~400 (app.js + index.html + styles.css) |
| Удалено строк кода | ~430 (старый inline HTML) |
| Компонентов затронуто | 3 (Frontend, VPS2 Nginx, K8s ConfigMap) |
