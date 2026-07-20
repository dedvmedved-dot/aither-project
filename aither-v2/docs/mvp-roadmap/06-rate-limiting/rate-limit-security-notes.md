# Rate Limit Security Notes

Date: 2026-07-20
Executor: hermes@vps2

## 1. Rate limit key design

- With Authorization header: `rl:{sha256(token_hex)}:{window}`
- Without Authorization: `rl:ip:{client_ip}:{window}`
- **No raw authorization tokens stored in Redis** (only SHA-256 hash)
- Key uses fixed-window timestamp to auto-rotate every N seconds

## 2. Redis security

- Redis is accessed by ClusterIP DNS (`aither-redis-rate-limit.aither-inference.svc:6379`)
- No auth configured for Redis (MVP — internal cluster traffic only)
- Redis runs as root container user (securityContext: {}) because `redis:7-alpine` requires `chown` on /data
- No persistent storage (emptyDir — data lost on pod restart, acceptable for rate limiting)

## 3. Fail-open behaviour

- If Redis is unavailable, BFF allows all requests
- Failure is logged on every request until Redis recovers
- Documented as finding BFF-RL-REDIS-FAIL-01 (PARTIAL)
- Health endpoint reports redis status: "connected" or "unavailable"

## 4. Request flow

```
Client -> BFF -> [Rate limit check] -> [Blocked: 429] / [Allowed: upstream proxy]
```

- Rate limit is checked BEFORE upstream call
- No upstream resources wasted on rate-limited requests
- Health check is NOT rate-limited (always 200)

## 5. Known gaps

- No Redis auth (MVP, internal cluster)
- No Redis persistence (acceptable for rate limiting state)
- No rate limiting per-endpoint (same limit for chat and completions)
- No distributed rate limiting (single Redis instance, single replica BFF)
- Fail-open when Redis unavailable (documented)
- Redis runs as root container user (documented in BFF-RL-REDIS-FAIL-01)
