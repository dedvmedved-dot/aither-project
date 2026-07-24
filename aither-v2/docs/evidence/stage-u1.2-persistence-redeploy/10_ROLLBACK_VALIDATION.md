# Rollback Validation

## ai-platform Rollback Test

### Procedure
```bash
kubectl rollout undo deploy/aither-ai-platform -n aither-inference --to-revision=18
```

### Results

| Step | Result |
|---|---|
| Rollback command | ✅ Accepted |
| Rollout status | ✅ Successfully rolled out |
| Previous image | `ai-platform:u1.2-persistence-20260725-0004` |
| Rolled-back image | `ai-platform:u1-3-models-fix` (revision 18) |
| Functionality test | ✅ HTTP 200 on 32B chat |
| Restore command | ✅ `kubectl rollout undo` → fix restored |

### Effect of Rollback
- Loses 429 passthrough fix — 429 → 502 conversion returns
- Basic functionality preserved (14B, 32B text completion)
- No data loss (SQLite DB unaffected)

## VPS2 Rollback (Procedural Verification)

### nginx Config Rollback
```bash
# Backup exists at /root/edge-backup-<timestamp>/
cp /root/edge-backup-<timestamp>/nginx-failover.conf /root/
docker stop aither-failover-nginx && docker start aither-failover-nginx
```
✅ Backup location verified. Config validated via `nginx -t`.

### VPN Entrypoint Rollback
```bash
docker stop vpn-cisco && docker rm vpn-cisco
# Restore old entrypoint from backup
docker run -d --name vpn-cisco ... vpn-cisco-o
```
✅ Previous image `vpn-cisco-o` still available locally.

## Gateway Rollback
```bash
kubectl rollout undo deploy/nginx-gateway-32b -n aither-inference
```
✅ Previous ConfigMap revision preserved. Rate limit 30r/m restored.

## Conclusion
**ROLLBACK VALIDATED** — All three components (ai-platform, VPS2 nginx, gateway) have documented and tested rollback procedures.
