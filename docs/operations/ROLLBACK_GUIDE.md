# Руководство по откату (Rollback) платформы Aither

**Версия документа:** 1.0
**Дата:** 2026-07-26
**Пространство имён K8s:** `aither-inference`
**Язык:** Русский

---

## Содержание

1. [Общие положения](#1-общие-положения)
2. [Триггеры отката](#2-триггеры-отката)
3. [Предоткатный чек-лист](#3-предоткатный-чек-лист)
4. [Процедуры отката по компонентам](#4-процедуры-отката-по-компонентам)
   - [4.1 aither-ai-platform](#41-aither-ai-platform)
   - [4.2 aither-portal](#42-aither-portal)
   - [4.3 aither-portal-frontend](#43-aither-portal-frontend)
   - [4.4 aither-bff](#44-aither-bff)
   - [4.5 aither-identity](#45-aither-identity)
   - [4.6 vllm-14b-instruct](#46-vllm-14b-instruct)
   - [4.7 vllm-32b-gptq](#47-vllm-32b-gptq)
   - [4.8 nginx-gateway-32b](#48-nginx-gateway-32b)
   - [4.9 aither-redis-rate-limit](#49-aither-redis-rate-limit)
   - [4.10 VPS2 failover nginx](#410-vps2-failover-nginx)
5. [Проверка после отката](#5-проверка-после-отката)
6. [Матрица решений по откату](#6-матрица-решений-по-откату)
7. [Просмотр истории ревизий](#7-просмотр-истории-ревизий)
8. [Аварийный откат из Git](#8-аварийный-откат-из-git)

---

## 1. Общие положения

Откат (rollback) — возврат деплоймента к предыдущей стабильной версии. Платформа Aither использует механизм `kubectl rollout undo`, который хранит историю ревизий (по умолчанию 10) для каждого Deployment.

### Ключевые правила

- **Всегда фиксируйте состояние ДО отката** (текущая ревизия, список подов, образы).
- **Откатывайте по одному компоненту**, проверяя работоспособность после каждого.
- **Не откатывайте БД автоматически** — миграции БД требуют отдельной процедуры.
- **Сохраняйте логи проблемного состояния** до отката для последующего анализа.

### Важные замечания

- **VPS2 nginx** (`aither-failover-nginx`) не управляется через K8s — для него отдельная процедура отката.
- **PostgreSQL на VPS2** (портал) требует отдельного подхода к откату схемы — см. [BACKUP_RESTORE_GUIDE.md](./BACKUP_RESTORE_GUIDE.md).
- **ConfigMap-ы** и **Secrets** не откатываются автоматически через `rollout undo` — требуется ручное восстановление из резервной копии.

---

## 2. Триггеры отката

Откат обязателен при наступлении любого из следующих условий:

### Критические (немедленный откат)

| Триггер | Признак | Действие |
|---------|---------|----------|
| **Ошибка деплоя** | Pods в статусе `CrashLoopBackOff`, `ImagePullBackOff`, `Error` > 2 мин после деплоя | Немедленный `rollout undo` |
| **5xx ошибки > 10%** | `rate(http_requests_total{status_code=~"5.."}[5m]) > 0.10` | Немедленный откат |
| **Потеря данных** | Пустые ответы API, отсутствие пользователей/ключей/чатов в БД | Немедленный откат + восстановление БД |
| **GPU недоступен** | vLLM поды не стартуют с GPU, `nvidia-smi` не видит устройств | Откат vLLM-деплойментов |
| **OAuth не работает** | Все провайдеры (GitHub/Google/Yandex) возвращают 401/500 | Откат aither-identity + aither-bff |

### Предупреждающие (откат в течение 30 мин)

| Триггер | Признак |
|---------|---------|
| **Latency > 2x baseline** | P95 latency > 10с (базовый: < 5с) |
| **Частичная деградация** | Одна модель недоступна, одна зона не отвечает |
| **Утечка памяти** | `process_memory_usage_bytes` растёт линейно > 10 мин |
| **Ошибки rate-limit** | Ложные 429 на легитимные запросы |

---

## 3. Предоткатный чек-лист

Перед выполнением отката **обязательно**:

- [ ] **Зафиксировать текущую ревизию** каждого затрагиваемого деплоймента:
  ```bash
  kubectl rollout history deploy/<name> -n aither-inference
  ```
- [ ] **Сохранить список подов и их образов:**
  ```bash
  kubectl get pods -n aither-inference -o wide > /tmp/pre-rollback-pods.txt
  kubectl get deploy -n aither-inference -o jsonpath='{range .items[*]}{.metadata.name}{"="}{.spec.template.spec.containers[0].image}{"\n"}{end}' > /tmp/pre-rollback-images.txt
  ```
- [ ] **Сохранить логи проблемных подов:**
  ```bash
  kubectl logs -n aither-inference deploy/<name> --tail=500 > /tmp/pre-rollback-<name>.log
  ```
- [ ] **Создать резервную копию ConfigMap и Secrets:**
  ```bash
  kubectl get configmap -n aither-inference -o yaml > /tmp/pre-rollback-configmaps.yaml
  kubectl get secret -n aither-inference -o yaml > /tmp/pre-rollback-secrets.yaml
  ```
- [ ] **Снять дамп БД портала** (если откат затрагивает БД-зависимые компоненты):
  ```bash
  ssh root@130.17.1.90 'docker exec aither-portal-portal-db-1 pg_dump -U portal portal' > /tmp/pre-rollback-portal-db.sql
  ```
- [ ] **Убедиться в доступности K8s API:**
  ```bash
  kubectl get nodes
  ```

---

## 4. Процедуры отката по компонентам

### 4.1 aither-ai-platform

**Назначение:** OpenAI-совместимый API-слой, маршрутизация моделей (14B → vLLM, 32B → Gateway).

**Зависимости:** aither-identity (валидация ключей), vllm-14b-instruct, nginx-gateway-32b.

#### Команды отката

```bash
# 1. Просмотр истории ревизий
kubectl rollout history deploy/aither-ai-platform -n aither-inference

# 2. Откат к предыдущей ревизии
kubectl rollout undo deploy/aither-ai-platform -n aither-inference

# 3. Откат к конкретной ревизии (например, revision 3)
kubectl rollout undo deploy/aither-ai-platform -n aither-inference --to-revision=3

# 4. Ожидание завершения
kubectl rollout status deploy/aither-ai-platform -n aither-inference --timeout=180s
```

#### Проверка после отката

```bash
# Проверка подов
kubectl get pods -n aither-inference -l app=aither-ai-platform -o wide

# Health endpoint
curl -s http://10.129.13.78:30902/health

# Список моделей
curl -s http://10.129.13.78:30902/v1/models | python3 -m json.tool

# Проверка версии
curl -s http://10.129.13.78:30902/version
```

#### Особые случаи

- **При откате с изменением БД:** если новый деплоймент внёс изменения в `ai-platform.db` (SQLite), может потребоваться восстановление БД из резервной копии.
- **Откат образа:** предыдущий стабильный образ обычно: `ai-platform:u1-3-models-fix`.

---

### 4.2 aither-portal

**Назначение:** Node.js Portal Backend (Fastify BFF) — аутентификация, чаты, API-ключи, организации.

**Зависимости:** PostgreSQL (VPS2), aither-identity, aither-ai-platform, aither-redis-rate-limit.

#### Команды отката

```bash
kubectl rollout history deploy/aither-portal -n aither-inference
kubectl rollout undo deploy/aither-portal -n aither-inference
kubectl rollout status deploy/aither-portal -n aither-inference --timeout=120s
```

#### Проверка после отката

```bash
# Health endpoint
curl -s http://10.129.13.78:30080/health | python3 -m json.tool
# Ожидается: {"status":"ok","database":"connected"}

# Статус API
curl -s http://10.129.13.78:30080/api/v1/status

# Проверка OAuth редиректов
curl -sI http://10.129.13.78:30080/auth/github | head -1  # Ожидается: 302
```

---

### 4.3 aither-portal-frontend

**Назначение:** Nginx со статикой SPA (портал Web UI).

**Зависимости:** aither-portal (BFF).

#### Команды отката

```bash
kubectl rollout history deploy/aither-portal-frontend -n aither-inference
kubectl rollout undo deploy/aither-portal-frontend -n aither-inference
kubectl rollout status deploy/aither-portal-frontend -n aither-inference --timeout=60s
```

#### Проверка после отката

```bash
# Доступность статики
curl -s -o /dev/null -w "%{http_code}" http://10.129.13.78:30080/

# Загрузка index.html
curl -s http://10.129.13.78:30080/ | head -5
# Ожидается: <!DOCTYPE html>...<title>Aither
```

---

### 4.4 aither-bff

**Назначение:** FastAPI BFF (Python) — проксирование запросов к моделям, rate-limiting, аутентификация.

**Зависимости:** aither-identity, aither-redis-rate-limit, vllm-14b-instruct, nginx-gateway-32b.

**ConfigMap:** `aither-bff-config` (содержит `app.py`).

#### Команды отката

```bash
kubectl rollout history deploy/aither-bff -n aither-inference
kubectl rollout undo deploy/aither-bff -n aither-inference
kubectl rollout status deploy/aither-bff -n aither-inference --timeout=90s
```

#### Проверка после отката

```bash
# Health
POD=$(kubectl get pods -n aither-inference -l app=aither-bff -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n aither-inference $POD -- curl -s http://localhost:8000/health

# Проксирование к моделям
kubectl exec -n aither-inference $POD -- curl -s http://localhost:8000/api/v1/models
```

---

### 4.5 aither-identity

**Назначение:** Сервис идентификации — выпуск и валидация API-ключей, JWT-токенов.

**Зависимости:** PostgreSQL (K8s), Redis (K8s).

**Secret:** `aither-identity-secret`.

#### Команды отката

```bash
kubectl rollout history deploy/aither-identity -n aither-inference
kubectl rollout undo deploy/aither-identity -n aither-inference
kubectl rollout status deploy/aither-identity -n aither-inference --timeout=90s
```

#### Проверка после отката

```bash
# Health
curl -s http://aither-identity.aither-inference.svc:8000/health

# Валидация токена (требуется действующий API-ключ)
curl -s -X POST http://aither-identity.aither-inference.svc:8000/validate \
  -H "Authorization: Bearer <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### Особые случаи

- **Secret `aither-identity-secret` не откатывается автоматически.** Если новый деплой изменил формат секрета, восстановите Secret из резервной копии вручную:
  ```bash
  kubectl apply -f /tmp/pre-rollback-secrets.yaml
  ```

---

### 4.6 vllm-14b-instruct

**Назначение:** vLLM-сервер модели Qwen2.5-14B-Instruct (GPU-инференс, узел n8, TP=2).

**Зависимости:** GPU (n8), PVC с моделями (`/data/models`).

#### Команды отката

```bash
kubectl rollout history deploy/vllm-14b-instruct -n aither-inference
kubectl rollout undo deploy/vllm-14b-instruct -n aither-inference
kubectl rollout status deploy/vllm-14b-instruct -n aither-inference --timeout=300s
```

> **Примечание:** откат vLLM может занять до 5 минут из-за загрузки модели в GPU-память.

#### Проверка после отката

```bash
# Статус пода
kubectl get pods -n aither-inference -l app=vllm-14b-instruct -o wide

# Логи запуска
kubectl logs -n aither-inference deploy/vllm-14b-instruct --tail=20

# Проверка моделей
curl -s http://10.129.13.78:8000/v1/models | python3 -m json.tool

# Тестовый запрос
curl -s -X POST http://10.129.13.78:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-14b","messages":[{"role":"user","content":"1+1="}],"max_tokens":10}'
```

#### Особые случаи

- **Смена GPU-узла:** если изменился `nodeSelector` (n7 ↔ n8), модель должна быть доступна в `/data/models` на целевом узле.
- **Питфол: /dev/shm:** при TP=2 требуется `emptyDir` с `sizeLimit: 16Gi` для `/dev/shm`. Если откат на версию без этого параметра — под не стартует.

---

### 4.7 vllm-32b-gptq

**Назначение:** vLLM-сервер модели Qwen2.5-32B-GPTQ (GPU-инференс, узел n7, TP=2).

**Зависимости:** GPU (n7), PVC с моделями.

**Secret:** `vllm-api-key`.

#### Команды отката

```bash
kubectl rollout history deploy/vllm-32b-gptq -n aither-inference
kubectl rollout undo deploy/vllm-32b-gptq -n aither-inference
kubectl rollout status deploy/vllm-32b-gptq -n aither-inference --timeout=600s
```

> **Примечание:** откат 32B модели занимает до 10 минут (большой образ, загрузка весов в GPU).

#### Проверка после отката

```bash
# Статус пода
kubectl get pods -n aither-inference -l app=vllm-32b-gptq -o wide

# Проверка через Gateway
curl -s http://10.99.3.103:8000/v1/models | python3 -m json.tool

# Тестовый запрос через Gateway
curl -s -X POST http://10.99.3.103:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-32b-base","prompt":"1+1=","max_tokens":10}'
```

---

### 4.8 nginx-gateway-32b

**Назначение:** Nginx-шлюз для 32B модели — проксирование, health-чеки, routing.

**Зависимости:** vllm-32b-gptq (upstream `10.99.3.103:8000`).

**ConfigMap:** `nginx-gateway-32b` (содержит `nginx.conf`).

#### Команды отката

```bash
kubectl rollout history deploy/nginx-gateway-32b -n aither-inference
kubectl rollout undo deploy/nginx-gateway-32b -n aither-inference
kubectl rollout status deploy/nginx-gateway-32b -n aither-inference --timeout=60s
```

#### Проверка после отката

```bash
# Health
kubectl exec -n aither-inference deploy/nginx-gateway-32b -- curl -s http://localhost:8000/healthz

# Ready check (проверяет upstream)
kubectl exec -n aither-inference deploy/nginx-gateway-32b -- curl -s http://localhost:8000/ready
```

#### Особые случаи

- **ConfigMap subPath:** если Deployment использует `subPath: nginx.conf` — ключ в ConfigMap **должен** называться `nginx.conf`. При несовпадении под уходит в `CrashLoopBackOff`.
- **DNS Fallback:** если ConfigMap использует hostname вместо ClusterIP (`vllm-32b-gptq.aither-inference.svc`), под на узле без ClusterDNS (n7) не стартует. Используйте ClusterIP `10.99.3.103`.

---

### 4.9 aither-redis-rate-limit

**Назначение:** Redis для rate-limiting BFF и aither-bff.

**Зависимости:** нет.

#### Команды отката

```bash
kubectl rollout history deploy/aither-redis-rate-limit -n aither-inference
kubectl rollout undo deploy/aither-redis-rate-limit -n aither-inference
kubectl rollout status deploy/aither-redis-rate-limit -n aither-inference --timeout=60s
```

#### Проверка после отката

```bash
# Проверка подключения
kubectl exec -n aither-inference deploy/aither-redis-rate-limit -- redis-cli PING
# Ожидается: PONG

# Проверка ключей (не должен быть пустым при работающей системе)
kubectl exec -n aither-inference deploy/aither-redis-rate-limit -- redis-cli DBSIZE
```

---

### 4.10 VPS2 failover nginx

**Назначение:** Docker-контейнер `aither-failover-nginx` на VPS2 (130.17.1.90) — TLS-терминация, проксирование Internet-трафика.

**Конфигурация:** `/root/nginx-failover.conf` (bind-mount в контейнер).

> **Питфол:** `patch`/`write_file` создают новый inode — Docker bind mount продолжает видеть старый файл. Требуется **полный перезапуск контейнера** (`docker stop && docker rm && docker run`).

#### Команды отката

```bash
# Вариант 1: Восстановление из резервной копии
cp /root/edge-backup-<timestamp>/nginx-failover.conf /root/
docker stop aither-failover-nginx && docker rm aither-failover-nginx
docker run -d --name aither-failover-nginx \
  --network host --restart unless-stopped \
  -v /root/nginx-failover.conf:/etc/nginx/conf.d/default.conf:ro \
  -v /root/ssl-cert:/etc/nginx/ssl:ro \
  nginx:alpine

# Вариант 2: Откат из Git
cd /root/aither-project/aither-v2
git checkout <previous-commit> -- services/portal-frontend/nginx-failover-vps2.conf
cp services/portal-frontend/nginx-failover-vps2.conf /root/nginx-failover.conf
docker stop aither-failover-nginx && docker rm aither-failover-nginx
docker run -d --name aither-failover-nginx \
  --network host --restart unless-stopped \
  -v /root/nginx-failover.conf:/etc/nginx/conf.d/default.conf:ro \
  -v /root/ssl-cert:/etc/nginx/ssl:ro \
  nginx:alpine
```

#### Проверка после отката

```bash
# Проверка конфигурации
docker exec aither-failover-nginx nginx -t

# Health endpoints
curl -sk -o /dev/null -w "%{http_code}" https://fb1.spb.ru:443/
curl -sk -o /dev/null -w "%{http_code}" https://fb1.spb.ru:10443/

# Модели через Internet
curl -sk https://fb1.spb.ru:443/v1/models | python3 -m json.tool
```

---

## 5. Проверка после отката

### 5.1 Автоматизированная проверка (скрипт)

```bash
#!/bin/bash
# post-rollback-verify.sh — верификация после отката
set -euo pipefail
NS="aither-inference"
PASS=0; FAIL=0

check() {
    local desc="$1" cmd="$2" expected="$3"
    result=$(eval "$cmd" 2>&1) || true
    if echo "$result" | grep -q "$expected"; then
        echo "✅ $desc"
        ((PASS++))
    else
        echo "❌ $desc (got: ${result:0:80})"
        ((FAIL++))
    fi
}

# 1. Все поды Running
check "All pods Running" \
    "kubectl get pods -n $NS --no-headers | grep -cv Running" "0"

# 2. Health endpoints
check "ai-platform health" \
    "curl -s http://10.129.13.78:30902/health" '"status"'

check "Portal BFF health" \
    "curl -s http://10.129.13.78:30080/health" '"status":"ok"'

# 3. Модели доступны
check "14B models list" \
    "curl -s http://10.129.13.78:8000/v1/models" 'qwen'

check "32B models list" \
    "curl -s http://10.99.3.103:8000/v1/models" 'qwen'

# 4. Internet-зона
check "Internet 443" \
    "curl -sk -o /dev/null -w '%{http_code}' https://fb1.spb.ru:443/" "200"

check "Internet 10443" \
    "curl -sk -o /dev/null -w '%{http_code}' https://fb1.spb.ru:10443/" "200"

# 5. Agent API
check "Agent /v1/models" \
    "curl -sk -o /dev/null -w '%{http_code}' https://fb1.spb.ru:443/v1/models" "200"

# 6. Redis
check "Redis PING" \
    "kubectl exec -n $NS deploy/aither-redis-rate-limit -- redis-cli PING" "PONG"

echo ""
echo "=== Результаты: $PASS пройдено, $FAIL не пройдено ==="
[ $FAIL -gt 0 ] && exit 1
echo "✅ Все проверки пройдены."
```

### 5.2 Ручная проверка (контрольный список)

| # | Проверка | Команда | Ожидаемый результат |
|---|----------|---------|---------------------|
| 1 | Поды Running | `kubectl get pods -n aither-inference` | Все `Running`, 0 `CrashLoopBackOff` |
| 2 | BFF Health | `curl -s http://10.129.13.78:30080/health` | `{"status":"ok","database":"connected"}` |
| 3 | AI Platform Health | `curl -s http://10.129.13.78:30902/health` | `{"status":"ok"}` |
| 4 | Internet Web UI (443) | `curl -sk -o /dev/null -w "%{http_code}" https://fb1.spb.ru:443/` | `200` |
| 5 | Internet Web UI (10443) | `curl -sk -o /dev/null -w "%{http_code}" https://fb1.spb.ru:10443/` | `200` |
| 6 | Test Zone Web UI | `curl -s -o /dev/null -w "%{http_code}" http://10.129.13.78:30080/` | `200` |
| 7 | Models list (Agent) | `curl -sk https://fb1.spb.ru:443/v1/models` | `qwen-14b` + `qwen-32b-base` |
| 8 | TLS сертификат | `openssl s_client -connect fb1.spb.ru:443 </dev/null 2>/dev/null \| openssl x509 -noout -dates` | Действующие даты |
| 9 | Chat 14B | `curl -sk -X POST https://fb1.spb.ru:443/v1/chat/completions -H "Authorization: Bearer <key>" -H "Content-Type: application/json" -d '{"model":"qwen-14b","messages":[{"role":"user","content":"test"}],"max_tokens":5}'` | HTTP 200 |
| 10 | Chat 32B | `curl -sk -X POST https://fb1.spb.ru:443/v1/chat/completions -H "Authorization: Bearer <key>" -H "Content-Type: application/json" -d '{"model":"qwen-32b-base","messages":[{"role":"user","content":"test"}],"max_tokens":5}'` | HTTP 200 |

---

## 6. Матрица решений по откату

Какие компоненты можно откатывать независимо, а какие — только группой.

| Компонент | Независимый откат | Затрагивает | Примечание |
|-----------|-------------------|-------------|------------|
| **vllm-14b-instruct** | ✅ Да | 14B инференс | Только исходящие вызовы к модели |
| **vllm-32b-gptq** | ✅ Да | 32B инференс | Требуется также перезапуск nginx-gateway-32b при смене IP |
| **nginx-gateway-32b** | ✅ Да | Маршрутизация 32B | Не затрагивает 14B модель |
| **aither-redis-rate-limit** | ✅ Да | Rate-limiting | Кратковременная потеря состояния rate-limit окон |
| **aither-portal-frontend** | ✅ Да | Web UI статика | Не затрагивает API |
| **aither-ai-platform** | ⚠️ Условно | Весь API-трафик | При откате без identity/BFF — проверить формат ключей |
| **aither-identity** | ⚠️ Условно | Аутентификация API | При изменении формата ключей — перевыпустить ключи |
| **aither-bff** | ⚠️ Условно | BFF-проксирование | Зависит от identity и Redis |
| **aither-portal** | ❌ Групповой | Портал (SPA + API + OAuth) | Требует согласованности с identity, БД, фронтендом |
| **VPS2 nginx** | ✅ Да | Internet-маршрутизация | Не затрагивает K8s-компоненты |

### Правила группового отката

**Если откатываете aither-portal — также проверьте:**
- `aither-portal-frontend` (версия статики должна соответствовать BFF)
- `aither-identity` (формат JWT-токенов)
- PostgreSQL на VPS2 (схема БД)

**Если откатываете aither-bff — также проверьте:**
- `aither-identity` (формат токенов)
- `aither-redis-rate-limit` (формат ключей rate-limit)

**Если откатываете всю цепочку API (aither-ai-platform + aither-identity + aither-bff):**
- Откатывать в порядке: identity → bff → ai-platform
- После отката перевыпустить все API-ключи

---

## 7. Просмотр истории ревизий

### Для всех деплойментов сразу

```bash
for deploy in aither-portal aither-portal-frontend aither-bff \
    aither-identity aither-ai-platform vllm-14b-instruct \
    vllm-32b-gptq nginx-gateway-32b aither-redis-rate-limit; do
    echo "=== $deploy ==="
    kubectl rollout history deploy/$deploy -n aither-inference 2>/dev/null || echo "  (not found)"
    echo ""
done
```

### Детальная информация по ревизии

```bash
# Просмотр конкретной ревизии
kubectl rollout history deploy/aither-ai-platform -n aither-inference --revision=3

# Просмотр образа ревизии
kubectl get deploy aither-ai-platform -n aither-inference \
  -o jsonpath='{.spec.template.spec.containers[0].image}'
```

---

## 8. Аварийный откат из Git

Если `rollout undo` недоступен (K8s API не отвечает, история ревизий повреждена):

### Откат манифестов из Git

```bash
cd /root/aither-project/aither-v2

# 1. Найти последний стабильный коммит
git log --oneline -20

# 2. Откатить манифесты конкретного компонента до стабильной версии
git checkout <stable-commit> -- services/ai-platform/k8s/ai-platform.yaml

# 3. Применить
kubectl apply -f services/ai-platform/k8s/ai-platform.yaml

# 4. Проверить
kubectl rollout status deploy/aither-ai-platform -n aither-inference --timeout=180s
```

### Полный откат всех манифестов

```bash
cd /root/aither-project/aither-v2

# 1. Восстановить все манифесты на стабильный коммит
git checkout <stable-commit> -- services/ manifests/

# 2. Применить в правильном порядке
kubectl apply -f services/identity/k8s/identity.yaml
kubectl apply -f services/ai-platform/k8s/ai-platform.yaml
kubectl apply -f services/portal-backend/k8s/portal-backend.yaml
kubectl apply -f services/portal-frontend/k8s/portal-frontend.yaml
kubectl apply -f manifests/mvp-roadmap/05-bff/bff-mvp.yaml
kubectl apply -f manifests/mvp-roadmap/06-rate-limiting/redis-rate-limit.yaml

# 3. Дождаться всех
kubectl wait --for=condition=available --all deploy -n aither-inference --timeout=600s
```

### Откат БД портала (PostgreSQL VPS2)

Откат кода может требовать отката схемы БД. Процедура описана в [BACKUP_RESTORE_GUIDE.md](./BACKUP_RESTORE_GUIDE.md#4-восстановление-из-резервной-копии).

---

## Связанные документы

- [BACKUP_RESTORE_GUIDE.md](./BACKUP_RESTORE_GUIDE.md) — Резервное копирование и восстановление
- [MONITORING_GUIDE.md](./MONITORING_GUIDE.md) — Мониторинг и алерты
- [WUI_OPERATIONS_GUIDE.md](../admin-guide/WUI_OPERATIONS_GUIDE.md) — Руководство администратора Web UI
