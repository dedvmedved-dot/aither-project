# 12_FINAL_MANIFEST.md — CAP-01 Corrective Action Package

## Commit: `4f12504` (merge) + `5df015c` (parent)

## All Files Changed by This CAP

### Infrastructure / Deployment
| File | Type | Description |
|---|---|---|
| `scripts/deploy-vps2-edge.sh` | Modified | Fail-open → fail-closed health check |
| `services/portal-frontend/docker-compose.vps2.yml` | New | VPS2 service definition |
| `services/portal-frontend/vpn-cisco-entrypoint.sh` | Modified | Fixed expect wrapper (timeout -1) |
| `services/portal-frontend/nginx-failover-vps2.conf` | New | VPS2 nginx source-of-truth |
| `services/portal-frontend/nginx-gateway-32b-nginx.conf` | New | Gateway authoritative source |
| `03-vllm-14b-deploy/manifests/nginx-gateway-32b.yaml` | Modified | Rate limit values (300r/m, burst=20) |

### Application Code
| File | Type | Description |
|---|---|---|
| `services/ai-platform/app/main.py` | Modified | 429 passthrough (3 code blocks) |

### Documentation
| File | Type | Description |
|---|---|---|
| `docs/operations/VPS2_EDGE_DEPLOYMENT.md` | New | VPS2 edge deployment guide |
| `docs/operations/AI_PLATFORM_REDEPLOYMENT.md` | New | ai-platform build/deploy guide |
| `docs/operations/U1.2_ROLLBACK.md` | New | Rollback procedures |

### Evidence — Network Stability
| File | Type | Description |
|---|---|---|
| `docs/evidence/stage-u1.1-network-stability/00_EXECUTIVE_SUMMARY.md` | New | Network root cause summary |
| `docs/evidence/stage-u1.1-network-stability/07_ROOT_CAUSE_ANALYSIS.md` | New | VPN root cause analysis |

### Evidence — 32B Internet
| File | Type | Description |
|---|---|---|
| `docs/evidence/stage-u1.2-internet-32b/INTERNET_32B_ROOT_CAUSE.md` | Modified | Root cause (redacted keys) |
| `docs/evidence/stage-u1.2-internet-32b/INTERNET_32B_NGINX_DIFF.md` | New | Nginx config diff |
| `docs/evidence/stage-u1.2-internet-32b/INTERNET_32B_PERSISTENCE.md` | Modified | Persistence status (redacted keys) |
| `docs/evidence/stage-u1.2-internet-32b/INTERNET_32B_STABILITY_TESTS.md` | Modified | Stability tests (redacted keys) |
| `docs/evidence/stage-u1.2-internet-32b/INTERNET_32B_REGRESSION_TESTS.md` | New | Regression tests |
| `docs/evidence/stage-u1.2-internet-32b/U1.4_32B_CHAT_API_GAP.md` | New | API gap finding |

### Evidence — 32B Stability
| File | Type | Description |
|---|---|---|
| `docs/evidence/stage-u1.2-32b-stability/00_EXECUTIVE_SUMMARY.md` | New | Stability gate summary |
| `docs/evidence/stage-u1.2-32b-stability/07_ROOT_CAUSE_ANALYSIS.md` | New | Dual root cause analysis |
| `docs/evidence/stage-u1.2-32b-stability/08_CORRECTIVE_ACTIONS.md` | New | Corrective actions table |
| `docs/evidence/stage-u1.2-32b-stability/09_STABILITY_GATE_RESULTS.md` | New | Gate results (230/230) |
| `docs/evidence/stage-u1.2-32b-stability/10_PERSISTENCE_AND_REDEPLOY.md` | New | Persistence status |

### Evidence — Persistence & Redeploy
| File | Type | Description |
|---|---|---|
| `docs/evidence/stage-u1.2-persistence-redeploy/00_EXECUTIVE_SUMMARY.md` | New | CAP summary |
| `docs/evidence/stage-u1.2-persistence-redeploy/01_SOURCE_OF_TRUTH_MAPPING.md` | New | Source mapping |
| `docs/evidence/stage-u1.2-persistence-redeploy/04_AI_PLATFORM_IMAGE_BUILD.md` | New | Image build details |
| `docs/evidence/stage-u1.2-persistence-redeploy/05_COMMIT_SCOPE.md` | New | Commit scope audit |
| `docs/evidence/stage-u1.2-persistence-redeploy/06_LOCAL_CHECKS.md` | New | Local validation |
| `docs/evidence/stage-u1.2-persistence-redeploy/06_SECRET_SCAN.md` | New | Secret scan report |
| `docs/evidence/stage-u1.2-persistence-redeploy/08_429_PASSTHROUGH_TEST.md` | New | 429 test |
| `docs/evidence/stage-u1.2-persistence-redeploy/11_ROLLBACK_PLAN.md` | New | Rollback plan |
| `docs/evidence/stage-u1.2-persistence-redeploy/12_CHANGED_FILES.md` | New | Changed files list |
| `docs/evidence/stage-u1.2-persistence-redeploy/13_FINAL_STATUS.md` | New | Final status |

### Infrastructure (pre-existing, needed for build/deploy)
| File | Type | Description |
|---|---|---|
| `services/ai-platform/Dockerfile` | New | Build infrastructure |
| `services/ai-platform/k8s/ai-platform.yaml` | New | K8s deployment manifest |
| `services/ai-platform/requirements.txt` | New | Python dependencies |

**Total: 39 files (33 in parent commit + 6 CAP-01 additions/modifications)**
