# Aither AI Platform — Руководство по развёртыванию

**Версия:** OPS-02-R1
**Дата:** 26 июля 2026
**Назначение:** Пошаговое развёртывание платформы Aither AI с нуля
**Namespace:** `aither-inference`

---

## 1. Предварительные требования

### 1.1. Инфраструктура

| Компонент | Минимальная версия | Примечание |
|-----------|-------------------|------------|
| Kubernetes | 1.33 | Два узла: control-plane (n8) + worker (n7) |
| NVIDIA GPU Operator | 24.9+ | RuntimeClass: `nvidia`, GPU driver ≥ 550 |
| Docker / containerd | 24.0+ | Для сборки образов и загрузки в кластерный registry |
| Helm | 3.16+ | Только для GPU Operator; остальное — `kubectl apply` |
| kubectl | 1.33+ | Соответствует версии кластера |
| NVIDIA GPU (физически) | 2× GPU на узле | n8: RTX A5000/A6000, n7: RTX 5080 |

### 1.2. Требования к узлам

#### Control-plane узел `bootsman-k8s-clnt01-n8-gpu` (n8)
- **IP:** 10.129.13.78
- **Роль:** control-plane + inference primary
- **Лейблы:**
  ```bash
  kubectl label node bootsman-k8s-clnt01-n8-gpu \
    aither.io/inference-primary=true \
    aither.io/qwen14b-instruct=true
  ```
- **hostPath для моделей:** `/data/models/Qwen2.5-14B-Instruct`
- **Локальный registry:** `10.129.13.78:5000`

#### Worker узел `bootsmam-k8s-clnt01-n7-gpu` (n7)
- **IP:** 10.129.13.77
- **Роль:** inference worker (32B GPTQ)
- **Лейблы:**
  ```bash
  kubectl label node bootsmam-k8s-clnt01-n7-gpu \
    aither.io/qwen32b-gptq=true
  ```
- **hostPath для моделей:** `/data/models/Qwen2.5-32B-GPTQ`

### 1.3. Конфигурация GPU

```bash
# На КАЖДОМ узле:
# 1. Проверить драйвер
nvidia-smi

# 2. Проверить наличие моделей
ls -la /data/models/

# 3. Проверить RuntimeClass
kubectl get runtimeclass nvidia
# Если отсутствует — применить:
# kubectl apply -f aither-v2/02-containerd-nvidia-runtime/manifests/runtimeclass-nvidia.yaml

# 4. Проверить allocatable GPU
kubectl describe node <node> | grep nvidia.com/gpu
# Ожидается: nvidia.com/gpu: 2 (или больше)
```

### 1.4. Предварительная проверка окружения

```bash
# Проверка kubectl доступа
kubectl get nodes
# Ожидается: оба узла в статусе Ready

# Проверка доступности namespace (будет создан при первом apply)
kubectl get ns aither-inference 2>/dev/null || echo "Будет создан"

# Проверка registry
curl -s http://10.129.13.78:5000/v2/_catalog
```

---

## 2. Порядок развёртывания

Развёртывание выполняется **строго по порядку**, так как каждый последующий
компонент зависит от предыдущих. Полное время: ~15–20 минут (без учёта загрузки образов).

```
1. vLLM Models (14B + 32B)    ← модели должны быть загружены до AI Platform
2. Redis Rate Limit            ← требуется для BFF
3. AI Platform                  ← зависит от: vLLM, Identity, nginx-gateway
4. Identity                     ← зависит от: PVC (автономный)
5. BFF (Backend-for-Frontend)  ← зависит от: Redis, vLLM, nginx-gateway
6. Portal Backend               ← зависит от: Identity, AI Platform
7. Portal Frontend              ← зависит от: Portal Backend
8. nginx Gateway 32B            ← зависит от: vLLM 32B
```

### Шаг 1: vLLM Models (14B Instruct + 32B GPTQ)

```bash
# 1.1 Создать namespace
kubectl apply -f aither-v2/03-vllm-14b-deploy/manifests/vllm-namespace.yaml

# 1.2 Создать ServiceAccount
kubectl apply -f aither-v2/03-vllm-14b-deploy/manifests/vllm-sa.yaml

# 1.3 Создать Secret с API-ключом vLLM (если ещё не создан)
kubectl create secret generic vllm-api-key \
  --namespace aither-inference \
  --from-literal=VLLM_API_KEY="<сгенерированный-api-ключ>" \
  --dry-run=client -o yaml | kubectl apply -f -

# 1.4 Развернуть vLLM-деплойменты (оба: 14B + 32B)
kubectl apply -f aither-v2/03-vllm-14b-deploy/manifests/vllm-deployment.yaml

# 1.5 Создать Service для каждого vLLM
kubectl apply -f aither-v2/03-vllm-14b-deploy/manifests/vllm-service.yaml

# 1.6 Применить NetworkPolicy (опционально, для изоляции)
kubectl apply -f aither-v2/03-vllm-14b-deploy/manifests/vllm-network-policy.yaml

# 1.7 Дождаться готовности (startupProbe: до 5 минут на модель)
kubectl wait --for=condition=ready pod \
  -l model=qwen-14b-instruct \
  -n aither-inference \
  --timeout=600s

kubectl wait --for=condition=ready pod \
  -l model=qwen-32b-gptq \
  -n aither-inference \
  --timeout=600s

# 1.8 Проверить
kubectl get pods -n aither-inference -l app=vllm
```

