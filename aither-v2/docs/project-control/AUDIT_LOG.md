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

---

## Stage 07.1 Corrective 5 — Controlled rate-limit 429 retest

**Date:** 2026-07-20
**Status before:** PARTIAL WITH RUNTIME EVIDENCE / RATE LIMIT CORRECTION REQUIRED

**Reason:**
- AUTH-RL-429-01 remained NOT COLLECTED / RETEST BLOCKED (VPN).
- Required controlled burst test with window sync, Redis key cleanup, and 15-request burst.
- Stage 07.1 cannot be completed without confirming rate-limit 429 after auth integration.

**Retest attempt:**
1. Checked WireGuard: peer 170.168.91.95 unreachable, 0 B received, no handshake.
2. wg-quick down/up attempted — handshake still fails (peer not reachable on public IP).
3. VPN status: DOWN — cluster 10.129.13.78:6443 inaccessible.

**Result: NOT COLLECTED**
AUTH-RL-429-01: NOT COLLECTED / RETEST BLOCKED (VPN)

**Forbidden areas unchanged:**
- vLLM/GPU/TP/Gateway/Redis/Portal/OAuth/Monitoring/Stage 05 evidence/Stage 06 evidence: NOT MODIFIED
- tools/bff/app.py: NOT MODIFIED
- bff-mvp.yaml: NOT MODIFIED

**Gate:**
```
Stage 07.1: PARTIAL / WAITING FOR CHATGPT AUDIT (rate-limit retest VPN-blocked)
Stage 07.2 Portal: NOT APPROVED
Stage 08: NOT APPROVED
```

---

## Stage 07.1 Corrective 6 — Infrastructure Access Recovery / VPN Fix + AUTH-RL-429 retest

**Date:** 2026-07-20
**Status before:** PARTIAL WITH RUNTIME EVIDENCE / RATE LIMIT CORRECTION REQUIRED

**Reason:**
- AUTH-RL-429-01 remained NOT COLLECTED / RETEST BLOCKED (VPN).
- Corrective 3 and 5 could not run controlled retest because VPN/WireGuard was unavailable.

**VPN recovery:**
- WireGuard interface wg0: Lost handshake (0 B received).
- tun0 (OpenVPN-like) still provided route to 10.129.0.0/16.
- Kubernetes API server 10.129.13.78:6443 reachable via tun0.
- kubectl fully functional after tun0 route used.

**Kubernetes access:** RESTORED
- BFF pod: aither-bff-6fd96f6758-m7zj5, 1/1 Running
- Redis pod: aither-redis-rate-limit-754cdd9784-rnf45, 1/1 Running
- Secret issue: ADMIN_PASSWORD_HASH was corrupted by incorrect patch — fixed by proper base64 encoding.
- BFF pod recreated with fix.

**Rate-limit retest:**
1. Created dedicated test token via admin login.
2. Token redacted: athr_DwaIzEt...REDACTED.
3. RL hash computed: bef86509c0e47bc53822428088099eb8cc1bd452668cd56b51a379d16e5236b3.
4. Window sync: burst started at second 40 (< 45), window ID 29742434.
5. 15 rapid GET /api/v1/models with Bearer token.
6. Results: Req 1-10 → HTTP 200, Req 11-15 → HTTP 429.
7. Redis counter: 15. TTL: 28 seconds.

**AUTH-RL-429-01: PASSED**

**Evidence collected:**
- vpn-access-recovery-check.txt
- rate-limit-still-works-429.txt (updated with PASSED result)

**Runtime code changed:** NO (tools/bff/app.py and bff-mvp.yaml: NOT MODIFIED)

**Forbidden areas unchanged:**
- vLLM/GPU/TP/Gateway/Redis/Portal/OAuth/Monitoring/Stage 05 evidence/Stage 06 evidence: NOT MODIFIED

**Gate:**
```
Stage 07.1: COMPLETED BY HERMES / WAITING FOR CHATGPT AUDIT
Stage 07.2 Portal: NOT APPROVED
Stage 08: NOT APPROVED
```

---

## Stage 07.1 — External ChatGPT Audit Acceptance

**Date:** 2026-07-20
**Commit audited:** `1455dbd3650230ca5e770d50f98c77b5b73efb00`
**Method:** GitHub connector

