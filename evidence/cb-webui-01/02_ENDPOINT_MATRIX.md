# CB-WEBUI-01 — Матрица конечных точек

## Сводная таблица эндпоинтов

| # | Эндпоинт | Зона | Протокол | Назначение | Статус |
|---|----------|------|----------|------------|--------|
| 1 | `https://fb1.spb.ru:443/` | Интернет | HTTPS | Web UI (основной) | ✅ |
| 2 | `https://fb1.spb.ru:443/api/v1` | Интернет | HTTPS | Портал API (BFF) | ✅ |
| 3 | `https://fb1.spb.ru:443/api/v1/chat` | Интернет | HTTPS | Чат с моделями | ✅ |
| 4 | `https://fb1.spb.ru:443/api/v1/auth/login` | Интернет | HTTPS | Аутентификация | ✅ |
| 5 | `https://fb1.spb.ru:443/api/v1/auth/logout` | Интернет | HTTPS | Выход из сессии | ✅ |
| 6 | `https://fb1.spb.ru:443/api/v1/tokens` | Интернет | HTTPS | Управление API-ключами (префикс `athr_`) | ✅ |
| 7 | `https://fb1.spb.ru:443/v1/models` | Интернет | HTTPS | AI Agent — список моделей (GET) | ✅ |
| 8 | `https://fb1.spb.ru:443/v1/chat/completions` | Интернет | HTTPS | AI Agent — чат (POST, OpenAI-совместимый) | ✅ |
| 9 | `https://fb1.spb.ru:443/v1/` | Интернет | HTTPS | AI Platform API (через VPS2 → k8s) | ✅ |
| 10 | `https://fb1.spb.ru:10443/` | Интернет | HTTPS | Web UI (выделенный порт 32B) | ✅ |
| 11 | `https://fb1.spb.ru:10443/v1/` | Интернет | HTTPS | AI Platform 32B API | ✅ |
| 12 | `http://10.129.13.78:30080/` | Тестовая | HTTP | Web UI (NodePort) | ✅ |
| 13 | `http://10.129.13.78:30080/api/v1` | Тестовая | HTTP | Портал API (BFF, NodePort) | ✅ |
| 14 | `http://10.129.13.78:30080/api/v1/chat` | Тестовая | HTTP | Чат с моделями (NodePort) | ✅ |
| 15 | `http://10.129.13.78:30080/api/v1/auth/login` | Тестовая | HTTP | Аутентификация (NodePort) | ✅ |
| 16 | `http://10.129.13.78:30080/api/v1/auth/logout` | Тестовая | HTTP | Выход из сессии (NodePort) | ✅ |
| 17 | `http://10.129.13.78:30080/api/v1/tokens` | Тестовая | HTTP | Управление API-ключами (NodePort) | ✅ |
| 18 | `https://fb1.spb.ru:30901/` | Интернет | HTTPS | ChromaDB/RAG (выделенный порт) | ✅ |

## AI Agent API (OpenAI SDK-совместимый)

| Эндпоинт | Метод | Формат ответа | Назначение |
|----------|-------|---------------|------------|
| `/v1/models` | GET | `{"data": [{"id": "qwen-14b", ...}, {"id": "qwen-32b-base", ...}]}` | Список доступных моделей |
| `/v1/chat/completions` | POST | `{"choices": [{"message": {"content": "..."}}]}` | Чат с моделью (OpenAI-совместимый формат) |

Оба эндпоинта требуют аутентификации (Bearer токен или сессионная cookie).

## Маршрутизация запросов (Интернет-зона)

```
Клиент (Интернет)
    │
    ▼
VPS2 (fb1.spb.ru, nginx)
    │ TLS: Let's Encrypt (автообновление)
    │
    ├── :443 / → 10.129.13.78:30080 (Portal Frontend K8s NodePort)
    ├── :443 /api/ → 10.129.13.78:30080 (Portal BFF)
    ├── :443 /auth/ → 10.129.13.78:30080 (Portal Auth)
    ├── :443 /v1/models → 10.129.13.78:30902 (AI Platform — GET)
    ├── :443 /v1/chat/completions → 10.129.13.78:30902 (AI Platform — POST)
    ├── :443 /v1/ → 10.129.13.78:30902 (AI Platform K8s NodePort)
    ├── :10443 / → 10.129.13.78:30080 (Portal Web UI, 32B)
    ├── :10443 /v1/ → 10.129.13.78:30902 (AI Platform 32B)
    └── :30901 / → 10.129.13.78:30901 (ChromaDB/RAG)
```

## Маршрутизация запросов (Тестовая зона)

```
Клиент (10.129.13.0/24)
    │
    ▼
10.129.13.78:30080 (K8s NodePort)
    │
    └── Pod: aither-portal-frontend (nginx)
        ├── / → /usr/share/nginx/html (статический сайт, 7 страниц)
        ├── /api/ → aither-portal-backend:8000 (BFF)
        ├── /v1/chat/completions → aither-ai-platform:8000
        ├── /v1/models → aither-ai-platform:8000
        └── /health, /ready, /version → aither-portal-backend:8000
```

## Аутентификация

| Метод | Описание |
|-------|----------|
| Сессионная cookie | Устанавливается BFF при входе (`POST /api/v1/auth/login`) |
| Bearer token | Сохраняется в `localStorage` как `aither_token` для справки |
| API-ключ `athr_` | Префикс `athr_` + хеш, используется для программного доступа |
| Проверка сессии | `GET /api/v1/auth/me` — возвращает текущего пользователя |

## Модели

| Модель | ID | Режим | Тип ответа | Доступ через |
|--------|-----|-------|------------|--------------|
| Qwen 14B | `qwen-14b` | Chat completions | Диалоговые ответы на русском | `/v1/chat/completions`, `/api/v1/chat` |
| Qwen 32B Base | `qwen-32b-base` | Text completion | Продолжение текста на русском | `/v1/chat/completions`, `/api/v1/chat` |

## TLS

| Параметр | Значение |
|----------|----------|
| Сертификат | Let's Encrypt |
| Issuer | ISRG Root X2 |
| Валидность | ✅ Валидный |
| Автообновление | ✅ Включено |
| Порты | 443, 10443, 30901 |

## Итого

| Зона | Эндпоинтов | Статус |
|------|-----------|--------|
| Интернет (HTTPS) | 11 | ✅ Все PASS |
| Тестовая (HTTP) | 6 | ✅ Все PASS |
| **Всего** | **18** | ✅ Все PASS |
