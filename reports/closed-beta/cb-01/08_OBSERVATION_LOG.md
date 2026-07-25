# CB-01 Observation Log

**Window:** 2026-07-25 00:50 — 01:00 UTC

## Timeline

| Time (UTC) | Event |
|---|---|
| 00:50 | Window start — system snapshot |
| 00:51 | Pre-launch checks complete — all PASS |
| 00:52 | 5 API keys created in ai-platform.db |
| 00:53 | All 5 keys validated: GET /v1/models → HTTP 200 |
| 00:54 | UAT scenarios executed: Auth, models, invalid auth, invalid model |
| 00:54 | Chat 14B: "Здравствуйте (Zdravstvuyte)" — coherent Russian |
| 00:55 | Sequential load: 20 requests, 20/20 HTTP 200 |
| 00:57 | Backup created: ai-platform.db + identity.db |
| 00:58 | Controlled load: 2 users × 10 parallel = 20/20 HTTP 200 |
| 01:00 | Window close — post-test health check |

## Post-Window Health

```
K8s nodes: 2/2 Ready
Pods: 11/11 Running (0 restart delta)
VPN: UP (no reconnects)
nginx: ports 443/10443/30901 listening
Disk: 58% (20G free)
```

## Events
- No incidents
- No errors (beyond expected 4xx in negative tests)
- No pod restarts
- No GPU OOM