**Важно:** 14B разворачивается на n8 (`aither.io/qwen14b-instruct=true`),
32B — на n7 (`aither.io/qwen32b-gptq=true`). Если 32B не стартует на n7
(медленная загрузка образа), перенесите образ вручную:

```bash
# На n8 (где образ уже есть):
ctr -n k8s.io image export /tmp/vllm-image.tar docker.io/vllm/vllm-openai:v0.8.5
scp /tmp/vllm-image.tar root@10.129.13.77:/tmp/

# На n7:
ssh root@10.129.13.77 \
  'ctr -n k8s.io image import /tmp/vllm-image.tar'
# После импорта под запустится автоматически
```

### Шаг 2: Redis Rate Limit

```bash
# 2.1 Развернуть Redis
kubectl apply -f aither-v2/manifests/mvp-roadmap/06-rate-limiting/redis-rate-limit.yaml

# 2.2 Дождаться готовности
kubectl wait --for=condition=ready pod \
  -l app=aither-redis-rate-limit \
  -n aither-inference \
  --timeout=120s

# 2.3 Проверить
kubectl exec -n aither-inference deployment/aither-redis-rate-limit -- redis-cli ping
# Ожидается: PONG
```

### Шаг 3: AI Platform

```bash
# 3.1 Применить манифест (Secret + PVC + Deployment + Service)
kubectl apply -f aither-v2/services/ai-platform/k8s/ai-platform.yaml

# 3.2 Дождаться готовности
kubectl wait --for=condition=ready pod \
  -l app=aither-ai-platform \
  -n aither-inference \
  --timeout=120s

# 3.3 Проверить health
kubectl exec -n aither-inference deployment/aither-ai-platform -- \
  curl -s http://localhost:8000/health
# Ожидается: {"status":"ok",...}
```

**Примечание:** AI Platform автоматически использует:
- `AI_PLATFORM_IDENTITY_URL=http://aither-identity:8000` — валидация API-ключей
- `AI_PLATFORM_GATEWAY_URL=http://nginx-gateway-32b.aither-inference.svc:8000` — 32B-модель
- `VLLM_API_KEY` из Secret `vllm-api-key` — для аутентификации в vLLM

### Шаг 4: Identity

```bash
# 4.1 Создать Secret (на основе примера)
# Сначала создайте копию с реальными значениями:
cp aither-v2/services/identity/k8s/identity-secret.example.yaml \
   /tmp/aither-identity-secret.yaml

# Отредактируйте /tmp/aither-identity-secret.yaml:
#   IDENTITY_SECRET_KEY — JWT signing key (минимум 32 символа)
#   IDENTITY_ADMIN_PASS — bcrypt-хеш пароля
# Генерация bcrypt-хеша:
# python3 -c "import bcrypt; print(bcrypt.hashpw(b'<password>', bcrypt.gensalt()).decode())"

# 4.2 Применить Secret
kubectl apply -f /tmp/aither-identity-secret.yaml

# 4.3 Применить манифест (PVC + Deployment + Service)
kubectl apply -f aither-v2/services/identity/k8s/identity.yaml

# 4.4 Дождаться готовности
kubectl wait --for=condition=ready pod \
  -l app=aither-identity \
  -n aither-inference \
  --timeout=120s

# 4.5 Проверить
kubectl exec -n aither-inference deployment/aither-identity -- \
  curl -s http://localhost:8000/health
```

### Шаг 5: BFF (Backend-for-Frontend)

```bash
# 5.1 Создать BFF Auth Secret
# Скопируйте пример:
cp aither-v2/manifests/mvp-roadmap/07-auth-api/bff-auth-secret.example.yaml \
   /tmp/aither-bff-auth.yaml

# Отредактируйте /tmp/aither-bff-auth.yaml:
#   ADMIN_USERNAME — имя администратора портала
#   ADMIN_PASSWORD_HASH — SHA-256 хеш пароля:
#     echo -n "<password>" | sha256sum
#   SESSION_SECRET — случайная строка (32+ символов)
#   AUTH_TOKEN_HASH_SECRET — случайная строка (32+ символов)
#   BFF_14B_UPSTREAM_AUTH_TOKEN — совпадает с VLLM_API_KEY из vllm-api-key Secret
#   BFF_32B_GATEWAY_AUTH_TOKEN — совпадает с VLLM_API_KEY из vllm-api-key Secret

kubectl apply -f /tmp/aither-bff-auth.yaml

# 5.2 Применить манифест (ConfigMap + Deployment + Service)
kubectl apply -f aither-v2/manifests/mvp-roadmap/05-bff/bff-mvp.yaml

# 5.3 Дождаться готовности (BFF устанавливает pip-зависимости при старте)
kubectl wait --for=condition=ready pod \
  -l app=aither-bff \
  -n aither-inference \
  --timeout=300s

# 5.4 Проверить
kubectl exec -n aither-inference deployment/aither-bff -- \
  curl -s http://localhost:8000/health
# Ожидается: {"status":"ok","version":"0.4.0",...}
```

### Шаг 6: Portal Backend

```bash
# 6.1 Применить манифест (Deployment + Service)
kubectl apply -f aither-v2/services/portal-backend/k8s/portal-backend.yaml

# 6.2 Дождаться готовности
kubectl wait --for=condition=ready pod \
  -l app=aither-portal-backend \
  -n aither-inference \
  --timeout=120s

# 6.3 Проверить
kubectl exec -n aither-inference deployment/aither-portal-backend -- \
  curl -s http://localhost:8000/health
```

