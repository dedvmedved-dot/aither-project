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
Stage 07.1 — Auth / API Token / Agent Access Baseline: PASSED WITH FINDINGS / CONNECTOR VERIFIED.
   - BFF central auth with admin login, API token management, agent access.
   - 32B chat adapter over completion endpoint.
   - User token NOT forwarded to upstream.
   - Runtime evidence collected: rollout, pods, health, login, token lifecycle, agent auth, rate-limit 429 all PASSED.
   - AUTH-RL-429-01: PASSED / CONNECTOR VERIFIED — controlled burst test confirmed HTTP 429 after 10th request (15 reqs, counter=15, TTL=28s).
   - Findings: AUTH-UPSTREAM-VALID-01 (PARTIAL), AUTH-REDIS-FAIL-01 (PARTIAL), AUTH-TOKEN-PERSIST-01 (PARTIAL).
   - Old Stage 07 Portal-only task: SUPERSEDED.
Stage 07.2 Portal: COMPLETED BY HERMES / WAITING FOR CHATGPT AUDIT (Corrective 1 applied).
   - nginx:alpine portal deployed, 1/1 Running.
   - Login/logout/me via BFF session auth.
   - Token management: create (once), list (metadata only), revoke.
   - Chat UI: 14B native + 32B adapter through BFF.
   - API Access / Agent guide page.
   - Portal uses BFF only — no direct vLLM/Gateway access.
   - Raw tokens NOT persisted in browser storage.
   - 32B correctly labeled as chat adapter over completion.
   - Corrective 1 fixes applied:
     * loadTokens() now correctly reads {"tokens":[...]} from BFF response.
     * loadModels() now correctly reads {"models":[...]} from BFF response.
     * showPage() exported in window.App for all navigation links.
     * All onclick handlers use App.showPage() — no ReferenceError.
     * ConfigMap recreated from source files — alignment verified.
   - New evidence: portal-ui-token-list-render-check.txt (PASSED), portal-ui-model-select-render-check.txt (PASSED), portal-ui-navigation-check.txt (PASSED).
   - Open findings: 3 PORTAL-UI-* findings added (COMPLETED BY HERMES / WAITING FOR CHATGPT AUDIT).
   - Corrective 2 (manifest alignment) applied:
     * portal-mvp.yaml inline ConfigMap now MATCHES tools/portal/* (SHA256 verified: index.html, app.js, styles.css, nginx.conf all MATCH).
     * ConfigMap synced to cluster; portal pod restarted with corrected code.
     * Finding PORTAL-CM-ALIGN-01 added (COMPLETED BY HERMES / WAITING FOR CHATGPT AUDIT).
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
