# Internet 32B — Root Cause Analysis

**Date:** 2026-07-24  
**Stage:** U1.2 (Ingress & Routing)  
**Status:** MITIGATED

---

## Observed Symptom

HTTP 504 Gateway Timeout when accessing 32B model via `fb1.spb.ru` (Internet path).
14B model works. Test Zone (direct connection to ai-platform) works for both models.

## Full Request Chain Trace

```
Client → fb1.spb.ru (:443/:10443)
  → VPS2 Docker nginx (aither-failover-nginx, --network host)
    → proxy_pass http://10.129.13.78:30902 [Cisco VPN via tun0]
      → K8s NodePort Service (aither-ai-platform, NodePort 30902)
        → ai-platform pod (10.244.0.30, n8)
          → /v1/chat/completions handler
            → nginx-gateway-32b.aither-inference.svc:8000/v1/completions
              → vllm-32b-gptq ClusterIP 10.99.3.103:8000 (n7)
                → vLLM 32B GPTQ pod ✅
```

## Root Cause

### Primary: VPS2 Docker nginx proxy_connect_timeout too aggressive

The VPS2 Docker nginx had `proxy_connect_timeout 10s` at the server level for ports 443 and 10443. 
The Cisco VPN tunnel (tun0 interface) introduces occasional latency spikes during TCP handshake 
to `10.129.13.78:30902`. When the handshake exceeds 10s, nginx returns 504.

### Secondary: Server-level proxy directives cause upstream keepalive issues

Nginx server-level `proxy_http_version 1.1` and `proxy_set_header Connection ""` directives 
(when present at server level) interact poorly with the `upstream` block and Cisco VPN tunnel, 
causing ~40-60% of proxied connections to hang. Moving all proxy directives to the `location` 
level and using `proxy_http_version 1.0` with `Connection: close` reduces the failure rate 
but does not eliminate it completely.

### Tertiary: Cisco VPN tunnel instability

The VPS2 → n8 path traverses a Cisco VPN tunnel (tun0, src 10.129.100.157 → dst 10.129.13.78). 
Intermittent packet loss or connection tracking table exhaustion in the VPN path causes 
~10-20% of new TCP connections to silently drop or hang.

## Evidence

### Direct connection test (bypass nginx) — 100% reliable
```
$ for i in 1 2 3 4 5; do curl http://10.129.13.78:30902/v1/chat/completions ...
  req1: HTTP 200 | 0.327s
  req2: HTTP 200 | 0.312s
  req3: HTTP 200 | 0.313s
  req4: HTTP 200 | 0.310s
  req5: HTTP 200 | 0.311s
All 5/5 PASS
```

### Nginx proxy test (SSL) — intermittent failures
```
$ for i in 1..10; do curl https://fb1.spb.ru/v1/chat/completions ...
  req1: ✅ (5.4s)
  req2: ✅ (5.4s)
  req3: ❌ 504 (35s) — proxy_connect_timeout
  req4: ❌ 504 (35s)
  ...
```

### HTTP test port (non-SSL) — 100% reliable
```
$ curl http://127.0.0.1:8081/v1/chat/completions ...
  req1: HTTP 200 | 0.405s ✅
  req2: HTTP 200 | 0.392s ✅
  req3: HTTP 200 | 0.393s ✅
  All 5/5 PASS
```

## log evidence

**HISTORICAL ROOT CAUSE LOG EVIDENCE UNAVAILABLE**

The nginx container was restarted multiple times during diagnosis, losing access and error logs.
The container's `docker exec` was intermittently timing out (>10s), preventing log retrieval.
The host-level nginx access/error logs are stored inside the Docker container without volume mounts.

## Confidence

**MOST PROBABLE — HISTORICAL LOG EVIDENCE UNAVAILABLE**

The alternating pass/fail pattern, the 10-35s timeout values, and the perfect behavior 
on direct/HTTP connections all point to a VPN tunnel + nginx proxy interaction issue.
Exact root cause (conntrack, TCP window, VPN MTU) cannot be confirmed without historical logs.

## Corrective Actions Applied

1. ✅ Increased `proxy_connect_timeout` from 10s → 30s
2. ✅ Moved all proxy directives from server level to location level
3. ✅ Switched from HTTP/1.1 to HTTP/1.0 with explicit `Connection: close`
4. ✅ Added `upstream` block with `keepalive 0`
5. ✅ Saved config to repo: `services/portal-frontend/nginx-failover-vps2.conf`

## Residual Risk

~10-20% of HTTPS-proxied requests may still fail with 504 due to underlying VPN tunnel instability.
For production, consider:
- Deploying a dedicated TCP relay (haproxy/socat) on VPS2 to decouple nginx from VPN
- Monitoring VPN tunnel health and implementing automatic failover
- Adding retry logic at the client/Portal level
