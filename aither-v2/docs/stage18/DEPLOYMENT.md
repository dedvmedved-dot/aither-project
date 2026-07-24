# Stage 18 — Deployment Guide

## Prerequisites

- Kubernetes cluster (2 nodes, v1.33.x)
- Docker images built for Stage 15–17 services
- `ctr` (containerd CLI) available on target nodes
- Gateway (nginx) and vLLM already deployed in namespace `aither-inference`

## Images Required

| Image | Tag | Source |
|---|---|---|
| `aither-identity` | `stage15` | `services/identity/` Dockerfile |
| `aither-portal-backend` | `stage15` | `services/portal-backend/` Dockerfile |
| `aither-ai-platform` | `stage16` | `services/ai-platform/` Dockerfile |
| `nginx` | `stable-alpine` | Docker Hub (portal frontend) |

## Image Distribution on Nodes

Since no registry is available, images must be loaded directly onto cluster nodes:

### Step 1: Build images

```bash
docker build -t aither-identity:stage15 -f services/identity/Dockerfile services/identity/
docker build -t aither-portal-backend:stage15 -f services/portal-backend/Dockerfile services/portal-backend/
docker build -t aither-ai-platform:stage16 -f services/ai-platform/Dockerfile services/ai-platform/
```

### Step 2: Save and transfer to nodes

```bash
# Save images
docker save aither-identity:stage15 | gzip > /tmp/aither-identity.tar.gz
docker save aither-portal-backend:stage15 | gzip > /tmp/aither-portal-backend.tar.gz
docker save aither-ai-platform:stage16 | gzip > /tmp/aither-ai-platform.tar.gz

# Transfer to each node (requires SSH access)
for NODE in n7 n8; do
  for IMG in aither-identity aither-portal-backend aither-ai-platform; do
    cat /tmp/${IMG}.tar.gz | ssh $NODE "ctr -n k8s.io images import -"
  done
done
```

### Step 3: Import into containerd

```bash
ctr -n k8s.io images import /tmp/aither-identity.tar.gz
ctr -n k8s.io images import /tmp/aither-portal-backend.tar.gz
ctr -n k8s.io images import /tmp/aither-ai-platform.tar.gz
```

### Step 4: Create required secrets

```bash
# Identity service secret (replace REPLACE_ME values)
kubectl apply -f services/identity/k8s/identity.yaml

# AI Platform secret template (replace if needed)
kubectl apply -f services/ai-platform/k8s/ai-platform.yaml
```

**Important:** Before applying, replace `REPLACE_ME` with real values in:
- `services/identity/k8s/identity.yaml` — `IDENTITY_SECRET_KEY`, `IDENTITY_ADMIN_PASS`

### Step 5: Deploy services

```bash
# Deploy in dependency order
kubectl apply -f services/identity/k8s/identity.yaml
kubectl apply -f services/portal-backend/k8s/portal-backend.yaml
kubectl apply -f services/portal-frontend/k8s/portal-frontend.yaml
kubectl apply -f services/ai-platform/k8s/ai-platform.yaml
```

### Step 6: Bootstrap admin user

```bash
# Get Identity pod name
kubectl exec -n aither-inference deploy/aither-identity -- \
  curl -s -X POST http://localhost:8000/v1/identity/bootstrap
```

### Step 7: Verify deployment

```bash
kubectl get pods -n aither-inference -w
kubectl get svc -n aither-inference
```

## Verification

After deployment, verify all services:

```bash
# Check pods
kubectl get pods -n aither-inference

# Test health endpoints (using port-forward)
kubectl port-forward -n aither-inference svc/aither-identity 8001:8000 &
curl http://localhost:8001/health
curl http://localhost:8001/ready
curl http://localhost:8001/version

kubectl port-forward -n aither-inference svc/aither-portal-backend 8002:8000 &
curl http://localhost:8002/health

kubectl port-forward -n aither-inference svc/aither-ai-platform 8003:8000 &
curl http://localhost:8003/health
```

## Rollback

```bash
kubectl delete deploy aither-identity aither-portal-backend aither-portal-frontend aither-ai-platform -n aither-inference
kubectl delete svc aither-identity aither-portal-backend aither-portal-frontend aither-ai-platform -n aither-inference
```
