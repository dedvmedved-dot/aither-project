# Internet 32B — Persistence Assessment

**Date:** 2026-07-24

## Runtime vs Source-of-Truth

| Property | Value |
|---|---|
| **Runtime file** | `/root/nginx-failover.conf` (VPS2, 130.17.1.90) |
| **Source-of-truth file** | `/root/aither-project/aither-v2/services/portal-frontend/nginx-failover-vps2.conf` |
| **Deployment mechanism** | Manual: Docker bind mount + container restart |
| **Persistence status** | NOT YET PERSISTENT — no automated deployment |

## Deployment Instructions (Manual)

```bash
# On VPS2 (130.17.1.90):
# 1. Copy config from repo
cp /root/aither-project/aither-v2/services/portal-frontend/nginx-failover-vps2.conf \
   /root/nginx-failover.conf

# 2. Recreate container (required due to bind mount cache)
docker stop aither-failover-nginx
docker rm aither-failover-nginx
docker run -d --name aither-failover-nginx \
  --network host \
  --restart unless-stopped \
  -v /root/nginx-failover.conf:/etc/nginx/conf.d/default.conf:ro \
  -v /root/ssl-cert:/etc/nginx/ssl:ro \
  nginx:alpine

# 3. Verify
docker exec aither-failover-nginx nginx -t
curl -sk -o /dev/null -w "%{http_code}\n" https://fb1.spb.ru/v1/models \
  -H "Authorization: Bearer <API_KEY>"
```

## GAP: No Automated Redeploy

| Item | Status |
|---|---|
| Config in repo | ✅ `services/portal-frontend/nginx-failover-vps2.conf` |
| Docker Compose | ❌ Not present — container started via `docker run` |
| Ansible/script | ❌ No deployment automation |
| SSL certs in repo | ❌ Separately managed (`/root/ssl-cert/`) |
| Redeploy survives VPS reboot | ⚠️ Only if Docker `--restart unless-stopped` works |
| Redeploy from clean repo clone | ❌ Requires manual steps |

## Required for Full Persistence

1. Create Docker Compose file or systemd unit for `aither-failover-nginx`
2. Document SSL certificate renewal/deployment process
3. Add to project deployment scripts
4. Test clean redeploy from repo clone