### Шаг 7: Portal Frontend

```bash
# 7.1 Применить манифест (ConfigMap + Deployment + Service)
kubectl apply -f aither-v2/services/portal-frontend/k8s/portal-frontend.yaml

# 7.2 Дождаться готовности
kubectl wait --for=condition=ready pod \
  -l app=aither-portal-frontend \
  -n aither-inference \
  --timeout=120s

# 7.3 Проверить
kubectl exec -n aither-inference deployment/aither-portal-frontend -- \
  curl -s http://localhost:80/
# Ожидается: HTML-страница портала
```

**Test Zone (MVP-портал, отдельный деплоймент):**

```bash
# Дополнительный упрощённый портал для Test Zone (http://10.129.13.78:30080)
kubectl apply -f aither-v2/manifests/mvp-roadmap/07-portal/portal-mvp.yaml

kubectl wait --for=condition=ready pod \
  -l app=aither-portal \
  -n aither-inference \
  --timeout=120s
```

### Шаг 8: nginx Gateway 32B

```bash
# 8.1 Применить манифест (ConfigMap + Deployment + Service)
kubectl apply -f aither-v2/03-vllm-14b-deploy/manifests/nginx-gateway-32b.yaml

# 8.2 Дождаться готовности
kubectl wait --for=condition=ready pod \
  -l app=nginx-gateway \
  -n aither-inference \
  --timeout=120s

# 8.3 Проверить health
kubectl exec -n aither-inference deployment/nginx-gateway-32b -- \
  curl -s http://localhost:8000/health
# Ожидается: {"status":"ok"} (проксируется от vLLM 32B)
```

---

## 3. Конфигурация ConfigMap

### 3.1. `aither-bff-config`

**Путь:** Встроен в `aither-v2/manifests/mvp-roadmap/05-bff/bff-mvp.yaml`

**Назначение:** Код приложения BFF (Python/FastAPI), монтируется как `/app/app.py`.
Маршрутизирует запросы к 14B (напрямую) и 32B (через nginx-gateway).

**Основные настройки:**
- `BFF_14B_BASE_URL` (env) — `http://vllm-14b-instruct.aither-inference.svc:8000`
- `BFF_32B_GATEWAY_URL` (env) — `http://nginx-gateway-32b.aither-inference.svc:8000`
- `RATE_LIMIT_ENABLED` (env) — `true`
- `REDIS_URL` (env) — `redis://aither-redis-rate-limit.aither-inference.svc:6379/0`

**Обновление:**
```bash
# После правки bff-mvp.yaml — переприменить:
kubectl apply -f aither-v2/manifests/mvp-roadmap/05-bff/bff-mvp.yaml
kubectl rollout restart deployment/aither-bff -n aither-inference
```

### 3.2. `aither-portal-config`

**Путь:** Встроен в `aither-v2/manifests/mvp-roadmap/07-portal/portal-mvp.yaml`

**Назначение:** Статические файлы MVP-портала для Test Zone
(HTML, CSS, JS, nginx.conf). Монтируется как:
- `/etc/nginx/conf.d/default.conf` ← ключ `nginx.conf`
- `/usr/share/nginx/html/index.html` ← ключ `index.html`
- `/usr/share/nginx/html/styles.css` ← ключ `styles.css`
- `/usr/share/nginx/html/app.js` ← ключ `app.js`

### 3.3. `aither-portal-frontend-config`

**Путь:** Встроен в `aither-v2/services/portal-frontend/k8s/portal-frontend.yaml`

**Назначение:** Статические файлы основного портала (Internet Zone, Stage 18a).
Монтируется как:
- `/etc/nginx/conf.d/default.conf` ← ключ `nginx.conf`
- `/usr/share/nginx/html/index.html` ← ключ `index.html`

**Конфигурация nginx proxy:**
- `/api/` → `aither-portal-backend:8000`
- `/v1/chat/completions` → `aither-ai-platform:8000`
- `/health`, `/ready`, `/version` → `aither-portal-backend:8000`

### 3.4. `nginx-gateway-32b`

**Путь:** Встроен в `aither-v2/03-vllm-14b-deploy/manifests/nginx-gateway-32b.yaml`

**Назначение:** Rate-limiting reverse proxy для 32B-модели. Блокирует
`/v1/chat/completions` (32B — базовая модель, только text completion).

**Основные настройки:**
```nginx
# Rate limiting: 300 запросов/минуту, burst 20
limit_req_zone $binary_remote_addr zone=completions:10m rate=300r/m;

# Проксирование /v1/completions → vLLM 32B
location /v1/completions {
    limit_req zone=completions burst=20 nodelay;
    proxy_pass http://vllm-32b-gptq.aither-inference.svc:8000;
    proxy_read_timeout 300s;
    proxy_connect_timeout 10s;
}
```

**Обновление:**
```bash
# После правки YAML:
kubectl apply -f aither-v2/03-vllm-14b-deploy/manifests/nginx-gateway-32b.yaml
kubectl rollout restart deployment/nginx-gateway-32b -n aither-inference
```

---

## 4. Управление Secrets

### 4.1. `aither-bff-auth`

**Путь:** Создаётся из `aither-v2/manifests/mvp-roadmap/07-auth-api/bff-auth-secret.example.yaml`

