# Stage 18A — Deployment Guide

## Prerequisites

- Two-node Kubernetes cluster (n7 worker, n8 control-plane)
- containerd v2.2.1+ on both nodes
- Private registry running on n8:5000
- kubectl access from build host
- **Secret `aither-identity-secret` must exist in namespace `aither-inference`**
  - Do NOT apply the example file directly
  - Create from `services/identity/k8s/identity-secret.example.yaml` after replacing placeholders

## Deployment Sequence

### 1. Build images (on build host)

```bash
# Build with current git SHA
./scripts/stage18a-build-images.sh 127.0.0.1:5000 $(git rev-parse --short HEAD)

# Or use fixed Stage 18A tag
GIT_SHA=$(git rev-parse --short HEAD)
TAG="stage18a-${GIT_SHA}"
```

### 2. Transfer images to n8

```bash
# Via rsync (recommended for unreliable SSH)
./scripts/stage18a-transfer-artifact.sh build-host n8

# After transfer, import into containerd and push to persistent registry
./scripts/stage18a-push-images.sh
```

### 3. Verify registry

```bash
./scripts/stage18a-verify-registry.sh
```

Expected output:
```
  containerd: active
  kubelet: active
  aither-registry: active
  GET /v2/_catalog: {"repositories":["aither-identity","aither-portal-backend","aither-ai-platform"]}
```

### 4. Update Kubernetes manifests

Update image tags in:
- `services/identity/k8s/identity.yaml`
- `services/portal-backend/k8s/portal-backend.yaml`
- `services/ai-platform/k8s/ai-platform.yaml`

Change `image:` from `:stage15`/`:stage16` to `:stage18a-<sha>`.

### 5. Deploy

```bash
./scripts/stage18a-deploy-services.sh
```

### 6. Verify deployment

```bash
kubectl get pods -n aither-inference -o wide
kubectl rollout status deployment/aither-identity -n aither-inference
kubectl rollout status deployment/aither-portal-backend -n aither-inference
kubectl rollout status deployment/aither-ai-platform -n aither-inference
```

## Rollback

To roll back to previous images:

```bash
kubectl set image deployment/aither-identity \
  -n aither-inference identity=10.129.13.78:5000/aither-identity:stage15
kubectl set image deployment/aither-portal-backend \
  -n aither-inference portal-backend=10.129.13.78:5000/aither-portal-backend:stage15
kubectl set image deployment/aither-ai-platform \
  -n aither-inference ai-platform=10.129.13.78:5000/aither-ai-platform:stage16
```

## PV/PVC Recovery

If hostPath directories have wrong permissions:

```bash
# On node where pod is scheduled
sudo chown -R 1000:1000 /data/aither/identity /data/aither/ai-platform
```

Then delete the pod to force recreation.
