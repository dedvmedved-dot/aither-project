# Operational Readiness Review

## 1. Deployment

| Component | Mechanism | Status | Notes |
|---|---|---|---|
| VPS2 Edge | `scripts/deploy-vps2-edge.sh` | ✅ | Backup, validation, rollback |
| ai-platform | `kubectl set image` + rollout | ✅ | Locally built image, pushed to registry |
| nginx-gateway-32b | K8s ConfigMap + Deployment | ✅ | ConfigMap subPath mount |
| vLLM models | K8s Deployment (fixed image) | ⚠️ | No deployment automation for vLLM itself |

## 2. Shutdown
| Component | Procedure | Safe? |
|---|---|---|
| VPS2 containers | `docker stop` | ✅ No data loss |
| K8s pods | Scale to 0 or `kubectl delete` | ✅ Stateless |
| vLLM inference | `kubectl scale --replicas=0` | ✅ GPU freed |
| SQLite DB | Pod stop stops writes | ⚠️ In-flight writes may be lost |

## 3. Restart
| Component | Procedure | Verified? |
|---|---|---|
| VPS2 VPN + nginx | `deploy-vps2-edge.sh` | ✅ Script tested |
| ai-platform | image pull + pod recreate | ✅ K8s handles |
| vLLM | image pull + model load | ⚠️ 5-10 min startup (model loading) |
| Gateway | ConfigMap + rollout restart | ✅ |

## 4. Update
| Component | Procedure | Risk |
|---|---|---|
| ai-platform | Rebuild image, `kubectl set image` | Low — stateless |
| Gateway config | `kubectl apply ConfigMap`, rollout | Low |
| VPS2 nginx | `docker cp` + `nginx -s reload` | Low |
| vLLM model | New Deployment with model change | High — 5-10 min downtime |

## 5. Rollback
All components have documented rollback: `docs/operations/U1.2_ROLLBACK.md`
- ai-platform: `kubectl rollout undo` ✅ tested
- Gateway: `kubectl rollout undo` ✅ available
- VPS2: backup-based restore ✅ backup location verified

## 6. Backup
| Data | Location | Backup? |
|---|---|---|
| ai-platform SQLite | Pod filesystem `/data/` | ❌ No automated backup |
| Identity SQLite | Pod filesystem `/data/` | ❌ No automated backup |
| K8s manifests | Git repository | ✅ Committed |
| VPS2 configs | `/root/` + Git | ✅ Source-of-truth in repo |
| SSL certs | `/root/ssl-cert/` | ❌ Manual only |

## 7. Restore
No formal restore procedure exists. SQLite databases are ephemeral (pod restart = data loss).
**Critical gap for production.**

## 8. Logs
| Component | Logging | Access |
|---|---|---|
| ai-platform | Structured JSON to stdout | `kubectl logs` |
| vLLM | stdout | `kubectl logs` |
| nginx-gateway | stdout (access + error) | `kubectl logs` |
| VPS2 nginx | File `/var/log/nginx/` | `docker logs` / `docker exec` |
| VPN | stdout | `docker logs` |

No centralized log aggregation. No log rotation policy.

## 9. Monitoring

| Component | What's monitored | Gap |
|---|---|---|
| ai-platform | HTTP requests, errors, gateway, uptime, memory | No alerting |
| K8s | Pod health, readiness, liveness | No GPU metrics |
| vLLM | Internal health endpoint | No request-level metrics |
| VPN | Manual (`ip link show tun0`) | No automated health check |
| VPS2 | Manual (`docker ps`, `df`) | No disk/memory alerting |

## 10. Operational Instructions
See runbooks at same path. Coverage: startup, shutdown, backup, restore, upgrade, rollback, incident.
