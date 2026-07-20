# Rate Limit Test Report

Date: 2026-07-20
Executor: hermes@vps2

## Test results

| Test | Expected | Actual | Status |
|---|---|---|---|
| Redis pods | 1/1 Running | 1/1 Running | PASSED |
| Redis Service | ClusterIP available | created | PASSED |
| BFF health with RL | 200, RL info | 200, rate_limit=enabled, redis=connected | PASSED |
| Under-limit requests | no 429 | no 429 (401 for missing auth) | PASSED |
| Exceeded limit | 429 | 429 "Rate limit exceeded. Try again later." | PASSED |
| Window reset | request succeeds | succeeds after key flush | PASSED |
| Raw token not in Redis | only hash/IP | only rl:ip:127.0.0.1:... key with counter | PASSED |
| No secrets committed | confirmed | confirmed | PASSED |
| Forbidden scope unchanged | confirmed | confirmed | PASSED |
| BFF rollout after RL | 1/1 Running | 1/1 Running | PASSED |

## Test evidence files

| File | Status |
|---|---|
| evidence/redis-manifest-dry-run.txt | PASSED |
| evidence/redis-rollout-status.txt | PASSED |
| evidence/redis-pods-after.txt | PASSED |
| evidence/redis-service-after.yaml | PASSED |
| evidence/bff-rollout-after-rl.txt | PASSED |
| evidence/bff-pods-after-rl.txt | PASSED |
| evidence/rate-limit-under-limit.txt | PASSED |
| evidence/rate-limit-exceeded-429.txt | PASSED |
| evidence/rate-limit-reset-window.txt | PASSED |
| evidence/redis-key-safety-check.txt | PASSED |
| evidence/no-secret-leak-check.txt | PASSED |
| evidence/forbidden-scope-check.txt | PASSED |
