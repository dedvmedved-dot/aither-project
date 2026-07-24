# Commit Scope Audit

## Commits in scope
- `5df015c` — fix(u1.2): stabilize VPN routing and persist 32B gateway fixes (33 files)
- `4f12504` — merge: resolve ai-platform conflicts (2 conflict resolutions)

## File Classification

| File | Expected (U1.2) | Actual | Comment |
|---|---|---|---|
| `03-vllm-14b-deploy/manifests/nginx-gateway-32b.yaml` | ✅ | ✅ | Rate limit values updated |
| `docs/evidence/stage-u1.1-network-stability/*` | ✅ | ✅ | Network root cause evidence |
| `docs/evidence/stage-u1.2-32b-stability/*` | ✅ | ✅ | 32B stability evidence |
| `docs/evidence/stage-u1.2-internet-32b/*` | ✅ | ✅ | Internet 32B evidence |
| `docs/evidence/stage-u1.2-persistence-redeploy/*` | ✅ | ✅ | Persistence evidence |
| `docs/operations/AI_PLATFORM_REDEPLOYMENT.md` | ✅ | ✅ | Operations doc |
| `docs/operations/U1.2_ROLLBACK.md` | ✅ | ✅ | Rollback procedures |
| `docs/operations/VPS2_EDGE_DEPLOYMENT.md` | ✅ | ✅ | Operations doc |
| `scripts/deploy-vps2-edge.sh` | ✅ | ✅ | Deployment automation |
| `services/ai-platform/app/main.py` | ✅ | ✅ | 429 passthrough fix |
| `services/ai-platform/Dockerfile` | ⚠️ | ✅ | Pre-existing, needed for build docs |
| `services/ai-platform/k8s/ai-platform.yaml` | ⚠️ | ✅ | Pre-existing, needed for deploy |
| `services/ai-platform/requirements.txt` | ⚠️ | ✅ | Pre-existing, needed for build |
| `services/portal-frontend/docker-compose.vps2.yml` | ✅ | ✅ | Service definition |
| `services/portal-frontend/nginx-failover-vps2.conf` | ✅ | ✅ | VPS2 nginx source |
| `services/portal-frontend/nginx-gateway-32b-nginx.conf` | ✅ | ✅ | Gateway source |
| `services/portal-frontend/vpn-cisco-entrypoint.sh` | ✅ | ✅ | VPN entrypoint fix |

## Files NOT in scope (present in working tree but NOT committed)
- `portal/` — portal frontend changes (separate concern)
- `manifests/mvp-roadmap/07-portal/portal-mvp.yaml` — portal manifest (separate concern)

## Assessment
**CLEAN** — All committed files relate to U1.2. Pre-existing infrastructure files (`Dockerfile`, `requirements.txt`, `k8s/ai-platform.yaml`) were needed for build/deploy documentation but were added as part of project scaffolding, not as U1.2 changes.
