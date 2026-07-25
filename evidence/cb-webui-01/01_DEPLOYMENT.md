# CB-WEBUI-01 — Детали развёртывания

## Обзор

Развёртывание CB-WEBUI-01 затронуло три компонента:
1. **Portal Frontend** (статический сайт: HTML + JS + CSS) — обновление кодовой базы
2. **VPS2 Nginx** (обратный прокси) — перенастройка маршрутизации
3. **K8s ConfigMap** — обновление конфигурации в кластере Kubernetes

## 1. Portal Frontend

### Обновлённые файлы

| Файл | Путь | Описание изменений |
|------|------|--------------------|
| `app.js` | `/root/aither-project/aither-v2/services/portal-frontend/app.js` | Полная переработка SPA-логики (509 строк) |
| `index.html` | `/root/aither-project/aither-v2/services/portal-frontend/index.html` | Обновлена разметка страниц (178 строк) |
| `styles.css` | `/root/aither-project/aither-v2/services/portal-frontend/styles.css` | Обновлены стили для CB-WEBUI-01 (213 строк) |

### Ключевые изменения в `app.js`

```javascript
// Автоопределение зоны подключения
function detectZone() {
    const host = window.location.hostname;
    if (host.includes('10.129') || host.includes('test') || host === 'localhost') {
        return 'TEST ZONE';
    }
    return 'INTERNET';
}
const ZONE = detectZone();
```

- **Аутентификация**: вход через `POST /api/v1/auth/login` с сессионной cookie
- **Чат**: отправка сообщений через `POST /api/v1/chat` с выбором модели
- **API-ключи**: управление через `GET/POST/DELETE /api/v1/tokens` (префикс `athr_`, stable)
- **AI Agent API**: `/v1/models` (GET) + `/v1/chat/completions` (POST, OpenAI-совместимый)
- **Локализация**: все сообщения и интерфейс на русском языке
- **Копирование**: кнопка «📋 Копировать» на ответах ассистента через Clipboard API

### Страницы SPA (7 страниц)

| # | Страница | ID | Назначение |
|---|----------|-----|------------|
| 1 | Вход | `page-login` | Форма аутентификации |
| 2 | Панель | `page-dashboard` | Сводка: пользователь, система, модели |
| 3 | Чат | `page-chat` | Выбор модели + диалог |
| 4 | API Ключи | `page-api-keys` | Создание/отзыв токенов `athr_` |
| 5 | Статус | `page-status` | Состояние системы и версия |
| 6 | Профиль | `page-profile` | Информация о пользователе |
| 7 | Обратная связь | `page-feedback` | Форма обратной связи |

### Выбор модели

```html
<select id="chat-model-select">
    <option value="qwen-14b">qwen-14b (Чат)</option>
    <option value="qwen-32b-base">qwen-32b-base (Базовая)</option>
</select>
```

### AI Agent API (OpenAI SDK-совместимый)

| Эндпоинт | Метод | Назначение |
|----------|-------|------------|
| `/v1/models` | GET | Список доступных моделей |
| `/v1/chat/completions` | POST | Чат с моделями (совместим с OpenAI SDK) |

Оба эндпоинта доступны через VPS2 nginx (порт 443 и 10443) с маршрутизацией на K8s AI Platform (`10.129.13.78:30902`).

## 2. VPS2 Nginx

### Обновлённый файл

| Файл | Путь |
|------|------|
| `nginx-failover.conf` | `/root/nginx-failover.conf` |

### Конфигурация маршрутизации

```
# Порт 443 (основной HTTPS)
server {
    listen 443 ssl;
    server_name fb1.spb.ru;

    # TLS: Let's Encrypt
    ssl_certificate     /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    location /v1/  { proxy_pass http://ai_platform; }         # AI Agent API (models, chat/completions)
    location /api/ { proxy_pass http://10.129.13.78:30080; }  # Portal BFF
    location /auth/{ proxy_pass http://10.129.13.78:30080; }  # Portal Auth
    location /     { proxy_pass http://10.129.13.78:30080; }  # Portal Web UI
}

# Порт 10443 (выделенный для 32B)
server {
    listen 10443 ssl;
    server_name fb1.spb.ru;

    # TLS: Let's Encrypt (тот же сертификат)
    ssl_certificate     /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    location /v1/  { proxy_pass http://ai_platform; }         # AI Agent API (32B)
    location /     { proxy_pass http://10.129.13.78:30080; }  # Portal Web UI
}

# Порт 30901 (ChromaDB/RAG)
server {
    listen 30901 ssl;
    server_name fb1.spb.ru;

    location /     { proxy_pass http://10.129.13.78:30901; }
}
```

### TLS (Let's Encrypt)

| Параметр | Значение |
|----------|----------|
| Сертификат | Let's Encrypt, валидный |
| Issuer | ISRG Root X2 |
| Автообновление | Включено (стандартный механизм Let's Encrypt) |
| Порты с TLS | 443, 10443, 30901 |
| CN | `fb1.spb.ru` |

### Upstream

```
upstream ai_platform {
    server 10.129.13.78:30902;  # K8s NodePort для AI Platform
    keepalive 16;
}
```

## 3. K8s ConfigMap

### Обновлённый ресурс

| Ресурс | Пространство имён | Назначение |
|--------|-------------------|------------|
| `aither-portal-frontend-config` | `aither-inference` | HTML/CSS/JS и nginx.conf для портального фронтенда |

### Структура ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aither-portal-frontend-config
  namespace: aither-inference
  labels:
    app: aither-portal-frontend
    stage: "15"    # Обновлено до CB-WEBUI-01
data:
  index.html: |    # Полный HTML + inline CSS + inline JS
    <!DOCTYPE html>
    ...
  nginx.conf: |    # Конфигурация nginx для подачи статики
    server {
        listen 80;
        ...
    }
```

### Применение ConfigMap

```bash
kubectl apply -f services/portal-frontend/k8s/portal-frontend.yaml
kubectl rollout restart deployment/aither-portal-frontend -n aither-inference
```

После перезапуска пода новый ConfigMap монтируется в `/usr/share/nginx/html` (статический контент) и `/etc/nginx/conf.d` (конфигурация nginx).

## Порядок развёртывания

1. Обновление исходных файлов в репозитории (`app.js`, `index.html`, `styles.css`)
2. Применение обновлённого K8s манифеста (`kubectl apply`)
3. Перезапуск Deployment (`kubectl rollout restart`)
4. Обновление nginx-конфигурации на VPS2 (`/root/nginx-failover.conf`)
5. Перезагрузка nginx на VPS2 (`nginx -s reload`)
6. Проверка доступности через оба endpoint'а
7. Верификация AI Agent API (`/v1/models`, `/v1/chat/completions`)
8. Верификация TLS-сертификата (Let's Encrypt)

## Результаты тестирования развёртывания

| Тип тестов | Количество | Статус |
|------------|------------|--------|
| Unit-тесты | 69 | ✅ PASS |
| Интеграционные тесты | 15 | ✅ PASS |
| Негативные тесты | 8 | ✅ PASS |
| **Всего** | **92** | ✅ PASS |

## Результат

После развёртывания Web UI доступен:
- Через Интернет: `https://fb1.spb.ru:443/`
- В тестовой зоне: `http://10.129.13.78:30080/`
- Выделенный порт 32B: `https://fb1.spb.ru:10443/`
- AI Agent API: `https://fb1.spb.ru:443/v1/models` + `https://fb1.spb.ru:443/v1/chat/completions`
- TLS: Let's Encrypt (валидный, автообновление)
