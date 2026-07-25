# Руководство администратора Web UI платформы Aither

**Версия документа:** 1.0  
**Дата:** 2026-07-26  
**Целевая версия платформы:** CB-WEBUI-01 / Stage 18B  
**Пространство имён K8s:** `aither-inference`  
**Язык:** Русский

---

## Содержание

1. [Обзор системы](#1-обзор-системы)
2. [Компоненты Web UI](#2-компоненты-web-ui)
3. [Зависимости](#3-зависимости)
4. [Конфигурация двух моделей](#4-конфигурация-двух-моделей)
5. [Настройка зон доступа (Internet / Test Zone)](#5-настройка-зон-доступа-internet--test-zone)
6. [Процедуры запуска, остановки и перезапуска](#6-процедуры-запуска-остановки-и-перезапуска)
7. [Проверки работоспособности (Health Checks)](#7-проверки-работоспособности-health-checks)
8. [Расположение журналов (логов)](#8-расположение-журналов-логов)
9. [Мониторинг](#9-мониторинг)
10. [Диагностика пользователей и сессий](#10-диагностика-пользователей-и-сессий)
11. [Диагностика ключей (без раскрытия секретов)](#11-диагностика-ключей-без-раскрытия-секретов)
12. [Диагностика маршрутизации моделей](#12-диагностика-маршрутизации-моделей)
13. [Диагностика Agent API](#13-диагностика-agent-api)
14. [Резервное копирование](#14-резервное-копирование)
15. [Восстановление](#15-восстановление)
16. [Откат (Rollback)](#16-откат-rollback)
17. [Типовые отказы и их устранение](#17-типовые-отказы-и-их-устранение)
18. [Безопасная процедура обновления](#18-безопасная-процедура-обновления)
19. [Верификация после обновления](#19-верификация-после-обновления)

---

## 1. Обзор системы

Платформа Aither предоставляет единый Web-интерфейс (SPA), доступный одновременно из двух сетевых зон:

- **Internet** — публичный доступ через HTTPS (домен `fb1.spb.ru`, порт 443)
- **Test Zone** — внутренний доступ через K8s NodePort (`10.129.13.78:30080`)

Web UI обеспечивает: аутентификацию, чат с моделями, управление API-ключами, мониторинг состояния системы и Agent API (OpenAI-совместимый).

### Стек технологий

| Компонент | Технология |
|-----------|-----------|
| Фронтенд (SPA) | Vanilla JS + HTML5 + CSS3, обслуживается nginx внутри K8s-пода |
| BFF (Backend-for-Frontend) | Fastify 4.x (Node.js/TypeScript), порт 3000 |
| База данных | PostgreSQL 16 (Alpine) |
| Rate limiting | Redis (через `@fastify/rate-limit`) |
| Инференс моделей | vLLM (GPU-сервер) |
| Обратный прокси (Internet) | nginx на VPS2 (Let's Encrypt TLS) |
| Оркестрация | Kubernetes, namespace `aither-inference` |
| Контейнерный реестр | Локальный Docker Registry (`10.129.13.78:5000`) |

---

## 2. Компоненты Web UI

### 2.1. Portal Frontend (K8s Deployment)

- **Deployment:** `aither-portal-frontend`
- **Образ:** `nginx:stable-alpine`
- **Порт:** 80 (ClusterIP)
- **NodePort:** 30080
- **ConfigMap:** `aither-portal-frontend-config` (содержит `index.html` и `nginx.conf`)
- **Страницы SPA (7):** Вход, Панель, Чат, API Ключи, Статус, Профиль, Обратная связь

```yaml
# K8s манифест
# /root/aither-project/aither-v2/services/portal-frontend/k8s/portal-frontend.yaml
```

**Probes:**
- Liveness: `GET /` на порт 80 (initialDelay: 10s, period: 15s)
- Readiness: `GET /` на порт 80 (initialDelay: 5s, period: 10s)

### 2.2. Portal Backend (BFF) — K8s Deployment

- **Deployment:** `aither-portal-backend`
- **Образ:** `10.129.13.78:5000/aither-portal-backend:stage18a-82fe433`
- **Порт:** 8000 (ClusterIP)
- **Service:** `aither-portal-backend`

**Переменные окружения:**

| Переменная | Назначение |
|-----------|-----------|
| `PORTAL_IDENTITY_URL` | URL Identity-сервиса |
| `PORTAL_AI_PLATFORM_URL` | URL AI Platform (vLLM) |
| `PORTAL_LOG_LEVEL` | Уровень логирования (по умолчанию `INFO`) |
| `PORTAL_CORS_ORIGIN` | Разрешённый CORS-источник |

**Probes:**
- Liveness: `GET /health` на порт 8000 (initialDelay: 10s, period: 15s)
- Readiness: `GET /ready` на порт 8000 (initialDelay: 5s, period: 10s)

### 2.3. BFF-сервер (основной процесс Node.js)

Код сервера: `/root/aither-project/portal/server.ts`

Версия: **v0.6.0** (security-hardened)

Порт: **3000** (в production слушает `127.0.0.1`, в dev — `0.0.0.0`)

Ключевые модули:
- `api-gateway.ts` — OpenAI-совместимый внешний API (`/api/v1/models`, `/api/v1/chat/completions`)
- `policies.ts` — политики безопасности организаций (DLP, jailbreak-детекция, лимиты)
- `ldap.ts` — интеграция с LDAP (FreeIPA / ALD Pro / OpenLDAP)

### 2.4. VPS2 nginx (обратный прокси)

Конфигурация: `/root/nginx-failover.conf`

Маршрутизация:

```
Порт 443 (основной HTTPS):
  /v1/*     → K8s AI Platform (10.129.13.78:30902)
  /api/*    → K8s Portal BFF (10.129.13.78:30080)
  /auth/*   → K8s Portal BFF
  /*        → K8s Portal Frontend (10.129.13.78:30080)

Порт 10443 (выделенный 32B):
  /v1/*     → K8s AI Platform
  /*        → K8s Portal Frontend

Порт 30901 (ChromaDB/RAG):
  /*        → K8s ChromaDB (10.129.13.78:30901)
```

TLS: Let's Encrypt, автообновление, сертификаты в `/etc/nginx/ssl/`.

---

## 3. Зависимости

### 3.1. NPM-зависимости BFF (portal/server.ts)

```json
{
  "dependencies": {
    "fastify": "^4.28.0",
    "@fastify/cors": "^9.0.0",
    "@fastify/rate-limit": "^9.1.0",
    "jsonwebtoken": "^9.0.0",
    "ldapjs": "^3.0.7",
    "pg": "^8.12.0"
  }
}
```

### 3.2. Инфраструктурные зависимости

| Сервис | Версия | Роль |
|--------|--------|------|
| PostgreSQL | 16-alpine | Хранение пользователей, организаций, API-ключей, чатов, биллинга |
| Redis | — | Rate limiting (100 запросов/мин на IP) |
| nginx | 1.27-alpine (VPS2), stable-alpine (K8s pod) | Статика + обратный прокси |
| vLLM | — | Инференс LLM-моделей |
| K8s | — | Оркестрация (namespace `aither-inference`) |

### 3.3. Внешние сервисы

| Сервис | Назначение | Конфигурация |
|--------|-----------|-------------|
| GitHub OAuth | OAuth-аутентификация | `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` |
| Google OAuth | OAuth-аутентификация | `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` |
| Yandex OAuth | OAuth-аутентификация | `YANDEX_CLIENT_ID` / `YANDEX_CLIENT_SECRET` |
| YooKassa | Платёжная система | `YOOKASSA_SHOP_ID` / `YOOKASSA_SECRET` |
| Let's Encrypt | TLS-сертификаты | Автоматическое обновление |

---

## 4. Конфигурация двух моделей

### 4.1. Карта моделей (MODEL_MAP)

Определена в `server.ts` и `api-gateway.ts`:

```typescript
const MODEL_MAP = {
  "qwen2.5-14b": {
    display_name: "Qwen 2.5 14B",
    vllm_path: "/models/Qwen2.5-14B-Instruct",
    description: "Быстрая универсальная модель",
  },
  "qwen2.5-32b": {
    display_name: "Qwen 2.5 32B",
    vllm_path: "/models/Qwen2.5-32B-Instruct-GPTQ",
    description: "Мощная модель для сложных задач",
  },
};
```

### 4.2. Характеристики моделей

| Параметр | qwen-14b | qwen-32b-base |
|----------|----------|---------------|
| ID в Web UI | `qwen-14b` | `qwen-32b-base` |
| ID в API | `qwen2.5-14b` | `qwen2.5-32b` |
| Режим | Chat completions (диалог) | Text completion (продолжение) |
| vLLM-путь | `/models/Qwen2.5-14B-Instruct` | `/models/Qwen2.5-32B-Instruct-GPTQ` |
| Max tokens | 4096 | 8192 |
| Скорость ответа | ~4 сек | ~5 сек |
| Язык | Русский | Русский |

### 4.3. Scope-модель прав доступа

API-ключи ограничиваются scope'ами:

| Scope | Модель | Тип доступа |
|-------|--------|-------------|
| `model:14b:chat` | qwen-14b | Диалоговый чат |
| `model:32b:chat-adapter` | qwen-32b | Чат-адаптер |
| `model:32b:completion` | qwen-32b | Completion (продолжение текста) |

---

## 5. Настройка зон доступа (Internet / Test Zone)

### 5.1. Internet-зона

**URL:** `https://fb1.spb.ru:443/`

**Схема маршрутизации:**
```
Клиент (Интернет)
  → VPS2 nginx :443 (HTTPS, TLS-termination)
    → 10.129.13.78:30080 (K8s NodePort, Portal Frontend)
    → 10.129.13.78:30902 (K8s NodePort, AI Platform — /v1/*)
```

**Настройка TLS:** Let's Encrypt, автообновление.

**Проверка TLS:**
```bash
curl -I https://fb1.spb.ru:443/
openssl s_client -connect fb1.spb.ru:443 -servername fb1.spb.ru </dev/null 2>/dev/null | openssl x509 -noout -dates
```

### 5.2. Test Zone

**URL:** `http://10.129.13.78:30080/`

**Схема доступа:**
```
Клиент (внутренняя сеть 10.129.13.0/24 или VPN)
  → 10.129.13.78:30080 (K8s NodePort)
    → Pod aither-portal-frontend (nginx)
      → /api/* → BFF (Fastify :3000)
      → /*     → SPA (статика)
```

### 5.3. Автоопределение зоны

Фронтенд автоматически определяет зону по hostname:

```javascript
function detectZone() {
    const host = window.location.hostname;
    if (host.includes('10.129') || host.includes('test') || host === 'localhost') {
        return 'TEST ZONE';
    }
    return 'INTERNET';
}
```

### 5.4. Проверка доступности зон

```bash
# Internet-зона
curl -sk -o /dev/null -w "%{http_code}" https://fb1.spb.ru:443/
# Ожидаемый ответ: 200

# Test Zone
curl -s -o /dev/null -w "%{http_code}" http://10.129.13.78:30080/
# Ожидаемый ответ: 200
```

### 5.5. Дополнительные порты (Internet)

| Порт | Назначение |
|------|-----------|
| `:443` | Основной Web UI + API |
| `:10443` | Выделенный порт 32B |
| `:30901` | ChromaDB/RAG |

---

## 6. Процедуры запуска, остановки и перезапуска

### 6.1. Запуск всех компонентов

```bash
# 1. Проверить, что кластер K8s работает
kubectl cluster-info
kubectl get nodes
# Ожидается: оба узла Ready

# 2. Проверить реестр образов
ssh root@n8 "curl -fsS http://localhost:5000/v2/_catalog"
# Ожидается: 3+ репозитория (aither-identity, aither-portal-backend, aither-ai-platform)

# 3. Применить манифесты
kubectl apply -f /root/aither-project/aither-v2/services/portal-frontend/k8s/portal-frontend.yaml
kubectl apply -f /root/aither-project/aither-v2/services/portal-backend/k8s/portal-backend.yaml

# 4. Дождаться готовности
kubectl rollout status deploy/aither-portal-frontend -n aither-inference --timeout=120s
kubectl rollout status deploy/aither-portal-backend -n aither-inference --timeout=120s

# 5. Запустить nginx на VPS2 (если остановлен)
docker start aither-failover-nginx
# или
docker run -d --name aither-failover-nginx \
  --network host \
  -v /root/nginx-failover.conf:/etc/nginx/conf.d/default.conf:ro \
  -v /etc/nginx/ssl:/etc/nginx/ssl:ro \
  nginx:1.27-alpine
```

### 6.2. Остановка

```bash
# Остановка K8s-компонентов (масштабирование до 0)
kubectl scale deploy/aither-portal-frontend -n aither-inference --replicas=0
kubectl scale deploy/aither-portal-backend -n aither-inference --replicas=0

# Остановка VPS2 nginx
docker stop aither-failover-nginx
```

### 6.3. Перезапуск

```bash
# Перезапуск K8s-подов (rolling restart)
kubectl rollout restart deploy/aither-portal-frontend -n aither-inference
kubectl rollout restart deploy/aither-portal-backend -n aither-inference

# Дождаться готовности
kubectl rollout status deploy/aither-portal-frontend -n aither-inference --timeout=120s
kubectl rollout status deploy/aither-portal-backend -n aither-inference --timeout=120s

# Перезагрузка VPS2 nginx (без даунтайма)
docker exec aither-failover-nginx nginx -t   # проверить конфигурацию
docker exec aither-failover-nginx nginx -s reload
```

### 6.4. Проверка статуса после перезапуска

```bash
kubectl get pods -n aither-inference -o wide
# Ожидается: все поды Running

kubectl get deployments -n aither-inference
# Ожидается: все AVAILABLE = 1

curl -s http://10.129.13.78:30080/health
# Ожидается: {"status":"ok","service":"portal-bff","database":"connected"}
```

---

## 7. Проверки работоспособности (Health Checks)

### 7.1. Health Check BFF

**Эндпоинт:** `GET /health`

```bash
# Через Internet
curl -s https://fb1.spb.ru:443/health | python3 -m json.tool

# Через Test Zone
curl -s http://10.129.13.78:30080/health | python3 -m json.tool
```

**Ожидаемый ответ:**
```json
{
  "status": "ok",
  "service": "portal-bff",
  "database": "connected"
}
```

Поле `database`:
- `"connected"` — PostgreSQL доступен
- `"error"` — база данных недоступна (проверить `kubectl get pods -n aither-inference | grep postgres`)

### 7.2. Health Check AI Platform (Core)

**Эндпоинт:** `GET /api/v1/core/status`

```bash
curl -s https://fb1.spb.ru:443/api/v1/core/status | python3 -m json.tool
```

**Ожидаемый ответ:**
```json
{
  "status": "ok",
  "model": "vLLM"
}
```

При ошибке:
```json
{
  "status": "unreachable",
  "error": "core_unreachable"
}
```

### 7.3. K8s Health Probes

```bash
# Проверить состояние проб
kubectl describe pod -n aither-inference -l app=aither-portal-frontend | grep -A5 "Liveness\|Readiness"
kubectl describe pod -n aither-inference -l app=aither-portal-backend | grep -A5 "Liveness\|Readiness"
```

### 7.4. Скрипт комплексной проверки

```bash
#!/bin/bash
# Полная проверка здоровья системы

echo "=== Portal Frontend ==="
HTTP=$(curl -sk -o /dev/null -w "%{http_code}" https://fb1.spb.ru:443/)
echo "Internet (443): $HTTP"

HTTP=$(curl -s -o /dev/null -w "%{http_code}" http://10.129.13.78:30080/)
echo "Test Zone (30080): $HTTP"

echo ""
echo "=== Portal BFF Health ==="
curl -s http://10.129.13.78:30080/health | python3 -m json.tool

echo ""
echo "=== AI Platform Status ==="
curl -s http://10.129.13.78:30080/api/v1/core/status | python3 -m json.tool

echo ""
echo "=== K8s Pods ==="
kubectl get pods -n aither-inference -o wide

echo ""
echo "=== K8s Deployments ==="
kubectl get deployments -n aither-inference
```

---

## 8. Расположение журналов (логов)

### 8.1. Логи BFF (Portal Backend)

BFF пишет в stdout/stderr. Доступ через kubectl:

```bash
# Текущие логи
kubectl logs -n aither-inference deploy/aither-portal-backend

# Логи с временной меткой
kubectl logs -n aither-inference deploy/aither-portal-backend --timestamps

# Последние 100 строк
kubectl logs -n aither-inference deploy/aither-portal-backend --tail=100

# Потоковая трансляция (follow)
kubectl logs -n aither-inference deploy/aither-portal-backend -f

# Логи за последний час
kubectl logs -n aither-inference deploy/aither-portal-backend --since=1h
```

### 8.2. Логи Portal Frontend (nginx)

```bash
kubectl logs -n aither-inference deploy/aither-portal-frontend --tail=100
```

### 8.3. Логи VPS2 nginx

```bash
docker logs aither-failover-nginx --tail=100
docker logs aither-failover-nginx -f   # follow
```

Логи доступа nginx обычно в `/var/log/nginx/access.log` (внутри контейнера или на хосте).

### 8.4. Уровень логирования

BFF: переменная окружения `PORTAL_LOG_LEVEL` (значения: `DEBUG`, `INFO`, `WARN`, `ERROR`).

Для временного повышения детализации:
```bash
kubectl set env deploy/aither-portal-backend -n aither-inference PORTAL_LOG_LEVEL=DEBUG
kubectl rollout status deploy/aither-portal-backend -n aither-inference --timeout=60s
```

Возврат к `INFO`:
```bash
kubectl set env deploy/aither-portal-backend -n aither-inference PORTAL_LOG_LEVEL=INFO
```

---

## 9. Мониторинг

### 9.1. Prometheus Alert Rules

Файл: `/root/aither-project/aither-v2/docs/stage17/prometheus/alert-rules.yaml`

**Критические алерты:**

| Алерт | Условие | Порог |
|-------|---------|-------|
| `ServiceDown` | `up == 0` для identity/portal-backend/ai-platform/gateway | 1 мин |
| `ReadinessCheckFailed` | `probe_success == 0` | 30 сек |
| `GatewayUnavailable` | Ошибки Gateway > 10/сек | 2 мин |

**Предупреждения:**

| Алерт | Условие | Порог |
|-------|---------|-------|
| `HighErrorRate` | HTTP 5xx > 5% | 5 мин |
| `HighLatency` | P95 latency > 5 сек | 5 мин |
| `PVCLowSpace` | PVC заполнен > 85% | 5 мин |
| `HighMemoryUsage` | Память > 500 MB | 5 мин |

### 9.2. Grafana Dashboards

Файлы дашбордов: `/root/aither-project/aither-v2/docs/stage17/grafana/`

| Дашборд | Файл | Назначение |
|---------|------|-----------|
| System Overview | `dashboard-system-overview.json` | Общее состояние системы |
| Gateway | `dashboard-gateway.json` | Метрики nginx-шлюза |
| AI Platform | `dashboard-ai-platform.json` | Состояние vLLM-инференса |
| Identity | `dashboard-identity.json` | Аутентификация и сессии |
| Portal | `dashboard-portal.json` | Web UI и BFF |

Дополнительно:
- `gpu-overview.json` — утилизация GPU
- `vllm-inference.json` — метрики вывода моделей

### 9.3. Быстрая проверка метрик вручную

```bash
# Статус API через BFF
curl -s http://10.129.13.78:30080/api/v1/status | python3 -m json.tool

# Количество подов
kubectl get pods -n aither-inference --no-headers | wc -l

# Использование ресурсов подами
kubectl top pods -n aither-inference

# Использование ресурсов узлами
kubectl top nodes
```

---

## 10. Диагностика пользователей и сессий

### 10.1. Информация о текущем пользователе

```bash
# Через API (требуется JWT-токен)
curl -s http://10.129.13.78:30080/api/v1/me \
  -H "Authorization: Bearer <JWT_TOKEN>" | python3 -m json.tool
```

Ответ:
```json
{
  "user": {
    "user_id": "uuid",
    "display_name": "Имя",
    "email": "email@domain",
    "avatar_url": "...",
    "oauth_provider": "github|google|yandex|ldap|email",
    "created_at": "2026-..."
  }
}
```

### 10.2. Список пользователей

```bash
curl -s http://10.129.13.78:30080/api/v1/users \
  -H "Authorization: Bearer <JWT_TOKEN>" | python3 -m json.tool
```

### 10.3. Диагностика через PostgreSQL

Подключение к БД:

```bash
# Найти под PostgreSQL
kubectl get pods -n aither-inference -l app=postgres

# Подключиться
kubectl exec -n aither-inference -it <postgres-pod> -- psql -U portal -d portal
```

Диагностические SQL-запросы:

```sql
-- Количество пользователей
SELECT count(*) FROM portal_users;

-- Последние входы (10 последних)
SELECT user_id, display_name, oauth_provider, last_login_at
FROM portal_users
ORDER BY last_login_at DESC NULLS LAST
LIMIT 10;

-- Активные организации
SELECT org_id, name, status, created_at
FROM portal_organizations
WHERE status = 'active'
ORDER BY created_at DESC;

-- Количество активных API-ключей
SELECT count(*) FROM portal_api_keys WHERE status = 'active';

-- Ключи, не использовавшиеся > 30 дней
SELECT key_id, name, created_at, last_used_at
FROM portal_api_keys
WHERE status = 'active'
  AND (last_used_at IS NULL OR last_used_at < now() - interval '30 days')
ORDER BY created_at DESC;

-- Количество чатов
SELECT count(*) FROM chats;

-- Количество сообщений
SELECT count(*) FROM chat_messages;
```

### 10.4. Диагностика зависших сессий

Сессии управляются через JWT-токены (срок действия 24 часа). При проблемах:

```bash
# Проверить валидность токена (декодировать без проверки подписи)
echo "<JWT_TOKEN>" | cut -d'.' -f2 | base64 -d 2>/dev/null | python3 -m json.tool
```

---

## 11. Диагностика ключей (без раскрытия секретов)

### 11.1. Структура ключа

- **API-ключ:** `ak-<hex>` (формат Agent API) или `athr_<urlsafe_base64>` (формат UI-токенов)
- **Префикс:** первые 11–12 символов ключа — безопасно показывать в UI и логах
- **Хеш:** полный ключ не хранится в БД (только хеш, если реализовано)
- **token_id:** 12 hex-символов (`secrets.token_hex(6)`) — **не секрет**, используется как первичный ключ БД

### 11.2. Просмотр ключей организации (без раскрытия полных ключей)

```bash
# Через BFF API
curl -s http://10.129.13.78:30080/api/v1/orgs/<ORG_ID>/api-keys \
  -H "Authorization: Bearer <JWT_TOKEN>" | python3 -m json.tool
```

Ответ содержит только префиксы и метаданные, **не** полные ключи.

### 11.3. Диагностика через БД (только метаданные)

```sql
-- Количество ключей по статусу
SELECT status, count(*) FROM portal_api_keys GROUP BY status;

-- Ключи по организациям
SELECT o.name, count(k.key_id) as key_count
FROM portal_organizations o
LEFT JOIN portal_api_keys k ON o.org_id = k.org_id AND k.status = 'active'
GROUP BY o.name
ORDER BY key_count DESC;

-- Недавно использованные ключи (только префикс и метаданные)
SELECT key_id, api_key_prefix, name, status, created_at, last_used_at
FROM portal_api_keys
WHERE last_used_at IS NOT NULL
ORDER BY last_used_at DESC
LIMIT 10;
```

### 11.4. Проверка безопасности

```bash
# Убедиться, что приватные ключи не в репозитории
cd /root/aither-project
git ls-files '*.pem' '*.key' '*private*' '*secret*'
# Ожидается: пустой вывод (или только .example файлы)

# Убедиться, что секреты в K8s Secrets, а не в ConfigMap
kubectl get secrets -n aither-inference
kubectl describe configmap -n aither-inference | grep -i secret
# Ожидается: нет секретов в ConfigMap
```

---

## 12. Диагностика маршрутизации моделей

### 12.1. Проверка доступности моделей

```bash
# Список моделей (публичный, без аутентификации)
curl -s https://fb1.spb.ru:443/api/v1/models | python3 -m json.tool
```

Ожидаемый ответ:
```json
{
  "object": "list",
  "data": [
    {
      "id": "qwen2.5-14b",
      "object": "model",
      "owned_by": "aither",
      "display_name": "Qwen 2.5 14B",
      "description": "Быстрая универсальная модель",
      "max_tokens": 4096
    },
    {
      "id": "qwen2.5-32b",
      "object": "model",
      "owned_by": "aither",
      "display_name": "Qwen 2.5 32B",
      "description": "Мощная модель для сложных задач",
      "max_tokens": 8192
    }
  ]
}
```

### 12.2. Тестовый вызов vLLM напрямую

```bash
# Проверка 14B через AI Platform (K8s NodePort)
curl -s -X POST http://10.129.13.78:30902/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "/models/Qwen2.5-14B-Instruct",
    "messages": [{"role": "user", "content": "Тест связи"}],
    "max_tokens": 10
  }' | python3 -m json.tool

# Проверка 32B
curl -s -X POST http://10.129.13.78:30902/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "/models/Qwen2.5-32B-Instruct-GPTQ",
    "messages": [{"role": "user", "content": "Тест связи"}],
    "max_tokens": 10
  }' | python3 -m json.tool
```

### 12.3. Трассировка маршрута запроса

```
Запрос → VPS2 nginx :443 → /v1/ → 10.129.13.78:30902 (AI Platform)
                              → /api/ → 10.129.13.78:30080 (Portal Frontend → BFF)
                                                → BFF: CORE_API + "/v1/chat/completions"
                                                       → 10.129.13.78:30902 (vLLM)
```

### 12.4. Диагностика проблем маршрутизации

```bash
# 1. Проверить, что nginx на VPS2 работает
docker ps | grep aither-failover-nginx

# 2. Проверить конфигурацию nginx
docker exec aither-failover-nginx nginx -t

# 3. Проверить доступность NodePort'ов
curl -s -o /dev/null -w "%{http_code}" http://10.129.13.78:30080/
curl -s -o /dev/null -w "%{http_code}" http://10.129.13.78:30902/health

# 4. Проверить логи nginx при ошибках
docker logs aither-failover-nginx --tail=50 | grep -i error
```

---

## 13. Диагностика Agent API

### 13.1. Endpoint'ы Agent API

Agent API — OpenAI-совместимый интерфейс для программных агентов:

| Метод | Эндпоинт | Аутентификация | Назначение |
|-------|----------|---------------|------------|
| `GET` | `/api/v1/models` | Без аутентификации | Список доступных моделей |
| `POST` | `/api/v1/chat/completions` | `Bearer ak-...` | Чат-завершение |
| `GET` | `/api/v1/health` | Без аутентификации | Проверка здоровья API |

**Формат ключа:** `ak-<hex>` (префикс `ak-`).

### 13.2. Тестовый вызов Agent API

```bash
# 1. Создать API-ключ через BFF (получить JWT-токен администратора)
TOKEN="<JWT_TOKEN>"
ORG_ID="<ORG_ID>"
KEY_RESP=$(curl -s -X POST http://10.129.13.78:30080/api/v1/orgs/$ORG_ID/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "diag-test"}')
API_KEY=$(echo $KEY_RESP | python3 -c "import sys,json; print(json.load(sys.stdin)['key']['api_key'])")
echo "API Key: $API_KEY"

# 2. Проверить список моделей
curl -s https://fb1.spb.ru:443/api/v1/models | python3 -m json.tool

# 3. Тестовый chat completion
curl -s -X POST https://fb1.spb.ru:443/api/v1/chat/completions \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-14b",
    "messages": [{"role": "user", "content": "Тест агента — ответь кратко"}],
    "max_tokens": 50,
    "temperature": 0.7
  }' | python3 -m json.tool

# 4. Проверить health API
curl -s https://fb1.spb.ru:443/api/v1/health | python3 -m json.tool
```

### 13.3. Коды ошибок Agent API

| Код | Тип ошибки | Описание |
|-----|-----------|----------|
| 401 | `invalid_request_error` | Отсутствует API-ключ |
| 401 | `authentication_error` | Неверный формат или отозванный ключ |
| 400 | `invalid_request_error` | Не указана модель или неверный формат сообщений |
| 400 | `invalid_request_error` | Неизвестная модель |
| 502 | `api_error` | Gateway (vLLM) недоступен |

### 13.4. Диагностика через БД

```sql
-- Статистика использования API-ключей
SELECT k.key_id, k.name, k.api_key_prefix, k.last_used_at,
       o.name as org_name
FROM portal_api_keys k
JOIN portal_organizations o ON k.org_id = o.org_id
WHERE k.status = 'active'
ORDER BY k.last_used_at DESC NULLS LAST
LIMIT 10;
```

---

## 14. Резервное копирование

### 14.1. Резервное копирование БД AI Platform (SQLite)

```bash
BACKUP_DIR="/root/backups/$(date +%Y%m%d-%H%M)"
mkdir -p "$BACKUP_DIR"

# Скопировать БД из пода
POD=$(kubectl get pods -n aither-inference -l app=aither-ai-platform -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n aither-inference "$POD" -- python3 -c "
import sqlite3
conn = sqlite3.connect('/data/ai-platform.db')
conn.backup(open('/tmp/backup.db', 'wb'))
"
kubectl cp "aither-inference/$POD:/tmp/backup.db" "$BACKUP_DIR/ai-platform.db"
```

### 14.2. Резервное копирование БД Identity (SQLite)

```bash
POD=$(kubectl get pods -n aither-inference -l app=aither-identity -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n aither-inference "$POD" -- python3 -c "
import sqlite3
conn = sqlite3.connect('/data/identity.db')
conn.backup(open('/tmp/backup.db', 'wb'))
"
kubectl cp "aither-inference/$POD:/tmp/backup.db" "$BACKUP_DIR/identity.db"
```

### 14.3. Резервное копирование PostgreSQL (Portal BFF)

```bash
# Через под PostgreSQL
PGPOD=$(kubectl get pods -n aither-inference -l app=postgres -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n aither-inference "$PGPOD" -- pg_dump -U portal portal > "$BACKUP_DIR/portal-pg.sql"
```

### 14.4. Резервное копирование конфигурации VPS2

```bash
cp /root/nginx-failover.conf "$BACKUP_DIR/nginx-failover.conf"
cp -r /etc/nginx/ssl "$BACKUP_DIR/ssl-certs/" 2>/dev/null
```

### 14.5. Резервное копирование репозитория

```bash
cd /root/aither-project
git status  # Убедиться, что все изменения закоммичены
git bundle create "$BACKUP_DIR/aither-project.bundle" --all
```

### 14.6. Верификация резервной копии

```bash
# Проверить целостность SQLite
sqlite3 "$BACKUP_DIR/ai-platform.db" "PRAGMA integrity_check;"
sqlite3 "$BACKUP_DIR/ai-platform.db" "SELECT count(*) FROM api_keys;"
sqlite3 "$BACKUP_DIR/identity.db" "PRAGMA integrity_check;"

# Проверить целостность Git-бандла
git bundle verify "$BACKUP_DIR/aither-project.bundle"

# Проверить целостность PostgreSQL дампа
grep -c "CREATE TABLE" "$BACKUP_DIR/portal-pg.sql"
```

### 14.7. Права доступа

```bash
chmod 600 "$BACKUP_DIR"/*
chmod 700 "$BACKUP_DIR"
```

---

## 15. Восстановление

### 15.1. Восстановление PostgreSQL

```bash
RESTORE_FILE="/root/backups/<timestamp>/portal-pg.sql"
PGPOD=$(kubectl get pods -n aither-inference -l app=postgres -o jsonpath='{.items[0].metadata.name}')
kubectl exec -i -n aither-inference "$PGPOD" -- psql -U portal portal < "$RESTORE_FILE"
```

### 15.2. Восстановление AI Platform

```bash
RESTORE_FILE="/root/backups/<timestamp>/ai-platform.db"
POD=$(kubectl get pods -n aither-inference -l app=aither-ai-platform -o jsonpath='{.items[0].metadata.name}')
kubectl cp "$RESTORE_FILE" "aither-inference/$POD:/tmp/restore.db"
kubectl exec -n aither-inference "$POD" -- python3 -c "
import shutil
shutil.copy('/tmp/restore.db', '/data/ai-platform.db')
print('Restored')
"
kubectl rollout restart deploy/aither-ai-platform -n aither-inference
kubectl rollout status deploy/aither-ai-platform -n aither-inference --timeout=120s
```

### 15.3. Восстановление VPS2 nginx

```bash
RESTORE_DIR="/root/backups/<timestamp>"
cp "$RESTORE_DIR/nginx-failover.conf" /root/nginx-failover.conf
docker exec aither-failover-nginx nginx -t
docker exec aither-failover-nginx nginx -s reload
```

### 15.4. Верификация после восстановления

Выполнить полную проверку по разделу [7. Проверки работоспособности](#7-проверки-работоспособности-health-checks).

---

## 16. Откат (Rollback)

### 16.1. Откат Portal Frontend

```bash
# Просмотр истории
kubectl rollout history deploy/aither-portal-frontend -n aither-inference

# Откат к предыдущей версии
kubectl rollout undo deploy/aither-portal-frontend -n aither-inference
kubectl rollout status deploy/aither-portal-frontend -n aither-inference --timeout=120s
```

### 16.2. Откат Portal Backend (BFF)

```bash
kubectl rollout undo deploy/aither-portal-backend -n aither-inference
kubectl rollout status deploy/aither-portal-backend -n aither-inference --timeout=120s
```

### 16.3. Откат VPS2 nginx

```bash
# Из резервной копии
cp /root/backups/<timestamp>/nginx-failover.conf /root/nginx-failover.conf
docker exec aither-failover-nginx nginx -t && docker exec aither-failover-nginx nginx -s reload

# Или из Git
cd /root/aither-project/aither-v2
git checkout <previous-commit> -- services/portal-frontend/nginx-failover-vps2.conf
cp services/portal-frontend/nginx-failover-vps2.conf /root/nginx-failover.conf
docker exec aither-failover-nginx nginx -s reload
```

### 16.4. Откат AI Platform

```bash
kubectl rollout undo deploy/aither-ai-platform -n aither-inference
kubectl rollout status deploy/aither-ai-platform -n aither-inference --timeout=120s
curl -s http://10.129.13.78:30902/version
```

### 16.5. Откат K8s ConfigMap

```bash
# Восстановить ConfigMap из предыдущей версии (если есть резервная копия)
kubectl apply -f /root/backups/<timestamp>/portal-frontend-configmap.yaml
kubectl rollout restart deploy/aither-portal-frontend -n aither-inference
```

### 16.6. Верификация после отката

Выполнить скрипт комплексной проверки из раздела [7.4](#74-скрипт-комплексной-проверки).

---

## 17. Типовые отказы и их устранение

### 17.1. Web UI не открывается (HTTP 502/504)

**Симптом:** Браузер показывает ошибку 502 Bad Gateway или 504 Gateway Timeout.

**Причины и решения:**

```bash
# 1. Проверить, работает ли VPS2 nginx
docker ps | grep aither-failover-nginx
docker logs aither-failover-nginx --tail=20

# 2. Проверить доступность K8s NodePort
curl -s -o /dev/null -w "%{http_code}" http://10.129.13.78:30080/

# 3. Проверить поды в K8s
kubectl get pods -n aither-inference
# Если поды в статусе Error/CrashLoopBackOff — смотреть логи:
kubectl logs -n aither-inference <pod-name> --tail=50
kubectl describe pod -n aither-inference <pod-name>

# 4. Если поды не запускаются (ImagePullBackOff):
kubectl describe pod -n aither-inference <pod-name> | grep -A5 "Events"
# Проверить доступность реестра:
ssh root@n8 "curl -fsS http://localhost:5000/v2/_catalog"
```

### 17.2. Ошибка «database: error» в /health

**Симптом:** Health-check возвращает `"database": "error"`.

```bash
# 1. Проверить под PostgreSQL
kubectl get pods -n aither-inference | grep postgres

# 2. Проверить логи PostgreSQL
kubectl logs -n aither-inference <postgres-pod> --tail=50

# 3. Проверить доступность из BFF
kubectl exec -n aither-inference deploy/aither-portal-backend -- python3 -c "
import urllib.request
print(urllib.request.urlopen('http://localhost:8000/health').read())
"

# 4. При необходимости перезапустить PostgreSQL
kubectl rollout restart deploy/postgres -n aither-inference
```

### 17.3. Модель не отвечает (ошибка vLLM)

**Симптом:** Чат возвращает «Model not found» или таймаут.

```bash
# 1. Проверить статус vLLM
kubectl get pods -n aither-inference -l app=vllm

# 2. Проверить health vLLM
curl -s http://10.129.13.78:30902/health

# 3. Проверить список моделей в vLLM
curl -s http://10.129.13.78:30902/v1/models | python3 -m json.tool

# 4. Проверить доступность GPU
kubectl describe pod -n aither-inference <vllm-pod> | grep -A10 "nvidia"
```

### 17.4. Ошибка CORS

**Симптом:** Браузер показывает ошибку Cross-Origin Resource Sharing.

```bash
# Проверить переменную CORS_ORIGIN
kubectl get deploy/aither-portal-backend -n aither-inference -o yaml | grep CORS_ORIGIN

# Установить правильное значение
kubectl set env deploy/aither-portal-backend -n aither-inference \
  PORTAL_CORS_ORIGIN="http://localhost:3000"
```

### 17.5. Превышен rate limit

**Симптом:** Пользователь получает 429 Too Many Requests.

Лимит: 100 запросов/мин на IP (через `@fastify/rate-limit` + Redis).

```bash
# Проверить Redis
kubectl get pods -n aither-inference | grep redis

# При необходимости перезапустить Redis
kubectl rollout restart deploy/redis -n aither-inference
```

### 17.6. Страница API-ключей не загружается

**Симптом:** «Не удалось загрузить ключи».

**Причина:** BFF endpoint `/api/v1/tokens` реализован не полностью (известное ограничение CB-WEBUI-01).

**Обходной путь:** Использовать прямые API-запросы через curl:

```bash
# Создание ключа
curl -X POST http://10.129.13.78:30080/api/v1/orgs/<ORG_ID>/api-keys \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "admin-key"}'

# Просмотр ключей организации
curl -s http://10.129.13.78:30080/api/v1/orgs/<ORG_ID>/api-keys \
  -H "Authorization: Bearer <JWT_TOKEN>" | python3 -m json.tool

# Отзыв ключа
curl -X DELETE http://10.129.13.78:30080/api/v1/orgs/<ORG_ID>/api-keys/<KEY_ID> \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

### 17.7. 32B модель только completion (не диалог)

**Симптом:** qwen-32b-base не ведёт диалог, только продолжает текст.

**Причина:** Базовая модель (base), не instruct. **Это известное ограничение, не баг.**

**Решение:** Использовать qwen-14b для диалоговых задач.

### 17.8. VPS2 недоступен — Internet-зона не работает

**Обходной путь:** Использовать Test Zone напрямую: `http://10.129.13.78:30080/`

Функциональность полностью идентична. API-ключи и учётные записи общие.

### 17.9. Под в статусе CrashLoopBackOff

```bash
# Получить логи падений
kubectl logs -n aither-inference <pod-name> --previous --tail=100

# Проверить события
kubectl describe pod -n aither-inference <pod-name> | grep -A20 "Events"

# Принудительно удалить под (ReplicaSet пересоздаст)
kubectl delete pod -n aither-inference <pod-name>
kubectl rollout status deploy/<deployment-name> -n aither-inference --timeout=180s
```

---

## 18. Безопасная процедура обновления

### 18.1. Подготовка

```bash
# 1. Убедиться, что все изменения закоммичены
cd /root/aither-project/aither-v2
git status

# 2. Создать резервную копию (см. раздел 14)
BACKUP_DIR="/root/backups/pre-upgrade-$(date +%Y%m%d-%H%M)"
mkdir -p "$BACKUP_DIR"
# ... выполнить процедуры из раздела 14

# 3. Проверить текущее состояние
kubectl get pods -n aither-inference -o wide
kubectl get deployments -n aither-inference
curl -s http://10.129.13.78:30080/health | python3 -m json.tool
```

### 18.2. Обновление Portal Frontend

```bash
# 1. Обновить ConfigMap
kubectl apply -f services/portal-frontend/k8s/portal-frontend.yaml

# 2. Перезапустить поды
kubectl rollout restart deploy/aither-portal-frontend -n aither-inference

# 3. Дождаться готовности
kubectl rollout status deploy/aither-portal-frontend -n aither-inference --timeout=120s

# 4. Проверить
curl -s -o /dev/null -w "%{http_code}" http://10.129.13.78:30080/
```

### 18.3. Обновление Portal Backend (BFF)

```bash
# 1. Собрать новый образ
cd /root/aither-project/portal
TAG="aither-portal-backend:stage18a-$(date +%Y%m%d-%H%M)"
docker build -t 10.129.13.78:5000/$TAG .
docker push 10.129.13.78:5000/$TAG

# 2. Обновить образ в K8s
kubectl set image deploy/aither-portal-backend -n aither-inference \
  portal-backend=10.129.13.78:5000/$TAG

# 3. Дождаться готовности
kubectl rollout status deploy/aither-portal-backend -n aither-inference --timeout=120s

# 4. Проверить
curl -s http://10.129.13.78:30080/health | python3 -m json.tool
```

### 18.4. Обновление VPS2 nginx

```bash
# 1. Обновить конфигурацию
cp /root/aither-project/aither-v2/services/portal-frontend/nginx-failover-vps2.conf \
   /root/nginx-failover.conf

# 2. Проверить синтаксис
docker exec aither-failover-nginx nginx -t

# 3. Применить (без даунтайма)
docker exec aither-failover-nginx nginx -s reload

# 4. Проверить
curl -sk -o /dev/null -w "%{http_code}" https://fb1.spb.ru:443/
```

### 18.5. Обновление vLLM (с даунтаймом ~5-10 мин)

```bash
# Запланировать окно обслуживания!

kubectl apply -f <updated-vllm-deployment.yaml>
kubectl rollout status deploy/<vllm-deployment> -n aither-inference --timeout=600s
curl -s http://10.129.13.78:30902/health
```

### 18.6. Откат при неудачном обновлении

```bash
# Немедленный откат BFF
kubectl rollout undo deploy/aither-portal-backend -n aither-inference
kubectl rollout status deploy/aither-portal-backend -n aither-inference --timeout=120s

# Немедленный откат Frontend
kubectl rollout undo deploy/aither-portal-frontend -n aither-inference
kubectl rollout status deploy/aither-portal-frontend -n aither-inference --timeout=120s
```

---

## 19. Верификация после обновления

### 19.1. Автоматизированный проверочный скрипт

```bash
#!/bin/bash
# post-upgrade-verify.sh — комплексная верификация после обновления

set -e
PASS=0
FAIL=0

check() {
    local desc="$1"
    local cmd="$2"
    local expected="$3"
    local result
    result=$(eval "$cmd" 2>/dev/null)
    if echo "$result" | grep -q "$expected"; then
        echo "✅ $desc"
        ((PASS++))
    else
        echo "❌ $desc (got: $result)"
        ((FAIL++))
    fi
}

echo "=== Aither Post-Upgrade Verification ==="
echo ""

# 1. K8s Pods
check "Portal Frontend pod Running" \
    "kubectl get pods -n aither-inference -l app=aither-portal-frontend -o jsonpath='{.items[0].status.phase}'" \
    "Running"

check "Portal Backend pod Running" \
    "kubectl get pods -n aither-inference -l app=aither-portal-backend -o jsonpath='{.items[0].status.phase}'" \
    "Running"

# 2. Health endpoints
check "BFF Health (/health)" \
    "curl -s http://10.129.13.78:30080/health" \
    '"status":"ok"'

check "BFF Health DB connected" \
    "curl -s http://10.129.13.78:30080/health" \
    '"database":"connected"'

# 3. Core / AI Platform
check "Core Status reachable" \
    "curl -s http://10.129.13.78:30080/api/v1/core/status" \
    '"status":"ok"'

# 4. Agent API
check "Agent API models accessible" \
    "curl -sk -o /dev/null -w '%{http_code}' https://fb1.spb.ru:443/api/v1/models" \
    "200"

check "Agent API health" \
    "curl -sk -o /dev/null -w '%{http_code}' https://fb1.spb.ru:443/api/v1/health" \
    "200"

# 5. Web UI доступность
check "Internet zone (443) accessible" \
    "curl -sk -o /dev/null -w '%{http_code}' https://fb1.spb.ru:443/" \
    "200"

check "Test Zone (30080) accessible" \
    "curl -s -o /dev/null -w '%{http_code}' http://10.129.13.78:30080/" \
    "200"

check "Dedicated 32B port (10443) accessible" \
    "curl -sk -o /dev/null -w '%{http_code}' https://fb1.spb.ru:10443/" \
    "200"

# 6. TLS certificate
check "TLS certificate valid" \
    "openssl s_client -connect fb1.spb.ru:443 -servername fb1.spb.ru </dev/null 2>/dev/null | openssl x509 -noout -dates | grep 'notAfter'" \
    "notAfter"

# 7. Model list
check "Models list returns qwen2.5-14b" \
    "curl -sk https://fb1.spb.ru:443/api/v1/models" \
    "qwen2.5-14b"

check "Models list returns qwen2.5-32b" \
    "curl -sk https://fb1.spb.ru:443/api/v1/models" \
    "qwen2.5-32b"

# 8. API status
check "API status endpoint" \
    "curl -s http://10.129.13.78:30080/api/v1/status" \
    "version"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [ $FAIL -gt 0 ]; then
    echo "⚠️  Some checks FAILED. Review output above."
    exit 1
else
    echo "✅ All checks PASSED."
fi
```

Сохранить скрипт и сделать исполняемым:
```bash
cat > /root/post-upgrade-verify.sh << 'SCRIPT'
# ... (вставить содержимое скрипта выше)
SCRIPT
chmod +x /root/post-upgrade-verify.sh
```

### 19.2. Ручная верификация (контрольный список)

| # | Проверка | Команда | Ожидаемый результат |
|---|----------|---------|---------------------|
| 1 | K8s поды Running | `kubectl get pods -n aither-inference` | Все `Running` |
| 2 | BFF Health | `curl -s http://10.129.13.78:30080/health` | `{"status":"ok","database":"connected"}` |
| 3 | Core Status | `curl -s http://10.129.13.78:30080/api/v1/core/status` | `{"status":"ok"}` |
| 4 | Internet Web UI | `curl -sk -o /dev/null -w "%{http_code}" https://fb1.spb.ru:443/` | `200` |
| 5 | Test Zone Web UI | `curl -s -o /dev/null -w "%{http_code}" http://10.129.13.78:30080/` | `200` |
| 6 | Порт 10443 | `curl -sk -o /dev/null -w "%{http_code}" https://fb1.spb.ru:10443/` | `200` |
| 7 | Agent API /models | `curl -sk -o /dev/null -w "%{http_code}" https://fb1.spb.ru:443/api/v1/models` | `200` |
| 8 | Agent API /health | `curl -sk -o /dev/null -w "%{http_code}" https://fb1.spb.ru:443/api/v1/health` | `200` |
| 9 | TLS-сертификат | `openssl s_client -connect fb1.spb.ru:443 -servername fb1.spb.ru </dev/null 2>/dev/null \| openssl x509 -noout -dates` | Действующие даты |
| 10 | Список моделей | `curl -sk https://fb1.spb.ru:443/api/v1/models \| python3 -m json.tool` | qwen2.5-14b + qwen2.5-32b |

### 19.3. Дымовой тест чата

```bash
# Создать тестовый ключ
TOKEN="<admin-jwt>"
ORG_ID="<org-id>"
API_KEY=$(curl -s -X POST http://10.129.13.78:30080/api/v1/orgs/$ORG_ID/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"smoke-test"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['key']['api_key'])")

# Тест 14B chat
curl -s https://fb1.spb.ru:443/api/v1/chat/completions \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-14b","messages":[{"role":"user","content":"Ответь одним словом: столица России?"}],"max_tokens":20}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'][:50])"

# Ожидается: ответ, содержащий «Москва»
```

### 19.4. Критерии успешной верификации

- Все 10 пунктов ручной проверки — ✅ PASS
- Дымовой тест чата возвращает осмысленный ответ
- Обе зоны (Internet + Test Zone) доступны
- TLS-сертификат валиден
- PostgreSQL подключён (`"database":"connected"`)
- AI Platform (Core) доступен

---

## Приложение A. Переменные окружения BFF

| Переменная | Назначение | Значение по умолчанию |
|-----------|-----------|----------------------|
| `JWT_SECRET` | Секрет для подписи JWT-токенов | **Обязательна** |
| `PG_HOST` | Хост PostgreSQL | `10.129.13.78` |
| `PG_PORT` | Порт PostgreSQL | `31113` |
| `PG_USER` | Пользователь PostgreSQL | `aither` |
| `PGPASSWORD` | Пароль PostgreSQL | — |
| `PG_DB` | Имя БД | `aither` |
| `CORE_API` | URL AI Platform (vLLM) | `http://gateway:8080` |
| `NODE_ENV` | Режим (`production`/`development`) | `production` |
| `CORS_ORIGIN` | Разрешённый CORS-источник | `https://<PUBLIC_HOST>` |
| `PUBLIC_HOST` | Публичный хост | `localhost` |
| `INVITE_CODE` | Код приглашения для регистрации | — |
| `ADMIN_KEY` | Ключ администратора (обход auth) | — |
| `ADMIN_JWT_SECRET` | Секрет JWT для Gateway admin | **Обязателен** |
| `DELEGATION_PRIVATE_KEY` | Приватный ключ делегирования RSA | **Обязателен** |
| `GITHUB_CLIENT_ID` | OAuth GitHub Client ID | — |
| `GITHUB_CLIENT_SECRET` | OAuth GitHub Client Secret | — |
| `GOOGLE_CLIENT_ID` | OAuth Google Client ID | — |
| `GOOGLE_CLIENT_SECRET` | OAuth Google Client Secret | — |
| `YANDEX_CLIENT_ID` | OAuth Yandex Client ID | — |
| `YANDEX_CLIENT_SECRET` | OAuth Yandex Client Secret | — |
| `YOOKASSA_SHOP_ID` | YooKassa Shop ID | — |
| `YOOKASSA_SECRET` | YooKassa Secret Key | — |

## Приложение B. Команды быстрого доступа

```bash
# Статус всех подов
alias kp='kubectl get pods -n aither-inference -o wide'

# Логи BFF
alias klog-bff='kubectl logs -n aither-inference deploy/aither-portal-backend --tail=100'

# Логи Frontend
alias klog-fe='kubectl logs -n aither-inference deploy/aither-portal-frontend --tail=100'

# Health check
alias health='curl -s http://10.129.13.78:30080/health | python3 -m json.tool'

# Перезапуск BFF
alias restart-bff='kubectl rollout restart deploy/aither-portal-backend -n aither-inference && kubectl rollout status deploy/aither-portal-backend -n aither-inference --timeout=120s'

# Перезапуск Frontend
alias restart-fe='kubectl rollout restart deploy/aither-portal-frontend -n aither-inference && kubectl rollout status deploy/aither-portal-frontend -n aither-inference --timeout=120s'

# Полная проверка
alias check-all='bash /root/post-upgrade-verify.sh'
```

---

## Приложение C. Схема БД (таблицы Portal)

| Таблица | Назначение |
|---------|-----------|
| `portal_users` | Пользователи (OAuth-провайдер, email, хеш пароля) |
| `portal_organizations` | Организации |
| `portal_org_members` | Членство в организациях (роли: owner, billing_admin, developer, viewer) |
| `portal_api_keys` | API-ключи (`ak-...`) |
| `chats` | Чаты (привязка к пользователю и модели) |
| `chat_messages` | Сообщения чатов (CASCADE DELETE) |
| `billing_accounts` | Баланс токенов организаций |
| `payment_transactions` | Платёжные транзакции (YooKassa) |

---

## Связанные документы

- [ADR-CB-WEBUI-001](../architecture/ADR-CB-WEBUI-001.md) — Архитектурное решение
- [RUNBOOK_BACKUP](../../aither-v2/docs/stage-u1.3/RUNBOOK_BACKUP.md) — Подробная процедура резервного копирования
- [RUNBOOK_RESTORE](../../aither-v2/docs/stage-u1.3/RUNBOOK_RESTORE.md) — Подробная процедура восстановления
- [RUNBOOK_UPGRADE](../../aither-v2/docs/stage-u1.3/RUNBOOK_UPGRADE.md) — Процедура обновления компонентов
- [RUNBOOK_ROLLBACK](../../aither-v2/docs/stage-u1.3/RUNBOOK_ROLLBACK.md) — Процедура отката
- [OPERATIONAL-RUNBOOK](../../aither-v2/docs/stage18b/OPERATIONAL-RUNBOOK.md) — Операционный runbook Stage 18B
- [WEB UI GUIDE](../user-package/13_WEB_UI_GUIDE.md) — Руководство пользователя Web UI
- [DUAL ZONE ACCESS GUIDE](../user-package/15_DUAL_ZONE_ACCESS_GUIDE.md) — Руководство по двухзонному доступу
