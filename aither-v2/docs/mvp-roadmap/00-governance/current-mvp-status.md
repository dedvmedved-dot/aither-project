# Current MVP Status

Date: 2026-07-20

## Summary

| Area | Status | Evidence |
|---|---|---|
| Cluster/GPU | PASSED WITH FINDINGS | Stage 01 |
| GPU runtime | PASSED | Stage 01 |
| vLLM 14B | PASSED | docs/mvp-roadmap/02-inference-acceptance/vllm-service-inventory.md |
| vLLM 32B | PASSED WITH FINDINGS | docs/mvp-roadmap/02-inference-acceptance/32b-benchmark-report.md |
| Gateway | PASSED WITH FINDINGS | docs/mvp-roadmap/04-gateway/gateway-hardening-report.md |
| Benchmark | **PASSED** | docs/mvp-roadmap/02-inference-acceptance/LOAD_TEST_60MIN_REPORT.md |
| Streaming TTFT | PASSED WITH MINOR FINDINGS | docs/mvp-roadmap/02-inference-acceptance/streaming-ttft-report.md |
| TP=2 | POSTPONED / RISK ACCEPTED | docs/mvp-roadmap/03-tp2-decision/tp2-decision-report.md |
| BFF | **PASSED WITH FINDINGS / CONNECTOR VERIFIED** | docs/mvp-roadmap/05-bff/bff-acceptance-report.md |
| Redis RL | **PASSED WITH FINDINGS / CONNECTOR VERIFIED** | docs/mvp-roadmap/06-rate-limiting/redis-rate-limiting-report.md |
| Auth / API Token | **PASSED WITH FINDINGS / CONNECTOR VERIFIED** | docs/mvp-roadmap/07-auth-api/auth-acceptance-report.md |
| Portal (UI) | **PASSED WITH FINDINGS / CONNECTOR VERIFIED** | docs/mvp-roadmap/07-portal/portal-acceptance-report.md |
| **E2E (Portal→BFF→Model)** | **PASSED WITH FINDINGS / CONNECTOR VERIFIED** | docs/mvp-roadmap/08-end-to-end-acceptance/e2e-acceptance-report.md |
| Monitoring | PARTIAL | |
| VPN | DIAGNOSED | |

## Remaining findings (not blockers for MVP)

- GW-32B-REPLICA-01: nginx-gateway-32b has one replica in CrashLoopBackOff — PARTIAL
- GW-IMG-01: RISK ACCEPTED / PARTIAL
- GW-SC-01: PARTIAL
- AUTH-REDIS-FAIL-01: PARTIAL
- AUTH-TOKEN-PERSIST-01: PARTIAL
- BFF-RL-REDIS-FAIL-01: PARTIAL
- BFF-RL-RESET-TTL-01: MINOR FINDING
- PROD-READY-01: OPEN
- VPN/MTU instability (intermittent kubectl failures)
- No HA (single GPU node n7)
- No monitoring stack
- Model provenance not documented

## BM-01: RESOLVED

60-minute load test completed successfully (330/330 requests, 0 errors, 0 restarts, 0 OOM).

## Next approved stage

Stage 08: PASSED WITH FINDINGS / CONNECTOR VERIFIED
Stage 09: NOT APPROVED
PROD-READY-01: OPEN
