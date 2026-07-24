# Root Cause Analysis — Internet Path Stabilization

## RC1: VPN Client Reconnect Loop

### Finding
OpenConnect `expect` wrapper executable (`vpn-cisco-entrypoint.sh`) used `expect eof` pattern which misinterpreted OpenConnect's DPD (Dead Peer Detection) activity as process termination.

### Evidence
- `vpn-cisco` container showed 2 running instances (52m + 2d) — original had restart loop
- Log analysis showed `tun0` being recreated every ~30 seconds (DPD interval)
- After fix: tunnel stable >52 minutes, no tun0 recreation

### Fix
```bash
# Before (bug):
expect eof

# After (fix):
set timeout -1
expect {
    timeout { exp_continue }
    eof {}
}
```

---

## RC2: Gateway Rate Limit → 502 Error Semantics

### Finding
nginx-gateway-32b had `limit_req_zone rate=30r/m` (0.5 requests/second) with `burst=10`.
ai-platform converted HTTP 429 (rate limited) to HTTP 502 (Bad Gateway).

### Evidence
- ai-platform logs: `"Gateway returned HTTP 429: rate limit exceeded"` → `"POST /v1/chat/completions HTTP/1.1" 502`
- Concurrency test: C1-C3 all 200, C4 had 9/20 failures (429→502)
- After rate limit fix (300r/m): C1-C4 all 50/50 PASS

### Fix
1. Gateway ConfigMap: `rate=30r/m` → `rate=300r/m`, `burst=10` → `burst=20`
2. ai-platform code: 4xx errors now pass through (HTTP 429 → HTTP 429, not 502)

---

## RC3: VPS2 Nginx Connection Timeout (contributing factor)

### Finding
`proxy_connect_timeout 10s` on VPS2 Docker nginx too aggressive for Cisco VPN tunnel latency spikes.

### Fix
- `proxy_connect_timeout`: 10s → 30s
- `proxy_http_version`: 1.0 → 1.1 (enables keepalive)
- `keepalive`: 0 → 16 (connection pooling)

### Evidence
- Sequential tests show consistent sub-second response times through VPN
- No TCP connection failures observed in 230 requests