| Ключ | Назначение | Генерация |
|------|-----------|-----------|
| `ADMIN_USERNAME` | Имя администратора портала | Задать вручную |
| `ADMIN_PASSWORD_HASH` | SHA-256 хеш пароля администратора | `echo -n "pass" \| sha256sum` |
| `SESSION_SECRET` | Секрет для сессионных cookie | `openssl rand -hex 32` |
| `AUTH_TOKEN_HASH_SECRET` | Секрет для HMAC-подписи API-токенов | `openssl rand -hex 32` |
| `BFF_14B_UPSTREAM_AUTH_TOKEN` | Bearer-токен для аутентификации в vLLM 14B | Совпадает с `VLLM_API_KEY` |
| `BFF_32B_GATEWAY_AUTH_TOKEN` | Bearer-токен для аутентификации в 32B Gateway | Совпадает с `VLLM_API_KEY` |

### 4.2. `aither-identity-secret`

**Путь:** Создаётся из `aither-v2/services/identity/k8s/identity-secret.example.yaml`

| Ключ | Назначение | Генерация |
|------|-----------|-----------|
| `IDENTITY_SECRET_KEY` | JWT signing key (мин. 32 символа) | `openssl rand -hex 32` |
| `IDENTITY_ADMIN_USER` | Имя bootstrap-администратора | `admin` |
| `IDENTITY_ADMIN_PASS` | bcrypt-хеш пароля администратора | `python3 -c "import bcrypt; print(bcrypt.hashpw(b'pass', bcrypt.gensalt()).decode())"` |

### 4.3. `aither-ai-platform-secret`

**Путь:** Встроен в `aither-v2/services/ai-platform/k8s/ai-platform.yaml`

Содержит только `AI_PLATFORM_LOG_LEVEL` (несекретное значение). API-ключи
для vLLM и Gateway читаются из других Secrets через `secretKeyRef`.

### 4.4. `vllm-api-key`

**Создание:**
```bash
kubectl create secret generic vllm-api-key \
  --namespace aither-inference \
  --from-literal=VLLM_API_KEY="$(openssl rand -hex 32)" \
  --dry-run=client -o yaml | kubectl apply -f -
```

Используется:
- vLLM-подами (env `VLLM_API_KEY`)
- AI Platform (env `AI_PLATFORM_GATEWAY_API_KEY`)
- BFF (env `BFF_14B_UPSTREAM_AUTH_TOKEN`, `BFF_32B_GATEWAY_AUTH_TOKEN`)

**Ротация:**
```bash
# 1. Обновить Secret
kubectl create secret generic vllm-api-key \
  --namespace aither-inference \
  --from-literal=VLLM_API_KEY="<новый-ключ>" \
  --dry-run=client -o yaml | kubectl apply -f -

# 2. Обновить aither-bff-auth (те же значения для _AUTH_TOKEN)
kubectl patch secret aither-bff-auth -n aither-inference \
  --type='json' \
  -p='[{"op":"replace","path":"/data/BFF_14B_UPSTREAM_AUTH_TOKEN","value":"'$(echo -n "<новый-ключ>" | base64)'"}]'

# 3. Перезапустить все зависимые поды
kubectl rollout restart deployment/vllm-14b-instruct -n aither-inference
kubectl rollout restart deployment/vllm-32b-gptq -n aither-inference
kubectl rollout restart deployment/aither-ai-platform -n aither-inference
kubectl rollout restart deployment/aither-bff -n aither-inference
```

---

## 5. Проверка после развёртывания

### 5.1. Проверка health всех подов

```bash
# Статус всех подов (все должны быть Running, READY 1/1)
kubectl get pods -n aither-inference -o wide

# Статус всех деплойментов
kubectl get deployments -n aither-inference

# Проверить на CrashLoopBackOff
kubectl get pods -n aither-inference --field-selector=status.phase!=Running
```

### 5.2. Проверка эндпоинтов здоровья

```bash
# AI Platform health
kubectl exec -n aither-inference deployment/aither-ai-platform -- \
  curl -s http://localhost:8000/health

# Identity health
kubectl exec -n aither-inference deployment/aither-identity -- \
  curl -s http://localhost:8000/health

# BFF health
kubectl exec -n aither-inference deployment/aither-bff -- \
  curl -s http://localhost:8000/health

# Portal Backend health
kubectl exec -n aither-inference deployment/aither-portal-backend -- \
  curl -s http://localhost:8000/health

# Portal Frontend
kubectl exec -n aither-inference deployment/aither-portal-frontend -- \
  curl -s -o /dev/null -w "%{http_code}" http://localhost:80/

# nginx Gateway 32B health
kubectl exec -n aither-inference deployment/nginx-gateway-32b -- \
  curl -s http://localhost:8000/health
```

### 5.3. Проверка доступности моделей

```bash
# Через vLLM напрямую (14B на n8)
curl -s http://10.129.13.78:8000/v1/models \
  -H "Authorization: Bearer <VLLM_API_KEY>" | python3 -m json.tool

# Через vLLM напрямую (32B на n7)
curl -s http://10.129.13.77:8000/v1/models \
  -H "Authorization: Bearer <VLLM_API_KEY>" | python3 -m json.tool

# Через AI Platform (Internet Zone — с VPS2)
curl -sk https://fb1.spb.ru:443/v1/models \
  -H "Authorization: Bearer <api-key>"

# Через Test Zone (MVP-портал)
curl -s http://10.129.13.78:30080/api/v1/models \
  -H "Authorization: Bearer <api-key>"
```

