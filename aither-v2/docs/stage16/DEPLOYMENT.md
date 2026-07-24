# Stage 16 — Deployment Guide

## Prerequisites

- Stage 14 deployment framework configured
- Stage 15 Identity + Portal deployed
- Kubernetes cluster with PVC support
- Docker images built for:
  - `aither-ai-platform:stage16`
  - `aither-identity:stage15` (updated with PVC)
  - `aither-portal-backend:stage15` (updated with AI Platform URL)
  - `aither-portal-frontend:stage15` (updated nginx + frontend)

## Build Images

```bash
cd services/ai-platform && docker build -t aither-ai-platform:stage16 .
cd ../identity && docker build -t aither-identity:stage15 .
cd ../portal-backend && docker build -t aither-portal-backend:stage15 .
cd ../portal-frontend && docker build -t aither-portal-frontend:stage15 .
```

## Environment Variables

### AI Platform
| Variable | Default | Required |
|---|---|---|
| `AI_PLATFORM_DB_PATH` | `/data/ai-platform.db` | No |
| `AI_PLATFORM_IDENTITY_URL` | `http://aither-identity:8000` | No |
| `AI_PLATFORM_GATEWAY_URL` | `http://nginx-gateway-32b.aither-inference.svc:8000` | No |
| `AI_PLATFORM_LOG_LEVEL` | `INFO` | No |
| `AI_PLATFORM_CORS_ORIGIN` | `http://localhost:3000` | No |

## Secrets to Create

```bash
# Identity Secret (REPLACE_ME with real values)
kubectl create secret generic aither-identity-secret \
  -n aither-inference \
  --from-literal=IDENTITY_SECRET_KEY='<random-32-char-min>' \
  --from-literal=IDENTITY_ADMIN_USER='admin' \
  --from-literal=IDENTITY_ADMIN_PASS='<bcrypt-hash>'
```

## Deploy

```bash
# Full deployment (includes all Stage 15+16 services)
bash deploy/deploy.sh

# Or apply Stage 16 manifests individually:
kubectl apply -f services/ai-platform/k8s/ai-platform.yaml
kubectl apply -f services/identity/k8s/identity.yaml  # Updated with PVC
kubectl apply -f services/portal-backend/k8s/portal-backend.yaml
kubectl apply -f services/portal-frontend/k8s/portal-frontend.yaml
```

## Bootstrap Model Registry

After deployment, register the default model:

```bash
# Get admin token
TOKEN=$(curl -s -X POST http://<portal>/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"<password>"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# Register model
curl -X POST http://<ai-platform>/api/v1/models \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "qwen-14b-instruct",
    "display_name": "Qwen 14B Instruct",
    "provider": "local",
    "model_identifier": "qwen-14b-instruct",
    "description": "Chat model via vLLM",
    "context_window": 8192,
    "enabled": true
  }'
```

## Upgrade from Stage 15

1. Apply new PVC manifests (`aither-identity-data`, `aither-ai-platform-data`)
2. Update Identity deployment (add PVC, securityContext)
3. Deploy AI Platform service
4. Update Portal Backend (add AI_PLATFORM_URL env)
5. Update Portal Frontend (new nginx.conf with /v1/chat/completions route)

## Rollback

1. Delete AI Platform: `kubectl delete deployment aither-ai-platform -n aither-inference`
2. Keep PVCs for data preservation
3. Revert Portal Frontend nginx.conf
4. Revert Portal Backend env

## PVC Data Backup

```bash
# Backup Identity DB
kubectl exec deployment/aither-identity -n aither-inference -- cat /data/identity.db > identity-backup.db

# Backup AI Platform DB
kubectl exec deployment/aither-ai-platform -n aither-inference -- cat /data/ai-platform.db > ai-platform-backup.db
```
