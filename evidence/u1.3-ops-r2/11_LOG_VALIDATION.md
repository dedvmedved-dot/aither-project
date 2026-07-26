# U1.3-OPS-R2 — 11_LOG_VALIDATION

**Date/Time (UTC):** 2026-07-26T02:15:09Z

## Scan Results

Scanned all Running pods (excluded test-/Completed pods) for 14 error patterns.

| Pod | Restarts | Error Matches |
|-----|----------|---------------|
| aither-ai-platform-84c478c874-75plb | 0 | 0 |
| aither-bff-64cb8c55b4-fz9s7 | 0 | 0 |
| aither-bff-64cb8c55b4-tv4h7 | 0 | 0 |
| aither-identity-67b5994997-2jdvd | 0 | 0 |
| aither-portal-6c445cc9f-44dzd | 0 | 0 |
| aither-portal-backend-559754567d-599kk | 0 | 0 |
| aither-portal-frontend-5cc6d99997-btksr | 0 | 0 |
| aither-redis-rate-limit-754cdd9784-stnl6 | 0 | 0 |
| nginx-gateway-32b-65786797-k8skw | 0 | 0 |
| nginx-gateway-32b-65786797-px4rz | 0 | 0 |
| vllm-14b-instruct-7f6f784dcb-g2h5d | 0 | 0 |
| vllm-32b-gptq-7d6dc7c64-r82nh | 0 | 0 |

## Patterns Scanned

Traceback, panic, fatal, Unhandled, ReferenceError, TypeError, CrashLoop, segmentation fault, OutOfMemory, OOMKilled, authentication failed, permission denied, x509, certificate verify failed

## Log Validation: PASS

- 0 critical error pattern matches
- 0 container restarts across all pods
- 12/12 pods scanned

Raw log: `logs/11-log-scan.log`
