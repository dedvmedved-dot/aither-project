# Aither / AI Hermes MVP Roadmap

## 1. Accepted stages

| Stage | Name | Status |
|---|---|---|
| 01 | Cluster/GPU Baseline | PASSED WITH FINDINGS |
| 02 | Inference Acceptance | PASSED WITH FINDINGS |
| 03 | TP=2 Decision | PASSED WITH MINOR CORRECTION REQUIRED |

## 2. Current stage

| Stage | Name | Goal |
|---|---|---|
| 04 | Gateway Hardening | Close or formalize GW-01, verify gateway auth, endpoint policy, securityContext, resources, image pinning, logs |

## 3. Planned MVP stages

| Stage | Name | Goal |
|---|---|---|
| 05 | BFF Acceptance | Route user traffic through BFF, verify BFF policy and gateway integration |
| 06 | Redis / Rate Limiting / Quotas | Add or document rate limiting, quota tracking, session/token controls |
| 07 | Portal Acceptance | Verify Portal uses BFF only and does not call vLLM directly |
| 08 | Security / Network Policy | Restrict direct internal access where possible |
| 09 | Monitoring / Observability | Metrics, logs, health probes, alerts |
| 10 | Failure / Recovery Tests | Restart, pod failure, rollout, rollback scenarios |
| 11 | RC1 Acceptance | End-to-end MVP release candidate audit |

## 4. Post-MVP

| Item | Status |
|---|---|
| TP=2 optimization | POSTPONED |
| Larger models | POST-MVP |
| Larger context | POST-MVP |
| Advanced autoscaling | POST-MVP |
| OAuth / full identity integration | POST-MVP unless explicitly re-approved |
