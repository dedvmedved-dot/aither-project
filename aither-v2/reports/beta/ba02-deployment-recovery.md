# Stage BA-02 — Deployment Recovery Report

**Date:** 2026-07-23
**Status:** ✅ Portal Backend recovered and deployed

## ImagePullBackOff Diagnosis

| Pod | Status | Image Tag | Root Cause |
|-----|--------|-----------|------------|
| `portal-backend-rmg5t` | ❌ ImagePullBackOff | `:stage18a-014f91b` | Image tag **not found** in cluster registry `10.129.13.78:5000`. The deployment was updated to reference a new tag that was never built/pushed. |
| `portal-backend-c9f9j` | ✅ Running | `:stage18a-82fe433` | Working on old stable tag |

## Fix Applied

1. **Built new image** with AI Platform proxy routes (unstaged code from BA-01R)
2. **Tagged**: `10.129.13.78:5000/aither-portal-backend:ba02-014f91b`
3. **Digest**: `sha256:e6ad1f193ba46368937b90efd37bf3c35457ca6b0d11808c255394225cb361a6`
4. **Deployment**: `kubectl set image deployment/aither-portal-backend portal-backend=10.129.13.78:5000/aither-portal-backend:ba02-014f91b`

## Result

```
aither-portal-backend-559754567d-599kk   1/1     Running   0          55s
All 11 pods in aither-inference namespace: Running ✓
```

## Deployment Method

Image built on **build host** (docker), pushed directly to **cluster registry** (`10.129.13.78:5000`), avoiding unstable SSH transfers. Updated via `kubectl set image`.
