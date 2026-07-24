# Deployment Validation — Fail-Closed Health Check

## Change Summary
Deployment script `scripts/deploy-vps2-edge.sh` health check changed from **fail-open** (WARNING on failure) to **fail-closed** (exit 1 on failure).

## Before (fail-open)
```bash
if curl -sk https://localhost/health >/dev/null 2>&1; then
  echo "✅ nginx healthy"
else
  echo "WARNING: nginx health check failed (may need auth)" >&2
fi
# Script continues regardless
```

## After (fail-closed)
```bash
HEALTH_OK=1
# Test nginx is listening on 443
if ! curl -sk --connect-timeout 5 https://localhost:443/ >/dev/null 2>&1; then
  echo "ERROR: nginx not responding on :443" >&2
  HEALTH_OK=0
fi
# Test nginx is listening on 10443
if ! curl -sk --connect-timeout 5 https://localhost:10443/ >/dev/null 2>&1; then
  echo "ERROR: nginx not responding on :10443" >&2
  HEALTH_OK=0
fi
if [ $HEALTH_OK -eq 0 ]; then
  echo "FATAL: Health check failed — deployment aborted" >&2
  echo "Rollback: docker stop aither-failover-nginx vpn-cisco; ..."
  exit 1
fi
```

## Validation
- Shell syntax: ✅ `bash -n` passes
- Both ports verified responding: :443 ✅, :10443 ✅
- Exit code path: 8 `exit 1` statements for error conditions
- Rollback message included in fatal output

## Behavior Matrix

| Condition | Before | After |
|---|---|---|
| Both ports up | ✅ healthy, continue | ✅ healthy, continue |
| :443 down | ⚠️ WARNING, continues | ❌ ERROR, exit 1 |
| :10443 down | ⚠️ WARNING, continues | ❌ ERROR, exit 1 |
| Both down | ⚠️ WARNING, continues | ❌ FATAL, exit 1 with rollback instructions |

## Conclusion
**DEPLOYMENT VALIDATED** — Health check is now fail-closed. Any port failure triggers non-zero exit with rollback instructions.
