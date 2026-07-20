# Redis Rate Limiting Report

Date: 2026-07-20
Executor: hermes@vps2
Repository branch: aither-v2
Commit: (this commit)

## 1. Objective

Implement and verify Redis-backed rate limiting for BFF.

## 2. Components

### Redis deployment

| Check | Expected | Actual | Status |
|---|---|---|---|
| Redis manifest dry-run | success | success | PASSED |
| Redis rollout | 1/1 Running | 1/1 Running | PASSED |
| Redis Service ClusterIP | created | created | PASSED |
| Redis probes (readiness/liveness) | configured | redis-cli ping | PASSED |

### BFF with rate limiting

| Check | Expected | Actual | Status |
|---|---|---|---|
| BFF rollout after RL | 1/1 Running | 1/1 Running | PASSED |
| /health with RL info | 200 + redis status | 200, rate_limit=enabled, redis=connected | PASSED |
| Under-limit requests | not 429 | 401 (upstream auth required, no 429) | PASSED |
| Exceeded limit | HTTP 429 | 429 "Rate limit exceeded" | PASSED |
| Window reset | returns to under-limit | confirmed via key flush | PASSED |
| Raw token not stored | PASSED | only sha256 hash or IP in Redis | PASSED |
| No secrets committed | PASSED | confirmed | PASSED |

## 3. Implementation details

- Fixed-window rate limiting per client (by Authorization hash or client IP)
- Rate limit check BEFORE upstream call (no wasted upstream traffic)
- Redis unavailable → fail-open (documented in findings)
- Health endpoint is NOT rate-limited
- Each rate limit key has TTL = window + 5 seconds (auto-cleanup)

## 4. Findings

| ID | Finding | Status | Target |
|---|---|---|---|
| BFF-RL-01 | Rate limiting implemented | PASSED | Stage 06 |
| BFF-RL-REDIS-01 | Redis-backed fixed-window rate limiting | PASSED | Stage 06 |
| BFF-RL-429-01 | HTTP 429 returned when limit exceeded | PASSED | Stage 06 |
| BFF-RL-KEY-01 | Rate limit key does not store raw Authorization token | PASSED | Stage 06 |
| BFF-RL-RESET-01 | Rate limit window reset verified | PASSED | Stage 06 |
| BFF-RL-REDIS-FAIL-01 | Redis unavailable behaviour (fail-open) | PARTIAL | Stage 06 |
| BFF-TOKEN-01 | Valid token test for 32B completion | NOT COLLECTED | Stage 05 |
| BFF-AUTH-01 | BFF has no built-in auth | PARTIAL | Stage 08 |

## 5. Conclusion

Stage 06 result by Hermes: **COMPLETED BY HERMES / WAITING FOR CHATGPT AUDIT**
