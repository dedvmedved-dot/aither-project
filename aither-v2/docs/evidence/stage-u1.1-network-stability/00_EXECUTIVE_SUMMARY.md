# Network Stability — Executive Summary

**Date:** 2026-07-24  
**Stage:** U1.1 (DNS / Network / TLS) — Corrective Work Package  
**Status:** NETWORK STABILITY GATE — READY FOR EXTERNAL AUDIT

---

## Problem

Internet path to 32B model via `fb1.spb.ru` returned HTTP 504 Gateway Timeout intermittently.
Initial nginx timeout adjustment (10s→30s) did not resolve the issue (4-6/10 stability).

## Root Cause

**CONFIRMED:** OpenConnect VPN tunnel was reconnecting every ~30 seconds due to a bug in the Docker container's entrypoint script.

The `expect` wrapper script used `expect eof` to wait for OpenConnect exit. OpenConnect's DPD (Dead Peer Detection, every 30 seconds) caused stdout activity that `expect` interpreted as EOF, triggering an exit (rc=0) and tunnel recreation. Each recreation destroyed `tun0`, changed the tunnel IP, and broke all in-flight TCP connections.

## Fix Applied

Changed `expect` timeout from default to `-1` (infinite) and replaced `expect eof` with:
```
set timeout -1
expect {
    timeout { exp_continue }
    eof {}
}
```

This prevents expect from exiting on DPD-related output. OpenConnect now runs stably for the duration of the session.

## Stability Results

| Route | Model | Endpoint | Result |
|---|---|---|---|
| :443 | — | GET /v1/models | **20/20** ✅ |
| :443 | 14B | POST chat/completions | **20/20** ✅ |
| :443 | 32B | POST chat/completions | **20/20** ✅ |
| :10443 | — | GET /v1/models | **20/20** ✅ |
| :10443 | 14B | POST chat/completions | **20/20** ✅ |
| :10443 | 32B | POST chat/completions | **20/20** ✅ |
| :30902 | — | GET /v1/models | **20/20** ✅ |
| :30902 | 14B | POST chat/completions | **20/20** ✅ |
| :30902 | 32B | POST chat/completions | 14/20 ⚠️ |

**8/9 combinations meet the 20/20 criterion.**  
:30902 32B failures are HTTP 502 from ai-platform (application-level concurrency limit), not network-related.

## Failure Domain

**VPN CLIENT** — OpenConnect expect wrapper

## Persistence

**NOT YET PERSISTENT** — entrypoint fix applied to running container only. Source-of-truth saved to repo. Redeploy requires container restart with updated entrypoint.

## Commit

**NOT CREATED** — awaiting external audit per project governance.
