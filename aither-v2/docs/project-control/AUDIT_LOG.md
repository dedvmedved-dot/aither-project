# Audit Log

## Stage 01 — Cluster/GPU Baseline

Status: PASSED WITH FINDINGS

Summary:
- GPU runtime was proven.
- Cluster baseline was proven.
- Gateway remained PARTIAL.
- Benchmark moved to Stage 02.

## Stage 02 — Inference Acceptance

Status: PASSED WITH FINDINGS

Accepted evidence:
- 60-minute load test duration: 3607s.
- 14B: 330/330.
- 32B: 330/330.
- Gateway: 66/66.
- HTTP errors: 0.
- Timeouts: 0.
- Pod restarts: 0.
- GPU OOM: 0.
- BM-01: RESOLVED.

Findings:
- Gateway remained PARTIAL.
- Streaming TTFT accepted with minor findings.

## Stage 03 — TP=2 Decision

Status: PASSED WITH MINOR CORRECTION REQUIRED

Accepted decision:
- TP=1 accepted for MVP.
- TP=2 postponed to Post-MVP Optimization.

Minor correction:
- Replace unsupported NCCL statement with:
  "NCCL usage observed: not proven; no explicit NCCL lines in collected grep/logs; not required for TP=1 MVP decision."

## Stage 04 — Gateway Hardening

Status: PASSED WITH FINDINGS / CONNECTOR VERIFIED

Summary:
- GW-01: RESOLVED.
- Gateway auth: no token 401, wrong token 401, valid token 200.
- Chat blocked: 422, Completion: 200.
- SecurityContext: PARTIAL (runAsNonRoot/readOnlyRootFilesystem not enabled).
- Image pinning: PARTIAL (version tag, digest failed over VPN).
- Rate limiting: POSTPONED to Stage 06.
- Direct 32B policy: ACCEPTED FOR MVP INTERNAL SCOPE.
- vLLM/BFF/Portal/Redis/OAuth/TP: NOT MODIFIED.

## Stage 04.1 — Repository Integrity Verification

Status: PASSED / CONNECTOR VERIFIED

Summary:
- Commit 448f262 exists and is in branch aither-v2.
- git fsck passed with dangling objects only.
- Stage 04 files exist and are non-empty.
- SHA256 hashes generated.
- Hardened YAML parses as 3 documents: ConfigMap, Deployment, Service.
- Key content present: GW-01, RESOLVED, auth checks, NCCL correction.

Conclusion:
Repository corruption was not confirmed. Previous raw/blob access issue was external fetch/cache/tool limitation.

## Repository Access Restoration

Status: RESTORED VIA GITHUB CONNECTOR

Summary:
- ChatGPT connected to GitHub through connector/API.
- Repository dedvmedved-dot/aither-project is public.
- ChatGPT has read-only pull access.
- ChatGPT verified Stage 04, Stage 04.1, current MVP status, TP=2 decision report, handover, and hardened gateway manifest.

## Stage 05 — BFF Acceptance (Corrective)

Status: PARTIAL / WAITING FOR CHATGPT AUDIT

Summary:
- Original commit 2ab4485 received PARTIAL / CORRECTIVE REQUIRED from ChatGPT audit.
- Root cause of CrashLoopBackOff: pip install without --user flag under runAsUser=1000.
- Fix: added HOME=/tmp and --user flag to pip install command.
- BFF deployed: 1/1 Running, 0 restarts, python:3.11-slim + FastAPI.
- Implementation mismatch resolved: deployment now matches tools/bff/app.py.
- Health: ✅ 200
- 14B chat: ✅ 200 (route confirmed, upstream auth needed)
- 32B completion (no token): ✅ 200 (route confirmed, gateway auth needed)
- 32B completion (valid token): ❌ NOT COLLECTED (VPN instability prevented secret retrieval)
- 32B chat blocked: ✅ 422
- Unknown model blocked: ✅ 400
- Direct vLLM bypass: ✅ NOT PRESENT
- No secrets committed: ✅ PASSED
- Allowed scope respected: vLLM/GPU/TP/Gateway/Portal/Redis/OAuth NOT modified.
- Stage 06 NOT started.

Evidence:
- 14 evidence files created in docs/mvp-roadmap/05-bff/evidence/
- Reports updated: bff-acceptance-report, bff-routing-policy, bff-security-notes, bff-inventory-report
- Status files updated: current-mvp-status, FINDINGS, PROJECT_MASTER, CHAT_HANDOVER, AUDIT_LOG

Findings added in FINDINGS.md:
- BFF-01 RESOLVED
- BFF-IMPL-01 RESOLVED
- BFF-ROUTE-01 PASSED
- BFF-CHAT-32B-01 PASSED
- BFF-DIRECT-01 PASSED
- BFF-RL-01 POSTPONED
- BFF-AUTH-01 PARTIAL
- BFF-SEC-01 PASSED
- BFF-TOKEN-01 NOT COLLECTED

## Stage 05 — BFF Acceptance (Corrective 2: status code propagation)

Status: PARTIAL / WAITING FOR CHATGPT AUDIT

Summary:
- Previous commit 0a2340f received PARTIAL / CORRECTIVE REQUIRED due to:
  BFF returning HTTP 200 for upstream 401/403 errors instead of real status codes.
- Fix applied to app.py and ConfigMap: both /api/v1/chat and /api/v1/completions handlers
  now return `Response(content=..., status_code=resp.status_code, ...)`.
- Verified: 14B chat no auth → HTTP 401 (was 200)
- Verified: 32B completion no auth → HTTP 401 (was 200)
- Verified: 32B chat blocked → HTTP 422 (unchanged)
- Verified: unknown model → HTTP 400 (unchanged)
- Verified: health → HTTP 200 (unchanged)
- Valid token test still NOT COLLECTED (VPN instability).
- Allowed scope respected: vLLM/GPU/TP/Gateway/Portal/Redis/OAuth NOT modified.
- Stage 06 NOT started, BLOCKED.

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
