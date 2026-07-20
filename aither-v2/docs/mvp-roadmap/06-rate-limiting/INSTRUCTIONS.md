# Stage 06 — Redis / Rate Limiting

## Objective

Реализовать Redis-backed fixed-window rate limiting для BFF.

## Architecture

```
User / Portal -> BFF -> Redis rate limit check -> Gateway / vLLM
```

## Components

| Component | Name | Namespace |
|---|---|---|
| Redis | aither-redis-rate-limit | aither-inference |
| BFF (with RL) | aither-bff | aither-inference |

## Rate limit settings (default)

| Variable | Default | Description |
|---|---|---|
| RATE_LIMIT_ENABLED | true | Enable/disable rate limiting |
| REDIS_URL | redis://aither-redis-rate-limit.aither-inference.svc:6379/0 | Redis connection string |
| RATE_LIMIT_WINDOW_SECONDS | 60 | Fixed window duration |
| RATE_LIMIT_MAX_REQUESTS | 10 | Max requests per window |

## Rate limit key format

- With Authorization header: `rl:{sha256(token_hex)}:{window}`
- Without Authorization header: `rl:ip:{client_ip}:{window}`
- No raw authorization tokens stored in Redis

## Rate limit behaviour

- Allowed requests (count <= MAX): normal upstream flow
- Exceeded requests (count > MAX): HTTP 429 "Rate limit exceeded"
- Health endpoint (/health): NOT rate-limited
- Redis unavailable: fail-open (requests allowed, logged as finding)

## Files

- Manifest: `manifests/mvp-roadmap/06-rate-limiting/redis-rate-limit.yaml`
- ConfigMap: `manifests/mvp-roadmap/05-bff/bff-mvp.yaml` (app.py with rate limiting)
- Evidence: `docs/mvp-roadmap/06-rate-limiting/evidence/`
- Reports: `docs/mvp-roadmap/06-rate-limiting/`
