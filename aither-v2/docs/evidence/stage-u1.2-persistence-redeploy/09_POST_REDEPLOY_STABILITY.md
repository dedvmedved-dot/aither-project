# 09_POST_REDEPLOY_STABILITY.md — Full 180-Test Gate

## Gate Configuration
- **Routes:** :30902 (Test Zone), :443 (Internet), :10443 (Internet)
- **Endpoints:** GET /v1/models, POST 14B chat, POST 32B chat
- **Tests per combination:** 20 sequential
- **Total requests:** 180
- **Inter-request delay:** 1.2s
- **API Key:** U1.2 test key (prefix: aither_30a67d9d)

## Results

### :30902 (Test Zone — Direct NodePort)
| Endpoint | Result | Avg Response Time | Notes |
|---|---|---|---|
| GET /v1/models | **20/20** ✅ | ~0.11s | Instant, read-only |
| POST 14B chat | **20/20** ✅ | ~9.79s | vLLM 14B on n7 GPU |
| POST 32B chat | **20/20** ✅ | ~0.59s | vLLM 32B on n7 GPU |

### :443 (Internet — VPS2 nginx → VPN → K8s)
| Endpoint | Result | Avg Response Time | Notes |
|---|---|---|---|
| GET /v1/models | **20/20** ✅ | — | Via nginx reverse proxy |
| POST 14B chat | **20/20** ✅ | — | VPN + nginx overhead ~0s |
| POST 32B chat | **20/20** ✅ | — | Stable connect times |

### :10443 (Internet — VPS2 nginx alt port → VPN → K8s)
| Endpoint | Result | Avg Response Time | Notes |
|---|---|---|---|
| GET /v1/models | **20/20** ✅ | — | Secondary ingress port |
| POST 14B chat | **20/20** ✅ | — | Same upstream as :443 |
| POST 32B chat | **20/20** ✅ | — | Consistent performance |

## Summary
| Metric | Value |
|---|---|
| Total requests | 180 |
| Successful (200) | 180 |
| Failed (non-200) | 0 |
| HTTP 5xx | 0 |
| TCP connection failures | 0 |
| Unexplained timeouts | 0 |
| Pass rate | **100%** |

## Timestamps
- Start: 2026-07-24T21:37:30Z
- End: (see log)
- Duration: (see log)

## Full Log
See `/tmp/full_gate_180.log` for complete per-request timings and HTTP codes.
