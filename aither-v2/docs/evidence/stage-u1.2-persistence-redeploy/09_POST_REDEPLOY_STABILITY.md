# 09_POST_REDEPLOY_STABILITY.md — Full 180-Test Gate

## Gate Configuration
- **Routes:** :30902 (Test Zone), :443 (Internet), :10443 (Internet)
- **Endpoints:** GET /v1/models, POST 14B chat, POST 32B chat
- **Tests per combination:** 20 sequential
- **Total requests:** 180
- **Inter-request delay:** 1.2s
- **Start:** 2026-07-24T21:37:30Z
- **End:** 2026-07-24T21:51:20Z
- **Duration:** 13m 50s

## Results

| Endpoint | Model | Requests | Pass | Fail | Avg Time | Max Time |
|---|---|---|---|---|---|---|
| Test Zone | GET /v1/models | 20 | 20 | 0 | 0.114s | 0.116s |
| Test Zone | POST 14B chat | 20 | 20 | 0 | 9.800s | 9.850s |
| Test Zone | POST 32B chat | 20 | 20 | 0 | 0.589s | 0.605s |
| Internet :443 | GET /v1/models | 20 | 20 | 0 | 0.076s | 0.127s |
| Internet :443 | POST 14B chat | 20 | 20 | 0 | 9.760s | 9.865s |
| Internet :443 | POST 32B chat | 20 | 20 | 0 | 0.545s | 0.590s |
| Internet :10443 | GET /v1/models | 20 | 20 | 0 | 0.075s | 0.124s |
| Internet :10443 | POST 14B chat | 20 | 20 | 0 | 9.759s | 9.855s |
| Internet :10443 | POST 32B chat | 20 | 20 | 0 | 0.546s | 0.589s |

| **TOTAL** | | **180** | **180** | **0** | | |

## Summary

```text
180/180 PASS
0 FAILURES
0 HTTP 5xx
0 TCP connection failures
0 unexplained timeouts
```

## Full Log
See `/tmp/full_gate_180.log` for complete per-request timings and HTTP codes.