**Ожидаемые модели:**
- `qwen-14b` (Qwen2.5-14B-Instruct, chat-модель)
- `qwen-32b-base` (Qwen2.5-32B-GPTQ, completion-модель)

### 5.4. Проверка входа на портал

```bash
# 1. Получить страницу портала
curl -sk -o /dev/null -w "%{http_code}" https://fb1.spb.ru:10443/
# Ожидается: 200

# 2. Вход через BFF API (получить session cookie)
curl -sk -c /tmp/aither-cookies.txt -X POST \
  https://fb1.spb.ru:10443/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"<ADMIN_USERNAME>","password":"<password>"}'
# Ожидается: {"status":"ok","session_id":"..."}

# 3. Проверить сессию
curl -sk -b /tmp/aither-cookies.txt \
  https://fb1.spb.ru:10443/api/v1/auth/me
# Ожидается: {"username":"<ADMIN_USERNAME>","created_at":"..."}
```

### 5.5. Проверка работы чата

```bash
# 1. Создать API-токен (через Web UI или API)
# Вход уже выполнен, cookie в /tmp/aither-cookies.txt

# 2. Создать токен
curl -sk -b /tmp/aither-cookies.txt -X POST \
  https://fb1.spb.ru:10443/api/v1/tokens \
  -H "Content-Type: application/json" \
  -d '{"name":"deploy-test","scopes":["model:14b:chat","model:32b:completion"]}'
# Сохранить значение поля "token"

# 3. Отправить тестовое сообщение (14B chat)
TOKEN="<полученный-токен>"
curl -sk -X POST \
  https://fb1.spb.ru:10443/v1/chat/completions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-14b","messages":[{"role":"user","content":"Скажи привет"}],"max_tokens":20}'
# Ожидается: HTTP 200, choices[0].message.content содержит текст

# 4. Отправить тестовое сообщение (32B completion)
curl -sk -X POST \
  https://fb1.spb.ru:10443/v1/chat/completions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-32b-base","messages":[{"role":"user","content":"Продолжи: искусственный интеллект"}],"max_tokens":20}'
# Ожидается: HTTP 200, текст completion
# Примечание: 32B возвращает text_completion (через /v1/completions), не chat.completion
```

### 5.6. Проверка через Test Zone

```bash
# Test Zone портал
curl -s -o /dev/null -w "%{http_code}" http://10.129.13.78:30080/
# Ожидается: 200

# Test Zone API (если настроен NodePort)
curl -s http://10.129.13.78:30080/api/v1/models
```

---

## 6. Скрипт валидации развёртывания

Сохраните как `scripts/validate-deployment.sh`:

