- Stage 06: PASSED WITH FINDINGS / CONNECTOR VERIFIED.
- Stage 05 is accepted for MVP with findings. Not production-ready.

Evidence updated:
- bff-status-code-propagation-check.txt (new)
- bff-14b-chat-auth-status.txt (updated, now shows 401)
- bff-32b-completion-no-token-401.txt (updated, now shows 401)
- bff-acceptance-report.md (updated with new results)
- bff-routing-policy.md (updated with status code info)
- bff-security-notes.md (updated)
- bff-inventory-report.md (updated)

Findings:
- BFF-STATUS-01: PASSED (status code propagation)
- BFF-TOKEN-01: NOT COLLECTED (unchanged)

## Stage 06 — Redis / Rate Limiting

Status: PASSED WITH FINDINGS / CONNECTOR VERIFIED

Summary:
- Redis deployed: aither-redis-rate-limit, 1/1 Running, redis:7-alpine.
- Redis initial securityContext caused CrashLoopBackOff (chown).
  Fixed by removing restrictive securityContext — documented in BFF-RL-REDIS-FAIL-01.
- BFF updated to v0.3.0 with Redis-backed fixed-window rate limiting.
- Rate limit checks before upstream call on POST /api/v1/chat and /api/v1/completions.
- GET /health NOT rate-limited (shows RL status and redis connection state).
- Rate limit key: rl:{sha256(token)}:{window} or rl:ip:{client_ip}:{window}.
- No raw Authorization tokens stored in Redis.
- Redis unavailable → fail-open (requests allowed, logged).
- Settings via env vars: RATE_LIMIT_ENABLED, REDIS_URL, RATE_LIMIT_WINDOW_SECONDS, RATE_LIMIT_MAX_REQUESTS.
- Default: 10 requests per 60 seconds.

Evidence:
- 12 evidence files in docs/mvp-roadmap/06-rate-limiting/evidence/
- Under-limit: not 429 (confirmed)
- Exceeded limit: HTTP 429 (confirmed)
- Window reset: confirmed via key flush
- Key safety: no raw tokens in Redis (confirmed)
- No secrets committed (confirmed)
- Forbidden areas unchanged (confirmed)

Findings added in FINDINGS.md:
- BFF-RL-01: PASSED
- BFF-RL-REDIS-01: PASSED
- BFF-RL-429-01: PASSED
- BFF-RL-KEY-01: PASSED
- BFF-RL-RESET-01: PASSED
- BFF-RL-REDIS-FAIL-01: PARTIAL
- BFF-RL-RESET-TTL-01: MINOR FINDING (added during audit)
- BFF-TOKEN-01: NOT COLLECTED (unchanged)
- BFF-AUTH-01: PARTIAL (unchanged)

## ChatGPT Audit Result

**Date:** 2026-07-20
**Commit audited:** c16c0bf
**Method:** GitHub connector

**Result: Stage 06 — PASSED WITH FINDINGS / CONNECTOR VERIFIED**

**Accepted:**
1. Redis deployed and running (1/1, redis:7-alpine).
2. BFF v0.3.0 contains Redis-backed fixed-window rate limiting.
3. HTTP 429 confirmed when limit exceeded.
4. Rate limit key uses SHA-256(token) or client IP — no raw tokens in Redis.
5. Forbidden runtime zones unchanged.

**Open findings (retained):**
- BFF-RL-REDIS-FAIL-01: PARTIAL (fail-open when Redis unavailable)
- BFF-RL-RESET-TTL-01: MINOR FINDING (TTL reset not directly observed; reset verified by manual key flush)
- BFF-TOKEN-01: NOT COLLECTED (unchanged)
- BFF-AUTH-01: PARTIAL (unchanged)

**Stage 06 is accepted for MVP with findings. Not production-ready.**

**Gate after audit:**
- Stage 06: **PASSED WITH FINDINGS / CONNECTOR VERIFIED**
- Stage 07: **READY FOR TASK PREPARATION**