# Corrective Actions

| ID | Finding | Change | Status | Rollback | Evidence |
|---|---|---|---|---|---|
| RC1-FIX | VPN expect wrapper causes tun0 restart | `expect eof` → `timeout -1 + exp_continue` | ✅ Applied | Restore original entrypoint | Tunnel stable >52 min |
| RC2A-FIX | Gateway rate limit too restrictive | `rate=30r/m` → `300r/m`, `burst=10` → `20` | ✅ Applied | `rate=30r/m burst=10` | 50/50 concurrency PASS |
| RC2B-FIX | ai-platform converts 429→502 | 4xx errors pass through, 5xx stay as 502 | ✅ Source fixed | Revert code change | ai-platform main.py |
| RC3-FIX | VPS2 nginx connect timeout | `proxy_connect_timeout 10s` → `30s` | ✅ Applied | Restore old nginx config | 180/180 sequential PASS |
| RC3-FIX | VPS2 nginx HTTP/1.0 no keepalive | HTTP/1.1 + keepalive 16 | ✅ Applied | `proxy_http_version 1.0` | Lower latency |

## GAPs Recorded

| ID | Area | Description | Blocking |
|---|---|---|---|
| U1.4-GAP-32B-CHAT-001 | 32B chat completions | qwen-32b-base is text completion model, not chat-capable | YES for full API compat |
| U1.4-GAP-32B-OVERLOAD-001 | API error semantics | ai-platform should return 429 on rate limit, not 502 | NO (fixed in source) |
