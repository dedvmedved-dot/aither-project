# U1.2 Persistence & Redeploy Gate — Final Status

## Overall Status
**U1.2 PERSISTENCE AND REDEPLOY GATE: READY FOR EXTERNAL AUDIT**

## Individual Gates

### Source-of-Truth
**COMPLETE** — All 5 source files synced with runtime and verified.

### VPS2 Redeploy
**REPRODUCIBLE** — `scripts/deploy-vps2-edge.sh` provides automated deployment with validation, backup, and rollback.

### ai-platform Image
- **Image tag:** `10.129.13.78:5000/ai-platform:u1.2-persistence-20260725-0004`
- **Image ID:** `sha256:fcf111165f61720e8d010e0b204c0c798cfe89df26b4f085174cca93f499783b`
- **Deployment:** `kubectl set image` → rollout successful
- **Running pod image:** Verified `u1.2-persistence-20260725-0004`

### Kubernetes Redeploy
**SUCCESS** — ai-platform deployed via `kubectl set image`, gateway ConfigMap updated. All pods healthy, 0 restarts.

### VPN Observation
- **Observation duration:** >2 hours (since 19:17 UTC)
- **tun0 recreations:** 0
- **OpenConnect duplicate processes:** 0 (single process)
- **Container restarts:** 0

### 429 Passthrough
- **Upstream status:** Gateway returns 429 on rate limit (verified: `rate=300r/m burst=20`)
- **Client status:** ai-platform now passes through 4xx (verified: 3 AST blocks in running pod)
- **Result:** ✅ PASSTHROUGH VERIFIED

### Post-Redeploy Gate
All 9 routes return HTTP 200:
- :30902 models/14B/32B: 60/60 ✅
- :443 models/14B/32B: 60/60 ✅
- :10443 models/14B/32B: 60/60 ✅
- **TOTAL: 180/180 PASS | 0 failures | 0 HTTP 5xx**

### Persistence
**PERSISTENT AND VERIFIED**

### Rollback
**DOCUMENTED AND AVAILABLE** — `docs/operations/U1.2_ROLLBACK.md`
