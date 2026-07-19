# BFF Routing Policy

## MVP Policy

1. Пользовательские клиенты должны обращаться только к BFF.
2. Portal должен обращаться только к BFF.
3. BFF является единственным пользовательским backend для inference.
4. BFF маршрутизирует 14B traffic в approved 14B backend (vllm-14b-instruct).
5. BFF маршрутизирует 32B completion traffic только через nginx-gateway-32b (никогда напрямую к vllm-32b-gptq).
6. BFF блокирует 32B chat запросы с HTTP 422 до upstream call.
7. BFF блокирует unknown model запросы с HTTP 400 до upstream call.
8. Authorization header пробрасывается от клиента в upstream без изменений.
9. Direct vLLM Services являются internal-only.
10. Direct gateway access является internal-only для BFF-to-gateway traffic.
11. Stage 07 Portal должен проверить схему Portal -> BFF only.
12. Stage 08 Security/NetworkPolicy должен решить, нужно ли ограничивать direct vLLM/gateway access на сетевом уровне.

## Implementation

BFF is implemented as **FastAPI** (python:3.11-slim, deployed via ConfigMap):

| Route | Method | Action | Upstream Target | Status Code |
|---|---|---|---|---|
| /health | GET | Health check | Local handler | 200 |
| /api/v1/chat | POST | Route 14B, block 32B (422), block unknown (400) | vllm-14b-instruct:8000 (14B only) | Upstream code propagated |
| /api/v1/completions | POST | Route 14B, route 32B via gateway, block unknown (400) | vllm-14b-instruct:8000 (14B), nginx-gateway-32b:8000 (32B) | Upstream code propagated |
| /api/v1/models | GET | Static model list | Local handler | 200 |

**Important**: All upstream responses now use `Response(status_code=resp.status_code)` — BFF returns the real upstream HTTP status code, not a hardcoded 200. This means:
- If upstream returns 401 (no auth), BFF returns 401
- If upstream returns 200 (success), BFF returns 200
- If upstream returns 500 (error), BFF returns 500

### Route verification

32B completion via nginx-gateway-32b: **YES** (confirmed)
32B chat blocked before upstream: **YES** (confirmed, HTTP 422)
32B direct vLLM bypass: **NOT PRESENT** (confirmed)
14B direct route: **YES** (approved, confirmed)
