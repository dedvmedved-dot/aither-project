# Stage 18B — Runtime Evidence

## Cluster State (2026-07-22)

### Nodes

| Node | Status | Role | Version |
|------|--------|------|---------|
| `bootsmam-k8s-clnt01-n7-gpu` | Ready | <none> | v1.33.5 |
| `bootsman-k8s-clnt01-n8-gpu` | Ready | control-plane | v1.33.5 |

### containerd

| Node | Status | Enabled | Version |
|------|--------|---------|---------|
| n7 (10.129.13.77) | active | enabled | 2.2.1.astra0 |
| n8 (10.129.13.78) | active | enabled | 2.2.1.astra0 |

### CRI (n8)

| Check | Result |
|-------|--------|
| RuntimeReady | true |
| NetworkReady | true |
| crictl version | 0.1.0 |
| RuntimeVersion | 2.2.1.astra0 |

### Registry

| Check | Result |
|-------|--------|
| Host | 10.129.13.78:5000 |
| API /v2/ | `{}` (200 OK) |
| Catalog | 3 repositories |
| Tags | `stage18a-82fe433` on all |
| Service status | active |

### Stage 18A Deployments

| Deployment | Ready | Available | Image |
|------------|-------|-----------|-------|
| aither-identity | 1/1 | 1 | `10.129.13.78:5000/aither-identity:stage18a-82fe433` |
| aither-portal-backend | 1/1 | 1 | `10.129.13.78:5000/aither-portal-backend:stage18a-82fe433` |
| aither-ai-platform | 1/1 | 1 | `10.129.13.78:5000/aither-ai-platform:stage18a-82fe433` |

### Stage 18A Pods (original baseline)

| Pod | Node | Status | Ready | Restarts |
|-----|------|--------|-------|----------|
| aither-identity-79cbf4c96d-c7r2h | n8 | Running | 1/1 | 0 |
| aither-portal-backend-f44cfcbbc-c9f9j | n8 | Running | 1/1 | 0 |
| aither-ai-platform-d6fc574cf-gxjcm | n8 | Running | 1/1 | 0 |

### AI Platform Corrective Pod Recovery (Stage 18B-C3)

**Purpose:** Demonstrate actual AI Platform pod deletion, replacement, and persistent marker survival (previously not demonstrated in Stage 18B).

**Pre-test pod:**

| Field | Value |
|-------|-------|
| Pod | `aither-ai-platform-d6fc574cf-gxjcm` |
| UID | `c5946712-75c1-49a2-b00c-665138989c41` |
| Node | bootsman-k8s-clnt01-n8-gpu |
| Start time | 2026-07-22T09:27:46Z |
| PVC | `aither-ai-platform-data` |
| PV | `pv-aither-ai-platform-data` |

**Deleted pod:**

| Field | Value |
|-------|-------|
| Pod | `aither-ai-platform-d6fc574cf-gxjcm` |
| UID | `c5946712-75c1-49a2-b00c-665138989c41` |
| Deletion command | `kubectl delete pod ... --wait=true` |
| Exit code | 0 |
| Timestamp | 2026-07-22T18:02:19Z |

**Replacement pod:**

| Field | Value |
|-------|-------|
| Pod | `aither-ai-platform-d6fc574cf-bfgqn` |
| UID | `17969774-d49c-46fe-8224-ff3e0579a90b` |
| Node | bootsman-k8s-clnt01-n8-gpu |
| Start time | 2026-07-22T18:02:19Z |
| Phase | Running |
| Container ready | true |
| Restart count | 0 |
| Rollout result | 1 ready / 1 available / 1 desired |
| `kubectl rollout status` | `deployment "aither-ai-platform" successfully rolled out` (2026-07-22T21:05:51Z) |
| Rollout exit code | **0** |

**Persistent marker:**

| Field | Value |
|-------|-------|
| Marker | `stage18b-c3-ai-platform-marker-1784743322` |
| Before deletion | ✅ present |
| After recovery | ✅ present (exact match) |
| Read command | `kubectl exec ... cat /data/stage18b-c3-marker.txt` |
| Exit code | 0 |

**Health ×3 after recovery:**

| Attempt | Timestamp | HTTP Status |
|---------|-----------|-------------|
| 1 | 2026-07-22T18:04:08Z | 200 |
| 2 | 2026-07-22T18:04:09Z | 200 |
| 3 | 2026-07-22T18:04:10Z | 200 |

**Other services after recovery:** identity HTTP 200, portal-backend HTTP 200. No CrashLoopBackOff, no ImagePullBackOff, no PVC degradation.

### PVC/PV

| PVC | Status | PV | Access Mode | Capacity |
|-----|--------|----|-------------|----------|
| aither-identity-data | Bound | pv-aither-identity-data | RWO | 1Gi |
| aither-ai-platform-data | Bound | pv-aither-ai-platform-data | RWO | 1Gi |

### Secret

| Secret | Namespace | UID | Exists |
|--------|-----------|-----|--------|
| aither-identity-secret | aither-inference | `4bfb16b9-7cee-46a4-9e5a-951a9195549b` | ✅ |

### Health Endpoints

| Service | Endpoint | ×3 Attempts | Status |
|---------|----------|-------------|--------|
| aither-identity | `/health` | 200, 200, 200 | ✅ PASS |
| aither-portal-backend | `/health` | 200, 200, 200 | ✅ PASS |
| aither-ai-platform | `/health` | 200, 200, 200 | ✅ PASS |
