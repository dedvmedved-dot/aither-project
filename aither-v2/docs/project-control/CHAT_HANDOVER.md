# Chat Handover Context

Use this text to start a new ChatGPT project or chat.

```text
Project: Aither / AI Hermes MVP.

GitHub:
https://github.com/dedvmedved-dot/aither-project

Branch:
aither-v2

Working directory:
aither-v2/

Role of ChatGPT:
- technical architect;
- task author for Hermes + DeepSeek;
- external auditor;
- stage acceptance authority.

Role of Hermes:
- implementation;
- evidence collection;
- logs/reports creation;
- GitHub commits.

Current status:
Stage 01 — Cluster/GPU Baseline: PASSED WITH FINDINGS.
Stage 02 — Inference Acceptance: PASSED WITH FINDINGS.
Stage 03 — TP=2 Decision: PASSED WITH MINOR CORRECTION REQUIRED.
Stage 04 — Gateway Hardening: PASSED WITH FINDINGS / CONNECTOR VERIFIED.
Stage 04.1 — Repository Integrity Verification: PASSED / CONNECTOR VERIFIED.
Stage 05 — BFF Acceptance: PASSED WITH FINDINGS / CONNECTOR VERIFIED.
   - ChatGPT audit of commit 8219c56 confirmed: BFF implementation, routing, status code propagation, bypass prevention, no secrets committed.
   - Open findings: BFF-TOKEN-01 (NOT COLLECTED), BFF-AUTH-01 (PARTIAL).
Stage 06 — Redis / Rate Limiting: PASSED WITH FINDINGS / CONNECTOR VERIFIED.
   - Redis-backed fixed-window rate limiting with 10 req/60s default.
   - HTTP 429 on exceeded limit (confirmed).
   - Rate limit by SHA-256(token hash) or client IP.
   - No raw tokens stored in Redis (confirmed).
   - Redis unavailable: fail-open.
   - Open findings: BFF-RL-REDIS-FAIL-01 (PARTIAL), BFF-RL-RESET-TTL-01 (MINOR FINDING), BFF-TOKEN-01 (NOT COLLECTED), BFF-AUTH-01 (PARTIAL).
Stage 07.1 — Auth / API Token / Agent Access Baseline: COMPLETED BY HERMES / WAITING FOR CHATGPT AUDIT.
   - BFF central auth with admin login, API token management, agent access.
   - 32B chat adapter over completion endpoint.
   - User token NOT forwarded to upstream.
   - Open findings: AUTH-REDIS-FAIL-01 (PARTIAL), AUTH-TOKEN-PERSIST-01 (PARTIAL).
   - Old Stage 07 Portal-only task: SUPERSEDED.
Stage 07.2 Portal: NOT APPROVED.
Stage 08: NOT APPROVED.

Stage 05 status details:
- BFF deployed: 1/1 Running, FastAPI on python:3.11-slim
- CrashLoopBackOff root cause: pip install without --user under runAsUser=1000 — FIXED
- Implementation mismatch nginx→FastAPI: RESOLVED (deployment matches app.py)
- /health: 200 ✅
- 14B chat via BFF (no auth): 401 — upstream auth required, status code propagated correctly ✅
- 32B completion via BFF (no token): 401 — gateway auth required, status code propagated correctly ✅
- 32B completion via BFF (valid token): NOT COLLECTED (VPN instability) ❌
- 32B chat blocked: 422 ✅
- Unknown model blocked: 400 ✅
- Direct vLLM bypass: NOT PRESENT ✅
- No secrets committed: PASSED ✅
- vLLM/GPU/TP/Gateway runtime/Portal/Redis/OAuth: NOT MODIFIED ✅
- Rate limiting: IMPLEMENTED in Stage 06
- Stage 06: PASSED WITH FINDINGS / CONNECTOR VERIFIED

Evidence directory: docs/mvp-roadmap/05-bff/evidence/ (14 files)

Key decisions:
TP=1 accepted for MVP.
TP=2 postponed to Post-MVP Optimization.
OAuth removed from immediate MVP.
Gateway accepted with findings (GW-IMG-01, GW-SC-01, GW-RL-01).
Direct vLLM 32B access is not user-facing for MVP.
Hermes must not change vLLM/GPU/TP/BFF/Portal/Redis/OAuth outside approved scope.

Repository access:
ChatGPT repository access was restored via GitHub connector/API.
Use GitHub connector/API for future audits instead of relying only on raw/blob web fetch.

Audit rule:
No transition to the next stage without external ChatGPT audit.

Hermes behavior rules:
- evidence first, conclusion second;
- do not overstate status;
- do not hide failures;
- preserve logs and evidence;
- use raw GitHub links;
- report all PARTIAL/FAILED findings.
```
