# Stability Gate Results

## Final Gate: 20/20 Sequential (all routes)

| Entry Point | Endpoint | Model | Result |
|---|---|---|---|
| :30902 | GET /v1/models | — | **20/20** ✅ |
| :30902 | POST chat | 14B | **20/20** ✅ |
| :30902 | POST chat | 32B | **20/20** ✅ |
| :443 | GET /v1/models | — | **20/20** ✅ |
| :443 | POST chat | 14B | **20/20** ✅ |
| :443 | POST chat | 32B | **20/20** ✅ |
| :10443 | GET /v1/models | — | **20/20** ✅ |
| :10443 | POST chat | 14B | **20/20** ✅ |
| :10443 | POST chat | 32B | **20/20** ✅ |

**Total sequential: 180/180 PASS**

## Concurrency: 50 Requests

| Concurrency | Result |
|---|---|
| 1 | 5/5 ✅ |
| 2 | 10/10 ✅ |
| 3 | 15/15 ✅ |
| 4 | 20/20 ✅ |

**Total concurrent: 50/50 PASS**

## Overall: 230/230 PASS | 0 HTTP 5xx | 0 TCP failures | 0 unexplained timeouts
