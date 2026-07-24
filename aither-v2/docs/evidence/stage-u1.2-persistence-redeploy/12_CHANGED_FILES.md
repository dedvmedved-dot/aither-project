# Changed Files

## Repository Files

| File | Type | Description |
|---|---|---|
| `services/portal-frontend/nginx-failover-vps2.conf` | Modified | HTTP/1.1, keepalive 16, connect_timeout 30s |
| `services/portal-frontend/nginx-gateway-32b-nginx.conf` | New | Authoritative gateway config (rate=300r/m, burst=20) |
| `services/portal-frontend/vpn-cisco-entrypoint.sh` | Modified | Fixed expect wrapper (timeout -1 + exp_continue) |
| `services/portal-frontend/docker-compose.vps2.yml` | New | VPS2 service definition |
| `services/ai-platform/app/main.py` | Modified | 429 passthrough (3 code blocks) |
| `03-vllm-14b-deploy/manifests/nginx-gateway-32b.yaml` | Modified | Rate limit values updated |
| `scripts/deploy-vps2-edge.sh` | New | VPS2 deployment automation |
| `docs/operations/VPS2_EDGE_DEPLOYMENT.md` | New | Operational documentation |
| `docs/operations/AI_PLATFORM_REDEPLOYMENT.md` | New | Build/deploy guide |
| `docs/operations/U1.2_ROLLBACK.md` | New | Rollback procedures |
| `docs/evidence/stage-u1.2-persistence-redeploy/*` | New | Evidence (13 files) |

## Runtime Files (not in Git)

| File | Description |
|---|---|
| `/root/nginx-failover.conf` | VPS2 nginx runtime config (source-of-truth synced) |
