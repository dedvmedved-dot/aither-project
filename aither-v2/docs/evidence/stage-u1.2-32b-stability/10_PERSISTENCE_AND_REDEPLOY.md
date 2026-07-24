# Persistence and Redeploy

## Current State
**PERSISTENCE: NOT YET PERSISTENT** (redeploy not verified)

## Source-of-Truth Files

| Runtime File | Source-of-Truth | Status |
|---|---|---|
| `/root/nginx-failover.conf` | `services/portal-frontend/nginx-failover-vps2.conf` | Source exists, needs sync |
| `/root/vpn-cisco-entrypoint.sh` | `services/portal-frontend/vpn-cisco-entrypoint.sh` | Source exists |
| K8s ConfigMap `nginx-gateway-32b` | `services/portal-frontend/nginx-gateway-32b-nginx.conf` | Source created |
| ai-platform code | `services/ai-platform/app/main.py` | Updated (429 fix) |

## Deployment Mechanisms
- VPS2 nginx: bind-mount `/root/nginx-failover.conf` → container `/etc/nginx/conf.d/default.conf`
- VPS2 VPN: Docker entrypoint script
- K8s gateway: ConfigMap + Deployment with subPath mount
- ai-platform: Docker image rebuild required

## Required for Full Persistence
1. Rebuild ai-platform Docker image with 429 fix
2. Verify container restart picks up new configs
3. Document deployment procedure