```bash
#!/bin/bash
# validate-deployment.sh — Валидация развёртывания Aither AI Platform
# Запуск: bash scripts/validate-deployment.sh [--strict]

set -euo pipefail
STRICT=false
[[ "${1:-}" == "--strict" ]] && STRICT=true

NS="aither-inference"
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS=0; FAIL=0; WARN=0

pass() { echo -e "  ${GREEN}✅ PASS${NC} — $1"; PASS=$((PASS+1)); }
fail() { echo -e "  ${RED}❌ FAIL${NC} — $1"; FAIL=$((FAIL+1)); }
warn() { echo -e "  ${YELLOW}⚠️  WARN${NC} — $1"; WARN=$((WARN+1)); }

echo "=== Aither Deployment Validation ==="
echo "Namespace: $NS"
echo "Started at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# --- 1. Namespace ---
echo "--- 1. Namespace ---"
if kubectl get ns "$NS" >/dev/null 2>&1; then
  pass "Namespace '$NS' существует"
else
  fail "Namespace '$NS' не найден"; fi

# --- 2. Pods Status ---
echo "--- 2. Pod Health ---"
EXPECTED_PODS=(
  "vllm-14b-instruct"
  "vllm-32b-gptq"
  "aither-redis-rate-limit"
  "aither-ai-platform"
  "aither-identity"
  "aither-bff"
  "aither-portal-backend"
  "aither-portal-frontend"
  "nginx-gateway-32b"
)

for prefix in "${EXPECTED_PODS[@]}"; do
  POD=$(kubectl get pods -n "$NS" --no-headers 2>/dev/null | grep "^${prefix}" | head -1 | awk '{print $1}')
  if [[ -z "$POD" ]]; then
    fail "Pod '$prefix-*' не найден"
    continue
  fi
  STATUS=$(kubectl get pod "$POD" -n "$NS" -o jsonpath='{.status.phase}' 2>/dev/null)
  READY=$(kubectl get pod "$POD" -n "$NS" -o jsonpath='{.status.containerStatuses[0].ready}' 2>/dev/null)
  RESTARTS=$(kubectl get pod "$POD" -n "$NS" -o jsonpath='{.status.containerStatuses[0].restartCount}' 2>/dev/null)

  if [[ "$STATUS" == "Running" && "$READY" == "true" ]]; then
    if [[ "$RESTARTS" -gt 5 ]]; then
      warn "$POD — Running ($RESTARTS перезапусков)"
    else
      pass "$POD — Running (restarts: $RESTARTS)"
    fi
  elif [[ "$STATUS" == "Running" ]]; then
    warn "$POD — Running, но не Ready"
  else
    fail "$POD — $STATUS"
  fi
done

# --- 3. Health Endpoints ---
echo "--- 3. Health Endpoints ---"
declare -A HEALTH_ENDPOINTS=(
  ["aither-ai-platform"]="http://localhost:8000/health"
  ["aither-identity"]="http://localhost:8000/health"
  ["aither-bff"]="http://localhost:8000/health"
  ["aither-portal-backend"]="http://localhost:8000/health"
)

for dep in "${!HEALTH_ENDPOINTS[@]}"; do
  ENDPOINT="${HEALTH_ENDPOINTS[$dep]}"
  POD=$(kubectl get pods -n "$NS" -l "app=${dep}" --no-headers 2>/dev/null | head -1 | awk '{print $1}')
  if [[ -z "$POD" ]]; then
    warn "$dep — под не найден, health check пропущен"
    continue
  fi
  HTTP_CODE=$(kubectl exec -n "$NS" "$POD" -- curl -s -o /dev/null -w "%{http_code}" "$ENDPOINT" 2>/dev/null || echo "000")
  if [[ "$HTTP_CODE" == "200" ]]; then
    pass "$dep health: $HTTP_CODE"
  else
    fail "$dep health: $HTTP_CODE (expected 200)"
  fi
done

# Frontend health (nginx)
POD_FE=$(kubectl get pods -n "$NS" -l app=aither-portal-frontend --no-headers 2>/dev/null | head -1 | awk '{print $1}')
if [[ -n "$POD_FE" ]]; then
  HTTP_FE=$(kubectl exec -n "$NS" "$POD_FE" -- curl -s -o /dev/null -w "%{http_code}" http://localhost:80/ 2>/dev/null || echo "000")
  if [[ "$HTTP_FE" == "200" ]]; then
    pass "Portal Frontend HTTP: $HTTP_FE"
  else
    fail "Portal Frontend HTTP: $HTTP_FE (expected 200)"
  fi
fi

# nginx Gateway 32B health
POD_GW=$(kubectl get pods -n "$NS" -l app=nginx-gateway --no-headers 2>/dev/null | head -1 | awk '{print $1}')
if [[ -n "$POD_GW" ]]; then
  HTTP_GW=$(kubectl exec -n "$NS" "$POD_GW" -- curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
  if [[ "$HTTP_GW" == "200" ]]; then
    pass "nginx Gateway 32B health: $HTTP_GW"
  else
    fail "nginx Gateway 32B health: $HTTP_GW (expected 200)"
  fi
fi

# --- 4. Services ---
echo "--- 4. Services ---"
EXPECTED_SVCS=(
  "vllm-14b-instruct"
  "vllm-32b-gptq"
  "aither-redis-rate-limit"
  "aither-ai-platform"
  "aither-identity"
  "aither-bff"
  "aither-portal-backend"
  "aither-portal-frontend"
  "nginx-gateway-32b"
)
for svc in "${EXPECTED_SVCS[@]}"; do
  if kubectl get svc "$svc" -n "$NS" >/dev/null 2>&1; then
    pass "Service '$svc' существует"
  else
    fail "Service '$svc' не найден"
  fi
done

# --- 5. Secrets ---
echo "--- 5. Secrets ---"
EXPECTED_SECRETS=(
  "vllm-api-key"
  "aither-bff-auth"
  "aither-identity-secret"
  "aither-ai-platform-secret"
)
for sec in "${EXPECTED_SECRETS[@]}"; do
  if kubectl get secret "$sec" -n "$NS" >/dev/null 2>&1; then
    pass "Secret '$sec' существует"
  else
    fail "Secret '$sec' не найден"
  fi
done

# --- 6. ConfigMaps ---
echo "--- 6. ConfigMaps ---"
EXPECTED_CMS=(
  "aither-bff-config"
  "nginx-gateway-32b"
  "aither-portal-frontend-config"
)
for cm in "${EXPECTED_CMS[@]}"; do
  if kubectl get configmap "$cm" -n "$NS" >/dev/null 2>&1; then
    pass "ConfigMap '$cm' существует"
  else
    fail "ConfigMap '$cm' не найден"
  fi
done

# --- 7. vLLM Model Check ---
echo "--- 7. vLLM Models ---"
for dep in vllm-14b-instruct vllm-32b-gptq; do
  POD=$(kubectl get pods -n "$NS" -l "app=vllm" --no-headers 2>/dev/null | grep "$dep" | head -1 | awk '{print $1}')
  if [[ -z "$POD" ]]; then
    warn "$dep — под не найден, model check пропущен"
    continue
  fi
  MODELS=$(kubectl exec -n "$NS" "$POD" -- curl -s http://localhost:8000/v1/models 2>/dev/null || echo "")
  if echo "$MODELS" | grep -q '"id"'; then
    pass "$dep — models endpoint отвечает"
  else
    warn "$dep — models endpoint не вернул данные (модель может загружаться)"
  fi
done

# --- 8. PVC Status ---
echo "--- 8. PVC Status ---"
for pvc in aither-ai-platform-data aither-identity-data; do
  PVC_STATUS=$(kubectl get pvc "$pvc" -n "$NS" -o jsonpath='{.status.phase}' 2>/dev/null)
  if [[ "$PVC_STATUS" == "Bound" ]]; then
    pass "PVC '$pvc' — Bound"
  elif [[ -n "$PVC_STATUS" ]]; then
    warn "PVC '$pvc' — $PVC_STATUS"
  else
    fail "PVC '$pvc' не найден"
  fi
done

# --- Summary ---
echo ""
echo "============================================"
echo -e "RESULTS: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC}, ${YELLOW}$WARN warnings${NC}"
echo "Finished at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [[ "$STRICT" == "true" ]]; then
  if [[ $FAIL -gt 0 ]] || [[ $WARN -gt 0 ]]; then
    echo "❌ STRICT MODE: FAIL (warnings treated as failures)"
    exit 1
  fi
fi

if [[ $FAIL -gt 0 ]]; then
  echo "❌ DEPLOYMENT: UNHEALTHY"
  exit 1
else
  echo "✅ DEPLOYMENT: HEALTHY"
  exit 0
fi
```

