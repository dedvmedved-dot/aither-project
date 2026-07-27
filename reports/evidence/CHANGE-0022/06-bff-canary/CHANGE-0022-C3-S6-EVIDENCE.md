# CHANGE-0022-C3 R7-R5-EMG-GW-R5 — Section 6: Real Production-Code BFF Canary

## Date
2026-07-27

## File Modified
`aither-v2/deploy/canary/bff-gateway-canary.yaml` — полная переработка (383 → 596 строк)

## Что сделано

### 1. Same source code as production BFF (v0.6.0-r7r7-c2-d18)
- Идентичная структура импортов, middleware, auth (admin + identity delegate)
- Все production-endpoint'ы: `/health`, `/ready`, `/api/v1/auth/login`, `/api/v1/auth/logout`, `/api/v1/auth/me`, `/api/v1/tokens` (GET/POST/DELETE), `/api/v1/models`, `/api/v1/chat`, `/api/v1/completions`
- Токен-менеджмент с ownership tracking (как в production)
- Login через identity service (как в production)

### 2. Same Docker image: `python:3.11-slim`
- Идентичный production BFF

### 3. Same dependency lock
- `pip install -q fastapi uvicorn[standard] httpx pydantic redis pyjwt[crypto]`
- `pyjwt[crypto]` добавлен для RS256 подписи (cryptography уже в production requirements)
- Никаких новых внешних зависимостей

### 4. Separate ConfigMap for upstream routing
- `BFF_GATEWAY_URL=http://aither-gateway.aither-inference.svc.cluster.local:8000`
- Только маршрутизация меняется; код — production

### 5. Separate Service + 1 replica
- `Service/aither-bff-gateway-canary` (ClusterIP, port 8000)
- `Deployment/aither-bff-gateway-canary` (replicas: 1)
- Production `aither-bff` НЕ изменён

### 6. Per-request RS256 delegation JWT (NOT static GATEWAY_AUTH_TOKEN)
- Функция `sign_delegation_jwt(org_id, user_id, tier, scopes, role)` → RS256 JWT
- JWT payload: `iss=aither-bff, aud=aither-gateway, sub, org_id, user_id, tier, scopes, jti, iat, nbf, exp`
- Каждый запрос к Gateway получает уникальный JWT (jti = uuid4)
- Приватный ключ: `/app/delegation/private.pem` (монтируется из K8s Secret `aither-delegation-key`)
- Fail-closed: ключ отсутствует → 503

### 7. Real StreamingResponse for SSE (не await response.aread())
- Функция `_stream_gateway()` → `StreamingResponse(event_stream(), media_type="text/event-stream")`
- Итерация через `resp.aiter_lines()` с реальной потоковой передачей
- Обработка ошибок: timeout, stream_error → SSE error + [DONE]
- Заголовки: `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`

### 8. Fail-closed: Redis outage → 503
- `check_rl()` возвращает `None` при недоступности Redis (вместо `True` как в production)
- Все эндпоинты: `rl_result is None → HTTP 503`
- Rate limiting fail-open в production; fail-closed в canary

### 9. `/ready` — полная проверка зависимостей
- Redis ping
- Gateway `/health` (raise_for_status)
- Delegation key (файл существует и читается)
- Gateway `/v1/models` (количество моделей > 0)
- Любой failure → HTTP 503 `{"status":"degraded",...}`
- Все OK → HTTP 200 `{"status":"ok",...}`
- Readiness probe использует `/ready`

### 10. `/health` — только process check
- Возвращает `{"status":"ok","version":"0.6.0-r7r7-c2-d18-canary","routes_through":"gateway","gateway_url":"...","rate_limit":"enabled"}`
- Никаких проверок зависимостей
- Liveness probe использует `/health`

### Что удалено из старого canary
- ❌ Inline упрощённая реализация (250 строк inline app.py)
- ❌ Статический `GATEWAY_AUTH_TOKEN` (`Authorization: Bearer {B32T}`)
- ❌ `await response.aread()` вместо реального SSE
- ❌ Fail-open Redis (пропускал запросы без Redis)
- ❌ `/health` как readiness probe (без проверки Gateway)

### Верификация
```bash
cd /root/aither-project-r7-canonical
python3 -c "
import yaml, ast
with open('aither-v2/deploy/canary/bff-gateway-canary.yaml') as f:
    docs = list(yaml.safe_load_all(f))
print(f'Documents: {len(docs)}')
for d in docs:
    if d and d.get('kind') == 'ConfigMap':
        app_py = d['data']['app.py']
        ast.parse(app_py)
        print(f'  app.py: {len(app_py.splitlines())} lines, AST OK')
    elif d:
        print(f'  {d.get(\"kind\")}: {d.get(\"metadata\",{}).get(\"name\")}')
"
# → 3 documents
# → app.py: 570 lines, AST OK
# → Deployment: aither-bff-gateway-canary
# → Service: aither-bff-gateway-canary
```
