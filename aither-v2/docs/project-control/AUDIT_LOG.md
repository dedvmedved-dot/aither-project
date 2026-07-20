- Stage 06: READY FOR TASK PREPARATION.
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

Status: COMPLETED BY HERMES / WAITING FOR CHATGPT AUDIT

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
- BFF-TOKEN-01: NOT COLLECTED (unchanged)
- BFF-AUTH-01: PARTIAL (unchanged)

Gate:
- Stage 06: WAITING FOR CHATGPT AUDIT
- Stage 07: NOT APPROVED