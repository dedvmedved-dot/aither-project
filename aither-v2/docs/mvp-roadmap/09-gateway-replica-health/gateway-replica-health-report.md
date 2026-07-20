# Gateway Replica Health Report

## Stage 09 — nginx-gateway-32b Replica Health / CrashLoopBackOff Remediation

### Summary

| Aspect | Result |
|---|---|
| Initial state | 1/2 Ready, 1 CrashLoopBackOff (242 restarts, 20h) |
| Root cause | nginx.conf used hostname `vllm-32b-gptq.aither-inference.svc`; нода n7 без ClusterDNS |
| Remediation | ConfigMap nginx-gateway-32b updated: hostname → ClusterIP `10.99.3.103` |
| Final state | 2/2 Ready, 2 Available, 0 CrashLoopBackOff |
| Regression: 32B completion | ✅ HTTP 200, non-empty response |
| Regression: 32B chat adapter | ✅ HTTP 200, adapter over completion |

### Evidence Inventory

| Evidence | Status |
|---|---|
| gw32b-initial-pod-state.txt | PASSED |
| gw32b-crashing-pod-describe.txt | PASSED |
| gw32b-crashing-pod-logs.txt | PASSED |
| gw32b-root-cause.txt | PASSED |
| gw32b-remediation-actions.txt | PASSED |
| gw32b-rollout-status-after.txt | PASSED |
| gw32b-pods-after.txt | PASSED |
| gw32b-events-after.txt | PASSED |
| gw32b-32b-completion-still-200.txt | PASSED |
| gw32b-32b-chat-adapter-still-200.txt | PASSED |
| gw32b-no-secret-leak-check.txt | PASSED |
| gw32b-forbidden-scope-check.txt | PASSED |

### Final Gateway State

| Metric | Value |
|---|---|
| Desired replicas | 2 |
| Ready replicas | 2 |
| Available replicas | 2 |
| CrashLoopBackOff pods | 0 |
| ImagePullBackOff pods | 0 |
| Pod names | nginx-gateway-32b-5d447469b9-28kng (n7), nginx-gateway-32b-5d447469b9-pvxtq (n8) |
| Pod statuses | 1/1 Running (both) |
| Restart counts | 0 (new pod), 0 (existing pod) |

### External ChatGPT Audit Decision

**Date:** 2026-07-20
**Commit audited:** c1d1f1953d6167a67ead7ad6153b379a656c24e1
**Method:** GitHub connector

**Decision:**
- Stage 09: **PASSED WITH FINDINGS / CONNECTOR VERIFIED**
- GW-32B-REPLICA-01: **RESOLVED / CONNECTOR VERIFIED**
- Stage 10: **NOT APPROVED**
- PROD-READY-01: **OPEN**

**Accepted evidence:**
- Root cause confirmed: nginx hostname resolution failed on n7 due MissingClusterDNS.
- nginx logs confirmed host not found in upstream.
- Runtime ConfigMap patch changed proxy_pass hostname to ClusterIP 10.99.3.103.
- Runtime ConfigMap patch was not committed.
- Final gateway state: 2/2 Running, 2/2 Ready, 0 CrashLoopBackOff.
- 32B completion regression: HTTP 200.
- 32B chat adapter regression: HTTP 200.
- Forbidden scope check: PASSED.
- No secret leak check: PASSED.

### Remaining Findings

| Finding | Status |
|---|---|
| DNS-N7-01 | PARTIAL (MissingClusterDNS on node n7) |
| GW-RUNTIME-CM-01 | PARTIAL (runtime ConfigMap differs from GitHub source-of-truth) |
| GW-CLUSTERIP-01 | RISK ACCEPTED / PARTIAL (hardcoded ClusterIP workaround) |
| GW-IMG-01 | RISK ACCEPTED / PARTIAL |
| GW-SC-01 | PARTIAL |
| AUTH-REDIS-FAIL-01 | PARTIAL |
| AUTH-TOKEN-PERSIST-01 | PARTIAL |
| BFF-RL-REDIS-FAIL-01 | PARTIAL |
| BFF-RL-RESET-TTL-01 | MINOR FINDING |
| PROD-READY-01 | OPEN |

### Gate

```
Stage 09: PASSED WITH FINDINGS / CONNECTOR VERIFIED
Stage 10: NOT APPROVED
PROD-READY-01: OPEN
```
