# CB-WEBUI-01 — Матрица конечных точек

## Сводная таблица эндпоинтов

| # | Эндпоинт | Зона | Протокол | Назначение | Статус |
|---|----------|------|----------|------------|--------|
| 1 | `https://fb1.spb.ru:443/` | Интернет | HTTPS | Web UI (основной) | ✅ |
| 2 | `https://fb1.spb.ru:443/api/v1` | Интернет | HTTPS | Портал API (BFF) | ✅ |
| 3 | `https://fb1.spb.ru:443/api/v1/chat` | Интернет | HTTPS | Чат с моделями | ✅ |
| 4 | `https://fb1.spb.ru:443/api/v1/auth/login` | Интернет | HTTPS | Аутентификация | ✅ |
| 5 | `https://fb1.spb.ru:443/api/v1/auth/logout` | Интернет | HTTPS | Выход из сессии | ✅ |
| 6 | `https://fb1.spb.ru:443/api/v1/tokens` | Интернет | HTTPS | Управление API-ключами | ⚠️ |
| 7 | `https://fb1.spb.ru:443/v1/` | Интернет | HTTPS | AI Platform API (через VPS2 → k8s) | ✅ |
| 8 | `https://fb1.spb.ru:10443/` | Интернет | HTTPS | Web UI (выделенный порт 32B) | ✅ |
| 9 | `https://fb1.spb.ru:10443/v1/` | Интернет | HTTPS | AI Platform 32B API | ✅ |
| 10 | `http://10.129.13.78:30080/` | Тестовая | HTTP | Web UI (NodePort) | ✅ |
| 11 | `http://10.129.13.78:30080/api/v1` | Тестовая | HTTP | Портал API (BFF, NodePort) | ✅ |
| 12 | `http://10.129.13.78:30080/api/v1/chat` | Тестовая | HTTP | Чат с моделями (NodePort) | ✅ |
| 13 | `http://10.129.13.78:30080/api/v1/auth/login` | Тестовая | HTTP | Аутентификация (NodePort) | ✅ |
| 14 | `http://10.129.13.78:30080/api/v1/auth/logout` | Тестовая | HTTP | Выход из сессии (NodePort) | ✅ |
| 15 | `http://10.129.13.78:30080/api/v1/tokens` | Тестовая | HTTP | Управление API-ключами (NodePort) | ⚠️ |
| 16 | `https://fb1.spb.ru:30901/` | Интернет | HTTPS | ChromaDB/RAG (выделенный порт) | ✅ |

## Маршрутизация запросов (Интернет-зона)

```
Клиент (Интернет)
    │
    ▼
VPS2 (fb1.spb.ru, nginx)
    │
    ├── :443 / → 10.129.13.78:30080 (Portal Frontend K8s NodePort)
    ├── :443 /api/ → 10.129.13.78:30080 (Portal BFF)
    ├── :443 /auth/ → 10.129.13.78:30080 (Portal Auth)
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
        ├── / → /usr/share/nginx/html (статический сайт)
        ├── /api/ → aither-portal-backend:8000 (BFF)
        ├── /v1/chat/completions → aither-ai-platform:8000
        └── /health, /ready, /version → aither-portal-backend:8000
```

## Аутентификация

| Метод | Описание |
|-------|----------|
| Сессионная cookie | Устанавливается BFF при входе (`POST /api/v1/auth/login`) |
| Bearer token | Сохраняется в `localStorage` как `aither_token` для справки |
| Проверка сессии | `GET /api/v1/auth/me` — возвращает текущего пользователя |

## Модели

| Модель | ID | Режим | Тип ответа |
|--------|-----|-------|------------|
| Qwen 14B | `qwen-14b` | Chat completions | Диалоговые ответы на русском |
| Qwen 32B Base | `qwen-32b-base` | Text completion | Продолжение текста на русском |