**Запуск валидации:**
```bash
# Обычный режим (warnings не блокируют)
bash scripts/validate-deployment.sh

# Строгий режим (warnings = failure)
bash scripts/validate-deployment.sh --strict
```

---

## 7. Типовые проблемы при развёртывании

### 7.1. Pod в CrashLoopBackOff

```bash
# Определить проблемный под
kubectl get pods -n aither-inference --field-selector=status.phase!=Running

# Просмотреть логи (включая предыдущую попытку)
kubectl logs -n aither-inference <pod-name> --previous

# Просмотреть события
kubectl describe pod -n aither-inference <pod-name> | grep -A10 "Events:"
```

**Типовые причины:**
- **vLLM:** модель не найдена в hostPath (`/data/models/Qwen2.5-*`)
- **vLLM:** недостаточно GPU-памяти (проверить `nvidia-smi` на узле)
- **BFF:** `Secret aither-bff-auth` не создан или отсутствуют ключи
- **Identity:** `Secret aither-identity-secret` не создан

### 7.2. vLLM не стартует: «No available shared memory»

**Симптом:** Под vLLM в CrashLoopBackOff, логи: `No available shared memory broadcast block found`.

**Причина:** `/dev/shm` по умолчанию 64 MB — недостаточно для tensor-parallel-size.

**Решение:** Уже предусмотрено в манифесте — том `dshm` с `sizeLimit: 8Gi`.
Если проблема сохраняется, проверить:
```bash
kubectl get pod -n aither-inference <pod> -o yaml | grep -A5 dshm
```

### 7.3. GPU не обнаруживаются (0 allocatable)

**Симптом:** Под висит в статусе `Pending`, события: `0/2 nodes available: insufficient nvidia.com/gpu`.

**Причина:** NVIDIA device plugin не видит GPU.

```bash
# Проверить device plugin
kubectl get pods -n kube-system -l name=nvidia-device-plugin-ds

# Проверить логи
kubectl logs -n kube-system -l name=nvidia-device-plugin-ds --tail=20

# На узле: проверить nvidia-smi
ssh root@10.129.13.77 nvidia-smi
```

**Решение:** Переустановить GPU Operator. См. `aither-v2/01-k8s-gpu-operator/README.md`.

### 7.4. Образ не загружается на worker-узле

**Симптом:** Под висит в `ImagePullBackOff` или `ErrImagePull`, особенно на n7.

**Причина:** Медленный интернет на n7 (CGNAT/VPN).

**Решение:** Перенести образ напрямую через `ctr` (см. Шаг 1, примечание).

### 7.5. BFF падает при старте: «Secret not found»

**Симптом:** BFF в CrashLoopBackOff, логи: `Missing: ADMIN_USERNAME, ADMIN_PASSWORD_HASH, ...`.

**Решение:**
```bash
# Проверить, что Secret существует
kubectl get secret aither-bff-auth -n aither-inference

# Если нет — создать из примера (см. Шаг 5)
kubectl apply -f /tmp/aither-bff-auth.yaml
kubectl rollout restart deployment/aither-bff -n aither-inference
```

### 7.6. Portal Frontend возвращает 502

**Симптом:** `curl http://10.129.13.78:30080/api/v1/models` → 502.

**Причина:** Portal Frontend не может связаться с `aither-portal-backend`.

**Диагностика:**
```bash
# Проверить, что Portal Backend Running
kubectl get pods -n aither-inference -l app=aither-portal-backend

# Проверить доступность изнутри Frontend пода
kubectl exec -n aither-inference deployment/aither-portal-frontend -- \
  curl -s http://aither-portal-backend:8000/health
```

### 7.7. AI Platform возвращает 503 на запросы к 32B

**Симптом:** Ошибка «upstream unavailable» при запросах к 32B-модели.

**Причина:** `nginx-gateway-32b` не может достичь `vllm-32b-gptq`.

**Диагностика:**
```bash
# Проверить 32B vLLM
kubectl get pods -n aither-inference -l model=qwen-32b-gptq

# Проверить nginx-gateway логи
kubectl logs -n aither-inference deployment/nginx-gateway-32b --tail=20 | grep -i error

# Проверить связность
kubectl exec -n aither-inference deployment/nginx-gateway-32b -- \
  curl -s http://vllm-32b-gptq.aither-inference.svc:8000/health
```

### 7.8. ConfigMap key не совпадает с subPath

**Симптом:** Под в CrashLoopBackOff, контейнер не стартует (логи пустые).

**Причина:** Deployment монтирует ConfigMap через `subPath`, но ключ в
ConfigMap не совпадает. Например: под ожидает `nginx.conf`, а ConfigMap
содержит `default.conf`.

