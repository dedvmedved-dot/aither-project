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

---

## Stage 07.1 — Auth / API Token / Agent Access Baseline

**Status: PARTIAL / CORRECTIVE REQUIRED**

**Date:** 2026-07-20
**Old Stage 07 Portal-only task:** SUPERSEDED. New sequence: Stage 07.1 (auth) → Stage 07.2 (Portal).

**Summary:**
- BFF v0.4.0 with central auth middleware.
- Admin login with session cookies (Redis-backed, 24h TTL).
- API token management: create (returns raw token ONCE), list (metadata only), revoke.
- Agent access with Bearer tokens (`athr_xxx`).
- 32B chat adapter over completion endpoint (not native chat).
- User token NOT forwarded to upstream — uses internal `BFF_*_UPSTREAM_AUTH_TOKEN`.
- Rate limiting preserved (Stage 06).
- Kubernetes Secret `aither-bff-auth` with 6 env vars.
- Example secret template (never commit real values).

**Evidence:**
- 20 evidence files in docs/mvp-roadmap/07-auth-api/evidence/
- Source code review: user token isolation confirmed
- Secret leak check: PASSED
- Forbidden scope check: PASSED
- Runtime evidence: PARTIALLY COLLECTED (VPN drop during evidence collection)

**Findings added in FINDINGS.md:**
- AUTH-01: COMPLETED BY HERMES
- AUTH-API-TOKEN-01: COMPLETED BY HERMES
- AUTH-TOKEN-HASH-01: PASSED
- AUTH-TOKEN-REVOKE-01: COMPLETED BY HERMES
- AUTH-AGENT-01: COMPLETED BY HERMES
- AUTH-UPSTREAM-01: PASSED (code review)
- AUTH-REDIS-FAIL-01: PARTIAL
- AUTH-TOKEN-PERSIST-01: PARTIAL
- AUTH-PORTAL-01: TARGET Stage 07.2
- AUTH-OAUTH-01: OUT OF SCOPE
- MODEL-32B-CHAT-ADAPTER-01: COMPLETED BY HERMES

**Open findings (unchanged from previous stages):**
- BFF-RL-REDIS-FAIL-01: PARTIAL
- BFF-RL-RESET-TTL-01: MINOR FINDING
- BFF-TOKEN-01: NOT COLLECTED
- BFF-AUTH-01: PARTIAL (functionally addressed by AUTH-01 but not closed until ChatGPT audit)

**Gate:**
- Stage 07.1: **WAITING FOR CHATGPT AUDIT**
- Stage 07.2 Portal: **NOT APPROVED**
- Stage 08: **NOT APPROVED**

---

## Stage 07.1 Corrective 1 — Auth runtime evidence, scope enforcement, source/manifest alignment

---

## Stage 07.1 Corrective 2 — Runtime evidence collection

**Date:** 2026-07-20
**Commit:** `0db08fb`
**Status before:** PARTIAL / CORRECTIVE REQUIRED

**Changes:**
1. Collected runtime evidence via Python from BFF pod (18 evidence files).
2. All runtime tests PASSED except rate-limit which returned PARTIAL (no 429 observed).
3. User token isolation confirmed at runtime.
4. Token storage safety confirmed: Redis HMAC-hash only.

**Evidence collected:**
- Rollout/pods: PASSED
- Health without auth: PASSED
- Models without token 401: PASSED
- Login success/wrong: PASSED
- Token create/list/revoke: PASSED
- Agent models with valid token: PASSED
- 14B/32B/32B-adapter BFF auth flow: PASSED (upstream returns 401 — test-only internal token)
- Wrong token 401: PASSED
- Rate limit 429: PARTIAL (no 429 observed; see Corrective 3)
- No secrets committed: PASSED
- No user token forwarding: PASSED

**Rate limit finding:**
Rate-limit test returned all 200 for 12 sequential requests. Possible window boundary crossing.
AUTH-RL-429-01 opened: "Rate limiting still returns 429 on BFF v0.4.0 after auth integration" — PARTIAL.

**Gate:**
- Stage 07.1: COMPLETED BY HERMES / WAITING FOR CHATGPT AUDIT (initially)
- Stage 07.2 Portal: NOT APPROVED
- Stage 08: NOT APPROVED

---

## Stage 07.1 Corrective 3 — Rate-limit retest and documentation alignment (Current)

**Date:** 2026-07-20
**Status before:** PARTIAL / CORRECTIVE REQUIRED (per GitHub connector audit of `0db08fb`)

**Reason:**
- Rate-limit retest required after Corrective 2 showed PARTIAL (no 429 observed).
- `auth-acceptance-report.md` had stale NOT COLLECTED labels and incorrect COMPLETED gate.
- `FINDINGS.md` needed AUTH-RL-429-01 and AUTH-UPSTREAM-VALID-01 findings.

**Changes:**
1. Rate-limit retest: NOT COLLECTED — VPN down (WireGuard peer unreachable).
2. `auth-acceptance-report.md`: Evidence Inventory updated with actual PASSED statuses from Corrective 2. Gate set to PARTIAL / WAITING FOR CHATGPT AUDIT.
3. `FINDINGS.md`: Added AUTH-RL-429-01 (NOT COLLECTED / RETEST BLOCKED VPN), AUTH-UPSTREAM-VALID-01 (PARTIAL). Updated AUTH-TOKEN-REVOKE-01, AUTH-AGENT-01, AUTH-UPSTREAM-01, AUTH-TOKEN-HASH-01 to PASSED with runtime confirmation. Updated MODEL-32B-CHAT-ADAPTER-01 to PASSED (adapter logic confirmed).
4. `CHAT_HANDOVER.md`: Stage 07.1 updated with runtime evidence status and new findings.
5. `current-mvp-status.md`: Auth/API Token status → PARTIAL WITH RUNTIME EVIDENCE / RATE LIMIT CORRECTION REQUIRED.
6. `AUDIT_LOG.md`: This entry added.
7. `CHATGPT_SESSION_LOG.md`: This entry added.

**Rate-limit status:** NOT COLLECTED (VPN prevents retest). No code change — rate-limit logic unchanged from Stage 06 (which confirmed 429 works). Need VPN-stable session for controlled burst test.

**Findings:**
- AUTH-RL-429-01: NOT COLLECTED / RETEST BLOCKED (VPN)
- AUTH-UPSTREAM-VALID-01: PARTIAL (test-only upstream tokens)
- All other Stage 07.1 findings: PASSED with runtime evidence or PARTIAL as documented

**Forbidden areas unchanged:**
- vLLM/GPU/TP/Gateway/Redis/Portal/OAuth/Monitoring/Stage 05 evidence/Stage 06 evidence: NOT MODIFIED

**Gate:**
```
Stage 07.1: PARTIAL / WAITING FOR CHATGPT AUDIT
Stage 07.2 Portal: NOT APPROVED
Stage 08: NOT APPROVED
```