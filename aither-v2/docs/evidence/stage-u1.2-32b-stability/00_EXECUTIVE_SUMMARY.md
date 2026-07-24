# 32B Stability Gate — Executive Summary

## Status
**NETWORK STABILITY GATE: READY FOR EXTERNAL AUDIT**

## Summary
Two root causes identified and resolved for Internet 32B HTTP 504/502:

### Root Cause 1: VPN Client (Network)
**CONFIRMED** — OpenConnect `expect` wrapper misidentified DPD keepalive as EOF, causing tun0 restart loop → TCP connection drops → nginx 504.

**Fix:** Changed `expect eof` to `expect { timeout { exp_continue }; eof {} }` in VPN entrypoint.

### Root Cause 2: Rate Limit + Error Semantics (Application)  
**CONFIRMED** — nginx-gateway-32b had `rate=30r/m` (0.5 req/s) with burst=10. Under concurrency >2, ai-platform received HTTP 429 from gateway and converted it to HTTP 502 (wrong error semantics).

**Fix:** 
- Gateway rate limit: 30r/m → 300r/m, burst 10 → 20
- ai-platform code: 4xx errors now pass through (HTTP 429 → HTTP 429, not 502)

### Additional Improvements
- VPS2 nginx: HTTP/1.0→1.1, keepalive 0→16, proxy_connect_timeout 10s→30s
- VPN tunnel: stable >52 minutes with no reconnect loops

## Final Stability Gate
- 9 routes × 20 sequential = 180/180 PASS
- Concurrency 1-4 × 50 requests = 50/50 PASS
- Total: **230/230 PASS, 0 failures**

## Key Files Changed
- `/root/nginx-failover.conf` — VPS2 nginx (HTTP/1.1, keepalive, timeouts)
- `services/ai-platform/app/main.py` — 429 passthrough
- `services/portal-frontend/nginx-gateway-32b-nginx.conf` — gateway rate limits
- `services/portal-frontend/nginx-failover-vps2.conf` — VPS2 nginx source-of-truth
- `services/portal-frontend/vpn-cisco-entrypoint.sh` — VPN entrypoint fix
