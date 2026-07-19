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
