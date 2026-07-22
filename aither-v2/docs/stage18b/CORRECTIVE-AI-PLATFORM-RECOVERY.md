# Stage 18B-C3 — AI Platform Corrective Pod Recovery

## Purpose

Demonstrate actual AI Platform pod deletion, replacement pod creation, persistent marker survival, and health endpoint verification (Stage 18B did not previously demonstrate AI Platform pod recovery).

## Pre-test State

| Field | Value |
|-------|-------|
| Context | `kubernetes-admin@kubernetes` |
| Nodes | n7 Ready, n8 Ready |
| AI Platform deployment UID | `18e7d84e-f328-4f95-9f17-f9b972737f03` |
| Generation | 2 |
| observedGeneration | 2 |
| readyReplicas | 1 |
| availableReplicas | 1 |
| Current pod | `aither-ai-platform-d6fc574cf-gxjcm` |
| Pod UID | `c5946712-75c1-49a2-b00c-665138989c41` |
| Pod node | bootsman-k8s-clnt01-n8-gpu |
| Pod startTime | 2026-07-22T09:27:46Z |

## Volume Topology

| Layer | Value |
|-------|-------|
| Mount path | `/data` |
| PVC | `aither-ai-platform-data` (Bound) |
| PV | `pv-aither-ai-platform-data` (Bound, Retain) |
| Access mode | ReadWriteOnce |
| Capacity | 1Gi |
| Storage class | (default) |

## Corrective Marker

| Field | Value |
|-------|-------|
| Marker | `stage18b-c3-ai-platform-marker-1784743322` |
| Created in | `/data/stage18b-c3-marker.txt` |
| Mount verified | ✅ `/data` — ext4 on `/dev/mapper/...` (n8) |
| Write command | `printf '%s\n' 'stage18b-c3-ai-platform-marker-1784743322' > /data/stage18b-c3-marker.txt` |
| Write exit code | 0 |
| Read verification | `cat /data/stage18b-c3-marker.txt` → `stage18b-c3-ai-platform-marker-1784743322` |

## Pod Deletion

| Field | Value |
|-------|-------|
| Command | `kubectl delete pod aither-ai-platform-d6fc574cf-gxjcm -n aither-inference --wait=true` |
| Exit code | 0 |
| Deleted pod | `aither-ai-platform-d6fc574cf-gxjcm` |
| Deleted pod UID | `c5946712-75c1-49a2-b00c-665138989c41` |
| Timestamp | 2026-07-22T18:02:19Z |

## Replacement Pod

| Field | Value |
|-------|-------|
| Replacement pod | `aither-ai-platform-d6fc574cf-bfgqn` |
| Replacement pod UID | `17969774-d49c-46fe-8224-ff3e0579a90b` |
| Node | bootsman-k8s-clnt01-n8-gpu |
| Phase | Running |
| Container ready | true |
| Restart count | 0 |
| Start time | 2026-07-22T18:02:19Z |

## Rollout Verification

| Check | Result |
|-------|--------|
| Name differs | ✅ YES (old: `-gxjcm`, new: `-bfgqn`) |
| UID differs | ✅ YES (old: `c5946712-...`, new: `17969774-...`) |
| readyReplicas | 1 |
| availableReplicas | 1 |
| desired replicas | 1 |
| Deployment Available | ✅ 1/1 |
| `kubectl rollout status` exit code | N/A (k8s API intermittent — pod verified via `kubectl get pods` [Running] and `kubectl get deployment` [1/1 available]) |

## Persistent Marker After Recovery

| Field | Value |
|-------|-------|
| Read command | `kubectl exec -n aither-inference aither-ai-platform-d6fc574cf-bfgqn -- cat /data/stage18b-c3-marker.txt` |
| Exit code | 0 |
| Expected | `stage18b-c3-ai-platform-marker-1784743322` |
| Actual | `stage18b-c3-ai-platform-marker-1784743322` |
| **Verdict** | ✅ **Marker preserved** |

## Health ×3 After Recovery

| Attempt | Timestamp (UTC) | HTTP Status | Endpoint |
|---------|-----------------|-------------|----------|
| 1 | 2026-07-22T18:04:08Z | 200 | `GET /ready` (port 8000) |
| 2 | 2026-07-22T18:04:09Z | 200 | `GET /ready` (port 8000) |
| 3 | 2026-07-22T18:04:10Z | 200 | `GET /ready` (port 8000) |

## Other Services After Recovery

| Service | Health | Degradation |
|---------|--------|-------------|
| aither-identity | HTTP 200 | ❌ None |
| aither-portal-backend | HTTP 200 | ❌ None |
| All deployments | 1/1 Ready | ❌ None |
| PVC/PV | Both Bound | ❌ None |

## Conclusion

```text
AI Platform pod recovery:    ✅ PASS
- Pod deleted and replacement created
- Replacement UID differs from original
- Replacement pod Running and Ready
- Deployment 1/1 available
- Persistent marker preserved after recovery
- Health ×3: 200 / 200 / 200
- Other services not degraded
- PVC/PV bindings unchanged
```
