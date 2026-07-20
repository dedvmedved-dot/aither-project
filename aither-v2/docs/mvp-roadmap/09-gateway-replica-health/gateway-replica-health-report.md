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

### Decision before ChatGPT audit

```
Stage 09: COMPLETED BY HERMES / WAITING FOR CHATGPT AUDIT
PROD-READY-01: OPEN
```
