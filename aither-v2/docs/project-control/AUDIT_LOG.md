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

Status: NOT AUDITED

Expected:
- Close or formalize GW-01.
- Verify gateway auth.
- Verify completion endpoint.
- Verify chat endpoint blocked.
- Verify hardening evidence.