**Диагностика:**
```bash
# Проверить subPath в деплойменте
kubectl get deploy <deployment> -n aither-inference \
  -o jsonpath='{.spec.template.spec.containers[0].volumeMounts[?(@.name=="config")].subPath}'

# Проверить ключи ConfigMap
kubectl get configmap <configmap> -n aither-inference \
  -o jsonpath='{.data}' | python3 -c "import sys,json; print(list(json.load(sys.stdin).keys()))"
```

**Решение:** Ключи должны совпадать. При несовпадении — обновить ConfigMap.

### 7.9. Портал работает, чат — нет (HTTP 401/403)

**Симптом:** Вход работает, дашборд работает, но чат возвращает 401 или 403.

**Диагностика:**
```bash
# Проверить scope API-ключа (должен включать model:14b:chat)
curl -sk -b /tmp/aither-cookies.txt \
  https://fb1.spb.ru:10443/api/v1/tokens

# Проверить AI Platform Identity URL
kubectl get deployment aither-ai-platform -n aither-inference \
  -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="AI_PLATFORM_IDENTITY_URL")].value}'
# Должно быть: http://aither-identity:8000
```

### 7.10. После переприменения ConfigMap поды не обновляются

**Симптом:** Изменили ConfigMap, но под продолжает использовать старую конфигурацию.

**Решение:** ConfigMap не триггерит автоматический перезапуск подов.
```bash
kubectl rollout restart deployment/<name> -n aither-inference
kubectl rollout status deployment/<name> -n aither-inference --timeout=120s
```

---

## 8. Полное удаление (teardown)

```bash
# Удалить всё в правильном порядке (обратном развёртыванию)
kubectl delete -f aither-v2/03-vllm-14b-deploy/manifests/nginx-gateway-32b.yaml --ignore-not-found
kubectl delete -f aither-v2/services/portal-frontend/k8s/portal-frontend.yaml --ignore-not-found
kubectl delete -f aither-v2/manifests/mvp-roadmap/07-portal/portal-mvp.yaml --ignore-not-found
kubectl delete -f aither-v2/services/portal-backend/k8s/portal-backend.yaml --ignore-not-found
kubectl delete -f aither-v2/manifests/mvp-roadmap/05-bff/bff-mvp.yaml --ignore-not-found
kubectl delete -f aither-v2/services/identity/k8s/identity.yaml --ignore-not-found
kubectl delete -f aither-v2/services/ai-platform/k8s/ai-platform.yaml --ignore-not-found
kubectl delete -f aither-v2/manifests/mvp-roadmap/06-rate-limiting/redis-rate-limit.yaml --ignore-not-found
kubectl delete -f aither-v2/03-vllm-14b-deploy/manifests/vllm-service.yaml --ignore-not-found
kubectl delete -f aither-v2/03-vllm-14b-deploy/manifests/vllm-deployment.yaml --ignore-not-found
kubectl delete -f aither-v2/03-vllm-14b-deploy/manifests/vllm-network-policy.yaml --ignore-not-found
kubectl delete -f aither-v2/03-vllm-14b-deploy/manifests/vllm-sa.yaml --ignore-not-found

# Удалить Secrets
kubectl delete secret vllm-api-key aither-bff-auth aither-identity-secret aither-ai-platform-secret \
  -n aither-inference --ignore-not-found

# Опционально: удалить PVC (данные будут потеряны!)
kubectl delete pvc aither-ai-platform-data aither-identity-data \
  -n aither-inference --ignore-not-found

# Опционально: удалить namespace (удалит ВСЁ)
# kubectl delete ns aither-inference
```

---

## 9. Полезные команды

```bash
# Быстрый статус всего namespace
alias ks='kubectl -n aither-inference'
ks get pods -o wide
ks get deployments
ks get svc
ks get configmap
ks get secret

# Просмотр логов с фильтрацией ошибок
ks logs deployment/<name> --tail=100 | grep -iE 'error|fail|exception|traceback'

# Просмотр использования ресурсов подами
kubectl top pods -n aither-inference

# Описание проблемного пода (полная диагностика)
ks describe pod <pod-name>

# Перезапуск деплоймента
ks rollout restart deployment/<name>
ks rollout status deployment/<name> --timeout=120s

# Доступ к поду изнутри
ks exec -it deployment/<name> -- /bin/sh

# Полный снапшот для отладки
ks get all -o yaml > /tmp/aither-snapshot.yaml
```

---

## 10. Связанные документы

- **Troubleshooting:** `docs/operations/TROUBLESHOOTING_GUIDE.md`
- **Runbook (Startup):** `aither-v2/docs/stage-u1.3/RUNBOOK_STARTUP.md`
- **Runbook (Backup):** `aither-v2/docs/stage-u1.3/RUNBOOK_BACKUP.md`
- **Runbook (Restore):** `aither-v2/docs/stage-u1.3/RUNBOOK_RESTORE.md`
- **Health Checklist:** `aither-v2/docs/stage-u1.3/03_HEALTH_CHECKLIST.md`
- **Known Issues:** `aither-v2/docs/stage-u1.3/05_KNOWN_ISSUES.md`
- **RC1 Release Notes:** `aither-v2/docs/release/RC1-RELEASE-NOTES.md`
- **WUI Operations Guide:** `docs/admin-guide/WUI_OPERATIONS_GUIDE.md`
- **Архитектура портала:** `aither-platform` skill (Hermes)
- **Hardware Inventory:** `hosts/hardware-inventory.md`
- **GPU Operator Setup:** `aither-v2/01-k8s-gpu-operator/README.md`