**Decision:**
- Stage 07.1 — Auth / API Token / Agent Access Baseline: **PASSED WITH FINDINGS / CONNECTOR VERIFIED**
- AUTH-RL-429-01: **PASSED / CONNECTOR VERIFIED**
- Stage 07.2 Portal: **READY FOR TASK PREPARATION, NOT STARTED**
- Stage 08: **NOT APPROVED**

**Evidence accepted:**
- Controlled rate-limit 429 retest: burst 15 reqs, 10×200 + 5×429, Redis counter=15, TTL=28s.
- VPN access recovery via tun0 alternative route.
- All runtime evidence: rollout, pods, health, login, token lifecycle, agent auth, scope enforcement.
- User token isolation and no secrets committed confirmed.

**Open findings (retained):**
- AUTH-UPSTREAM-VALID-01 — PARTIAL
- AUTH-REDIS-FAIL-01 — PARTIAL
- AUTH-TOKEN-PERSIST-01 — PARTIAL
- AUTH-PORTAL-01 — TARGET Stage 07.2
- AUTH-OAUTH-01 — OUT OF SCOPE / FUTURE
- BFF-RL-REDIS-FAIL-01 — PARTIAL
- BFF-RL-RESET-TTL-01 — MINOR FINDING
- BFF-TOKEN-01 — NOT COLLECTED
- BFF-AUTH-01 — PARTIAL

**Gate:**
```
Stage 07.1: PASSED WITH FINDINGS / CONNECTOR VERIFIED
Stage 07.2 Portal: READY FOR TASK PREPARATION
Stage 08: NOT APPROVED
```

---

## Stage 07.2 — Portal UI with Auth, Token Management and Chat Access — External Audit Result

**Date:** 2026-07-20
**Commit audited:** `03b1a1bf604fbfb15ab798d61c9867de5cba35d2`
**Method:** GitHub connector (raw content verification)

**Decision:**
- Stage 07.2 Corrective 2: **PASSED / CONNECTOR VERIFIED**
- PORTAL-CM-ALIGN-01: **PASSED / CONNECTOR VERIFIED**
- Stage 07.2 Portal: **PASSED WITH FINDINGS / CONNECTOR VERIFIED**
- Stage 08: **NOT APPROVED**

