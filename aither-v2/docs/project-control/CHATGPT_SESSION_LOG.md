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

### Gate (before audit)

- Stage 05 remains: **PARTIAL / WAITING FOR CHATGPT AUDIT**
- Stage 06: **BLOCKED** (requires Stage 05 audit pass)

---

### ChatGPT Audit Result

**Date:** 2026-07-20
**Commit audited:** `8219c56`
**Method:** GitHub connector (raw link verification)

**Result: Stage 05 — PASSED WITH FINDINGS / CONNECTOR VERIFIED**

**Accepted evidence:**
1. BFF deployment aligned with FastAPI implementation.
2. BFF routes 32B completion through nginx-gateway-32b.
3. BFF blocks 32B chat before upstream (422).
4. BFF blocks unknown model (400).
5. BFF correctly propagates upstream HTTP status codes (401→401, was 200).
6. Direct vLLM 32B user-facing bypass is not present.
7. Secrets are not committed.

**Open findings (retained):**
- BFF-TOKEN-01: valid-token 32B completion test — NOT COLLECTED (VPN instability)
- BFF-AUTH-01: BFF has no built-in auth — PARTIAL (relies on upstream)

**Stage 05 is accepted for MVP with findings. Not production-ready.**

**Gate after audit:**
- Stage 05: **PASSED WITH FINDINGS / CONNECTOR VERIFIED**
- Stage 06: **READY FOR TASK PREPARATION**

---

## Stage 05 Audit Result Minor Fix — CHAT_HANDOVER.md stale status codes

**Date:** 2026-07-20
**Reason:** После audit result commit `da53e47` в CHAT_HANDOVER.md остались устаревшие HTTP 200 для status code propagation.
**Fix:** заменены строки:
- `14B chat via BFF: 200` → `14B chat via BFF (no auth): 401`
- `32B completion via BFF (no token): 200` → `32B completion via BFF (no token): 401`
**Gate after fix:** Stage 06 remains READY FOR TASK PREPARATION.
**Changed files:** CHAT_HANDOVER.md, CHATGPT_SESSION_LOG.md (эта запись).
**vLLM/GPU/TP/Gateway/BFF/Portal/Redis/OAuth:** NOT MODIFIED.
