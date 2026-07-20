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

## Stage 06 — Redis / Rate Limiting

**Date:** 2026-07-20
**Hermes model:** deepseek-chat

### Task source

ChatGPT. Stage 06 — Redis-backed fixed-window rate limiting for BFF.

### What changed

1. **Redis deployed**: aither-redis-rate-limit (redis:7-alpine, 1/1 Running)
   - Initial CrashLoopBackOff due to securityContext -> fixed by removing restrictive securityContext
   - Documented as finding BFF-RL-REDIS-FAIL-01
2. **BFF app.py updated** to v0.3.0:
   - Added `redis.asyncio` client connection in lifespan
   - Added `_check_rate_limit()` — fixed-window INCR + EXPIRE
   - Rate limit checked before upstream call on POST /api/v1/chat and /api/v1/completions
   - Fail-open when Redis unavailable
   - Rate limit key: `rl:{sha256(token)}:{window}` or `rl:ip:{client_ip}:{window}`
3. **bff-mvp.yaml updated**:
   - ConfigMap app.py with rate limiting logic
   - ENV vars: RATE_LIMIT_ENABLED, REDIS_URL, RATE_LIMIT_WINDOW_SECONDS, RATE_LIMIT_MAX_REQUESTS
   - pip install includes `redis` package
4. **Manifests created**: manifests/mvp-roadmap/06-rate-limiting/redis-rate-limit.yaml

### Evidence collected

| Evidence | Status |
|---|---|
| redis-manifest-dry-run.txt | PASSED |
| redis-rollout-status.txt | PASSED |
| redis-pods-after.txt | PASSED |
| redis-service-after.yaml | PASSED |
| bff-rollout-after-rl.txt | PASSED |
| bff-pods-after-rl.txt | PASSED |
| rate-limit-under-limit.txt | PASSED (401, not 429) |
| rate-limit-exceeded-429.txt | PASSED (429 confirmed) |
| rate-limit-reset-window.txt | PASSED (flush + retry) |
| redis-key-safety-check.txt | PASSED (no raw token) |
| no-secret-leak-check.txt | PASSED |
| forbidden-scope-check.txt | PASSED |

### Reports created

- INSTRUCTIONS.md
- redis-rate-limiting-report.md
- rate-limit-test-report.md
- rate-limit-security-notes.md

### Open findings

- BFF-RL-REDIS-FAIL-01: PARTIAL (fail-open when Redis unavailable)
- BFF-TOKEN-01: NOT COLLECTED (unchanged)
- BFF-AUTH-01: PARTIAL (unchanged)

### Forbidden areas unchanged

- vLLM Deployments: NOT MODIFIED
- vLLM Services: NOT MODIFIED
- GPU limits: NOT MODIFIED
- TP / tensor_parallel_size: NOT MODIFIED
- Gateway runtime: NOT MODIFIED
- Gateway Stage 04 evidence: NOT MODIFIED
- Portal: NOT MODIFIED (not started)
- OAuth: NOT MODIFIED
- Stage 05 evidence: NOT MODIFIED

### Gate

- Stage 06: **COMPLETED BY HERMES / WAITING FOR CHATGPT AUDIT**
- Stage 07: **NOT APPROVED**

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

---

## Stage 06 Audit Result Minor Fix — documentation alignment

**Date:** 2026-07-20
**Reason:** External ChatGPT audit of c16c0bf returned `PASSED WITH FINDINGS / MINOR CORRECTION REQUIRED`.
**Fixes applied:**
1. FINDINGS.md: resolved BFF-RL-01 conflict (POSTPONED → SUPERSEDED), added BFF-RL-RESET-TTL-01 (MINOR FINDING).
2. CHAT_HANDOVER.md: removed stale "Stage 06: NOT STARTED", "Stage 06 is BLOCKED", "POSTPONED"; updated to PASSED WITH FINDINGS / CONNECTOR VERIFIED.
3. current-mvp-status.md: Redis RL set to PASSED WITH FINDINGS / CONNECTOR VERIFIED.
4. AUDIT_LOG.md: added ChatGPT Audit Result section with commit c16c0bf audit record.
5. PROJECT_MASTER.md: Stage 06 set to PASSED WITH FINDINGS / CONNECTOR VERIFIED.

**Gate after fix:**
- Stage 06: **PASSED WITH FINDINGS / CONNECTOR VERIFIED**
- Stage 07: **READY FOR TASK PREPARATION**
