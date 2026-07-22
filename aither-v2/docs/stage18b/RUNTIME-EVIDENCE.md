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

### Stage 18A Pods

| Pod | Node | Status | Ready | Restarts |
|-----|------|--------|-------|----------|
| aither-identity-79cbf4c96d-c7r2h | n8 | Running | 1/1 | 0 |
| aither-portal-backend-f44cfcbbc-c9f9j | n8 | Running | 1/1 | 0 |
| aither-ai-platform-d6fc574cf-gxjcm | n8 | Running | 1/1 | 0 |

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
