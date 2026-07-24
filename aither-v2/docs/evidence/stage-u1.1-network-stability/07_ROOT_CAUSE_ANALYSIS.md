# Root Cause Analysis — VPN Tunnel Instability

**Date:** 2026-07-24  
**Confidence:** CONFIRMED

---

## Symptom

HTTP 504 errors on Internet path (VPS2 nginx → Cisco VPN → K8s), intermittent, ~40-60% failure rate. Test Zone (direct connection) stable.

## Investigation

### Step 1: Trace full request chain
All hops verified. ai-platform backend responsive (0.3s directly). Issue isolated to VPS2 nginx → upstream connection.

### Step 2: Network baseline
- VPN: OpenConnect (AnyConnect client), Cisco ASA at 95.137.2.98
- Tunnel: tun0, MTU 1390, CSTP-only (--no-dtls)
- Routing: 10.129.0.0/16 → tun0
- TCP: 98/100 connect success to :30902
- Ping: 93/100, 7% loss (during tunnel flaps)

### Step 3: VPN process analysis
- Container: vpn-cisco (--network host), entrypoint `/entrypoint.sh`
- Entrypoint runs OpenConnect inside `expect` wrapper with `while true` loop
- Observed: tunnel IP changing every 30-60 seconds (10.129.100.{155,157,103,235,36,175,53...})
- Each reconnect: tun0 delete → new tun0 → new IP → TCP connections break → nginx 504

### Step 4: Root cause identification

The entrypoint's expect script:
```tcl
expect {
    "Password:" { ... }
    "Group:" { ... }
    "CSTP" { puts "CONNECTED!" }
}
expect eof   # ← THIS IS THE BUG
```

OpenConnect with DPD (30s interval per ASA server config: `X-CSTP-DPD: 30`) produces stdout/heartbeat activity every 30 seconds. The `expect eof` pattern matches this activity as "end of file", causing expect to exit with rc=0. The `while true` loop then deletes tun0 and reconnects.

### Step 5: Fix

Changed expect script to use infinite timeout and ignore non-EOF output:
```tcl
set timeout -1
expect {
    timeout { exp_continue }
    eof {}
}
```

### Step 6: Verification

Tunnel stable >25 minutes (vs <30 seconds before). All Internet routes 20/20.

## Evidence

- OpenConnect logs showing reconnect every 30s: `OpenConnect exited (rc=0), reconnecting in 5s...`
- ASA server DPD setting: `X-CSTP-DPD: 30`
- Tunnel IP changes: documented 7 different IPs in 10 minutes before fix
- Post-fix: tunnel IP stable (10.129.100.53) for 25+ minutes
