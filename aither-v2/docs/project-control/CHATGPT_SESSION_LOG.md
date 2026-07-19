# ChatGPT Session Log

## Stage 05 — Corrective 2: BFF upstream status code propagation

**Date:** 2026-07-20
**Previous commit:** `0a2340f`
**Hermes model:** deepseek-chat

### Причина corrective

Предыдущий коммит (`0a2340f`) получил статус `PARTIAL / CORRECTIVE REQUIRED`.
Основная проблема: BFF возвращал HTTP 200 для upstream 401/403 ошибок, вместо проброса реального статус-кода.

### Что исправлено

1. В `app.py` и в ConfigMap (bff-mvp.yaml) оба handler'а (`/api/v1/chat` и `/api/v1/completions`) теперь используют `Response(content=..., status_code=resp.status_code, ...)`.
2. Вместо `return await resp.aread()` (терял статус-код) — `return Response(content=..., status_code=resp.status_code)`.

### Собранные evidence

| Evidence | Status |
|---|---|
| bff-health-200.txt | updated |
| bff-14b-chat-auth-status.txt | **new** (was bff-14b-chat-200.txt) — shows 401 |
| bff-32b-completion-no-token-401.txt | updated — shows 401 |
| bff-32b-completion-valid-token-200.txt | NOT COLLECTED |
| bff-32b-chat-blocked-422.txt | unchanged |
| bff-unknown-model-blocked.txt | unchanged |
| bff-status-code-propagation-check.txt | **new** — summary of all status codes |
| bff-rollout-status.txt | updated |
| bff-pods-after.txt | updated |

### Результаты тестов

| Проверка | До фикса | После фикса | Статус |
|---|---|---|---|
| 14B chat (no auth) | 200 {"error":"Unauthorized"} | **401** {"error":"Unauthorized"} | PASSED |
| 32B completion (no auth) | 200 {"error":"auth required"} | **401** {"error":"auth required"} | PASSED |
| 32B chat blocked | 422 | 422 | PASSED |
| unknown model | 400 | 400 | PASSED |
| /health | 200 | 200 | PASSED |
| 32B completion (valid token) | NOT COLLECTED | NOT COLLECTED | NOT COLLECTED |

### Findings PARTIAL / NOT COLLECTED

- **BFF-TOKEN-01**: Valid token test for 32B completion — NOT COLLECTED (VPN instability)
- **BFF-AUTH-01**: BFF has no built-in auth — PARTIAL (relies on upstream)

### Что запрещённое не менялось

- vLLM Deployments: NOT MODIFIED
- vLLM Services: NOT MODIFIED
- GPU limits: NOT MODIFIED
- TP / tensor_parallel_size: NOT MODIFIED
- Gateway runtime: NOT MODIFIED
- Gateway Stage 04 evidence: NOT MODIFIED
- Portal: NOT MODIFIED (not started)
- Redis: NOT MODIFIED (not started)
- OAuth: NOT MODIFIED
- Monitoring: NOT MODIFIED
- GPU Operator: NOT MODIFIED
- containerd / NVIDIA runtime: NOT MODIFIED

### Gate

- Stage 05 remains: **PARTIAL / WAITING FOR CHATGPT AUDIT**
- Stage 06: **BLOCKED** (requires Stage 05 audit pass)