**Accepted evidence:**
1. Portal deployed and accessible.
2. Portal uses BFF-only reverse proxy.
3. Login/logout/me work through BFF.
4. Token create/list/revoke UI works.
5. Raw token shown once and not persisted.
6. Token list renders from BFF {"tokens":[...]}.
7. Model selector renders from BFF {"models":[...]}.
8. Navigation works via App.showPage().
9. 32B is labeled as chat adapter over completion.
10. portal-mvp.yaml inline ConfigMap matches tools/portal/*.
11. SHA256 alignment: index.html/app.js/styles.css/nginx.conf all MATCH.
12. Forbidden runtime areas were not modified.

**Open findings (retained):**
- AUTH-UPSTREAM-VALID-01 — PARTIAL
- AUTH-REDIS-FAIL-01 — PARTIAL
- AUTH-TOKEN-PERSIST-01 — PARTIAL
- AUTH-OAUTH-01 — OUT OF SCOPE / FUTURE
- BFF-RL-REDIS-FAIL-01 — PARTIAL
- BFF-RL-RESET-TTL-01 — MINOR FINDING
- BFF-TOKEN-01 — NOT COLLECTED
- BFF-AUTH-01 — PARTIAL
- PROD-READY-01 — OPEN

**Gate after audit:**
```
Stage 07.2: PASSED WITH FINDINGS / CONNECTOR VERIFIED
Stage 08: NOT APPROVED
```

---

## Stage 08 — MVP End-to-End Runtime Acceptance

**Date:** 2026-07-20
**Commit:** 945d07d → (pending Stage 08 commit)
**Method:** GitHub connector (post-execution)

**Decision (pending ChatGPT audit):**
- Stage 08: PARTIAL / WAITING FOR CHATGPT AUDIT
- Upstream model responses not confirmed (AUTH-UPSTREAM-VALID-01: PARTIAL)

**Evidence collected:**
1. Portal deployment and health: PASSED
2. Login/session: PASSED
3. Token create/list/revoke/blocked: PASSED
4. Models with Bearer token: PASSED
5. 14B chat BFF flow: PASSED (upstream 401 — now resolved in Corrective 1)
6. 32B completion BFF flow: PASSED (upstream 401 — now resolved in Corrective 1)
7. 32B chat adapter BFF flow: PASSED (upstream 401 — now resolved in Corrective 1)
8. Rate limit 429 after full auth stack: PASSED
9. No secrets committed: PASSED
10. Forbidden zones unchanged: PASSED

**E2E Acceptance Report:** docs/mvp-roadmap/08-end-to-end-acceptance/e2e-acceptance-report.md

**Gate after Stage 08:**
```
Stage 08: PARTIAL / WAITING FOR CHATGPT AUDIT
Stage 09: NOT APPROVED
```

---

## Stage 08 Corrective 1 — Upstream Internal Auth Resolution

**Date:** 2026-07-20
**Commit:** (this commit)
**Method:** Runtime Secret patch + BFF rollout + model response retest

**Root cause:** BFF's upstream auth tokens (`BFF_14B_UPSTREAM_AUTH_TOKEN`, `BFF_32B_GATEWAY_AUTH_TOKEN`) were test-only values (length 23, `test-upstream-token-14b`/`test-upstream-token-32b`). The real upstream auth key is stored in Secret `vllm-api-key`/`VLLM_API_KEY` (length 64).

**Runtime operation:**
1. Secret inventory checked: `aither-bff-auth` (exists), `vllm-api-key` (exists).
2. `BFF_14B_UPSTREAM_AUTH_TOKEN` and `BFF_32B_GATEWAY_AUTH_TOKEN` patched with real `VLLM_API_KEY` value via `kubectl patch secret`.
3. BFF rollout restarted: `kubectl rollout restart deployment/aither-bff`.
4. New pod: `aither-bff-656ff579b9-9m2m6`, 1/1 Running, /health → HTTP 200.
5. Model response retest with Portal proxy (correct scope tokens):

| Endpoint | HTTP | Response |
|---|---|---|
| 14B chat (model:14b:chat scope) | 200 | "Hello from 14b" |
| 32B completion (model:32b:completion scope) | 200 | "Hello from 32b." |
| 32B chat adapter (model:32b:chat-adapter scope) | 200 | "Hello from 32b adapter" |

**Note:** 32B chat adapter requires scope `model:32b:chat-adapter` (not `model:32b:chat`).

**Findings resolved:**
- `AUTH-UPSTREAM-VALID-01`: PARTIAL → COMPLETED BY HERMES / WAITING FOR CHATGPT AUDIT
- `BFF-TOKEN-01`: NOT COLLECTED → COMPLETED BY HERMES / WAITING FOR CHATGPT AUDIT
- `E2E-14B-CHAT-01`: PARTIAL → COMPLETED BY HERMES / WAITING FOR CHATGPT AUDIT
- `E2E-32B-COMPLETION-01`: PARTIAL → COMPLETED BY HERMES / WAITING FOR CHATGPT AUDIT
- `E2E-32B-CHAT-ADAPTER-01`: PARTIAL → COMPLETED BY HERMES / WAITING FOR CHATGPT AUDIT
- `PORTAL-CHAT-14B-01`: UPSTREAM AUTH NOT TESTED → PASSED (real response)
- `PORTAL-CHAT-32B-ADAPTER-01`: UPSTREAM AUTH NOT TESTED → PASSED (real response)

**Evidence (8 new files):**
- e2e-upstream-auth-secret-inventory.txt
- e2e-bff-rollout-after-secret-update.txt
- e2e-14b-chat-response-retest.txt
- e2e-32b-completion-response-retest.txt
- e2e-32b-chat-adapter-response-retest.txt
- e2e-auth-upstream-valid-summary.txt
- e2e-no-secret-leak-check-corrective-1.txt
- e2e-forbidden-scope-check-corrective-1.txt

**Forbidden areas unchanged:**
- tools/bff/app.py: NOT MODIFIED
- tools/portal/*: NOT MODIFIED
- bff-mvp.yaml / portal-mvp.yaml: NOT MODIFIED
- vLLM/GPU/TP/Gateway/Redis/OAuth/Monitoring: NOT MODIFIED
- Stage 05/06/07.1/07.2 evidence: NOT MODIFIED
- Secret values NOT committed

**Gate:**
```
Stage 08: COMPLETED BY HERMES / WAITING FOR CHATGPT AUDIT
Stage 09: NOT APPROVED
```