# Source-of-Truth Mapping

| File | Runtime Used | Source Matches | Deployment Mechanism |
|---|---|---|---|
| `nginx-failover-vps2.conf` | ✅ `/root/nginx-failover.conf` | ✅ Synced | Bind mount → Docker |
| `nginx-gateway-32b-nginx.conf` | ✅ K8s ConfigMap `nginx.conf` key | ✅ Identical | ConfigMap subPath → Deployment |
| `vpn-cisco-entrypoint.sh` | ✅ Running container entrypoint | ✅ Synced | Docker bind mount |
| `app/main.py` | ✅ Deployed as container image | ✅ Rebuilt & deployed | Docker image → K8s Deployment |
| `nginx-gateway-32b.yaml` | ⚠️ Partial — conf.d (unused) | ⚠️ Different zone name | Unused ConfigMap mount |

## Resolution
- `nginx-gateway-32b-nginx.conf` is **authoritative** for the running gateway
- `nginx-gateway-32b.yaml` contains rate limit values updated to 300r/m, burst 20 but uses different ConfigMap key (`default.conf` vs `nginx.conf`)
- The yaml manifest's ConfigMap is mounted to `/etc/nginx/conf.d/` which is NOT included by the main `nginx.conf`
- Risk: two source files for same logical config → documented as known limitation
