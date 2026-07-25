# CB-01 Controlled Load Evidence

**Timestamp:** 2026-07-25 00:58 UTC

## Test Configuration
- 2 concurrent users (BETA-USER-01, BETA-USER-02)
- 10 requests per user, parallel
- Models: qwen-14b (U1), qwen-32b-base (U2)
- Endpoint: POST /v1/chat/completions
- Duration: 49.9 seconds

## Raw Results

### User 1 (14B) — 10 requests
| Req | HTTP | Time (s) | Response |
|---|---|---|---|
| R4 | 200 | 5.39 | "Hello! How can I" |
| R7 | 200 | 10.31 | "Hello! How can I" |
| R5 | 200 | 15.24 | "Hello! How can I" |
| R1 | 200 | 20.17 | "Hello! How can I" |
| R3 | 200 | 25.09 | "Hello! How can I" |
| R6 | 200 | 30.01 | "Hello! How can I" |
| R9 | 200 | 34.93 | "Hello! How can I" |
| R2 | 200 | 39.94 | "Hello! How can I" |
| R10 | 200 | 44.89 | "Hello! How can I" |
| R8 | 200 | 49.83 | "Hello! How can I" |

### User 2 (32B) — 10 requests
| Req | HTTP | Time (s) | Response |
|---|---|---|---|
| R3 | 200 | 0.55 | Chinese text |
| R2 | 200 | 0.74 | "an all, I'm" |
| R1 | 200 | 0.98 | "and welcome to this edition" |
| R5 | 200 | 1.23 | Chinese text |
| R8 | 200 | 1.45 | Chinese text |
| R7 | 200 | 1.70 | "frnds, I am" |
| R4 | 200 | 1.94 | Chinese text |
| R6 | 200 | 2.18 | "a am trying to create" |
| R10 | 200 | 2.41 | ": We are trying to" |
| R9 | 200 | 2.66 | "me and my team are" |

## Summary
- **Total:** 20/20 HTTP 200 (100%)
- **Errors (4xx/5xx):** 0
- **14B avg time:** ~25s (GPU-queued, linear progression)
- **32B avg time:** ~1.5s (fast, independent)
- **No crashes, no restarts, no data mixing**
