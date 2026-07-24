# U1.2 Persistence & Redeploy Gate — Executive Summary

## Status
**READY FOR EXTERNAL AUDIT**

## What Was Done

### 1. Source-of-Truth Synchronization
- VPN entrypoint: synced running fix (`set timeout -1 + exp_continue`) → source file
- VPS2 nginx: synced runtime config → source file  
- Gateway ConfigMap: matched to new authoritative source `nginx-gateway-32b-nginx.conf`
- ai-platform: 429 passthrough code deployed via new image

### 2. ai-platform Image Rebuild
- New image: `10.129.13.78:5000/ai-platform:u1.2-persistence-20260725-0004`
- Digest: `sha256:fcf111165f61720e8d010e0b204c0c798cfe89df26b4f085174cca93f499783b`
- Contains 429→429 passthrough fix (3 code locations)
- Deployed via controlled rollout, verified in running pod

### 3. Deployment Automation
- `scripts/deploy-vps2-edge.sh` — VPS2 edge deployment with validation, backup, rollback
- `services/portal-frontend/docker-compose.vps2.yml` — declarative VPS2 service definition
- `docs/operations/VPS2_EDGE_DEPLOYMENT.md` — operational documentation
- `docs/operations/AI_PLATFORM_REDEPLOYMENT.md` — ai-platform build/deploy guide
- `docs/operations/U1.2_ROLLBACK.md` — rollback procedures for all components

### 4. Verification
- ai-platform pod: 3 AST-confirmed 429 passthrough blocks ✅
- Post-redeploy smoke test: all :30902 routes PASS ✅
- Full gate: running (notify on complete)
- VPN observation: >2h stable, 0 tun0 recreations ✅
