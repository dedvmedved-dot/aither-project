# RUNBOOK: Rollback

See also: `docs/operations/U1.2_ROLLBACK.md`

## ai-platform Rollback

```bash
ssh n8 "kubectl rollout undo deploy/aither-ai-platform -n aither-inference"
ssh n8 "kubectl rollout status deploy/aither-ai-platform -n aither-inference --timeout=120s"
```

Verify: `curl -s http://10.129.13.78:30902/version`

Previous image: `ai-platform:u1-3-models-fix`

## Gateway Rollback

```bash
ssh n8 "kubectl rollout undo deploy/nginx-gateway-32b -n aither-inference"
ssh n8 "kubectl rollout status deploy/nginx-gateway-32b -n aither-inference --timeout=60s"
```

## VPS2 nginx Rollback

```bash
# Restore from backup
cp /root/edge-backup-<timestamp>/nginx-failover.conf /root/
docker stop aither-failover-nginx
docker start aither-failover-nginx
# OR from Git
cd /root/aither-project/aither-v2
git checkout <previous-commit> -- services/portal-frontend/nginx-failover-vps2.conf
cp services/portal-frontend/nginx-failover-vps2.conf /root/nginx-failover.conf
docker exec aither-failover-nginx nginx -s reload
```

## VPS2 VPN Entrypoint Rollback

```bash
docker stop vpn-cisco
docker rm vpn-cisco
# Restore old entrypoint from backup
cp /root/edge-backup-<timestamp>/vpn-cisco-entrypoint.sh /root/.../
docker run -d --name vpn-cisco ... vpn-cisco-o /bin/bash /old-entrypoint.sh
```

## Verification After Rollback
Run `03_HEALTH_CHECKLIST.md`. Minimum: test both models on all three routes.
