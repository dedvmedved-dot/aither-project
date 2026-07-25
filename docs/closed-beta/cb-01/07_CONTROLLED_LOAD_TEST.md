# CB-07 Controlled Load Test

**Date:** 2026-07-25 00:58 UTC

---

## Test Configuration

- **Concurrent users:** 2 (BETA-USER-01, BETA-USER-02)
- **Models tested:** qwen-14b (U1), qwen-32b-base (U2)
- **Requests per user:** 10
- **Total requests:** 20
- **Endpoint:** POST /v1/chat/completions
- **Duration:** 49.9 seconds

---

## Results

| Metric | Value |
|---|---|
| Total requests | 20 |
| HTTP 200 | 20 (100%) |
| HTTP 4xx | 0 |
| HTTP 5xx | 0 |
| U1 14B avg time | ~25s (GPU-queued, linear) |
| U2 32B avg time | ~1.5s (fast, independent) |
| Max response time | 49.8s (14B, last in queue) |
| Min response time | 0.55s (32B) |

---

## Pod Health (Before/After)

| Pod | Before | After |
|---|---|---|
| aither-ai-platform | 1/1 Running | 1/1 Running |
| nginx-gateway-32b (×2) | 1/1 Running | 1/1 Running |
| vllm-14b-instruct | 1/1 Running | 1/1 Running |
| vllm-32b-gptq | 1/1 Running | 1/1 Running |
| aither-identity | 1/1 Running | 1/1 Running |
| aither-redis-rate-limit | 1/1 Running | 1/1 Running |

- **Restart count delta:** 0 (no restarts triggered)
- **GPU OOM:** Not observed
- **CrashLoopBackOff:** Not observed
- **VPN stability:** No reconnects

---

## Observations

1. **14B model is GPU-bound:** Requests were processed sequentially (~5s each), creating a linear queue. Under 2 concurrent users, the 10th request in each batch waited ~45-50s. This is expected behavior for a single GPU serving sequential inference.

2. **32B model is efficient:** All 10 requests completed quickly (~0.5-2.5s each) with no queuing observed.

3. **No user data mixing:** Each API key produced independent, correct responses.

4. **No degradation:** All subsequent requests continued to work normally.

5. **Rate limiting not triggered:** 20 requests across 2 users within 50s stayed well within the 300 req/min limit.

---

## Status: PASS

The system handles 2 concurrent users with separate API keys without errors, crashes, or data mixing. 14B queuing is expected GPU behavior.

---
*Evidence: reports/closed-beta/cb-01/07_CONTROLLED_LOAD_EVIDENCE.md*
