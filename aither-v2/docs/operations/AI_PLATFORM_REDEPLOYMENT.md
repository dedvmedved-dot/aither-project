# AI Platform Redeployment

## Prerequisites
- Docker on build machine with access to `10.129.13.78:5000` registry
- Source code from repository: `services/ai-platform/`
- kubectl access to cluster

## Build

```bash
cd services/ai-platform
TAG="ai-platform:u1.2-$(date +%Y%m%d-%H%M)"
docker build -t 10.129.13.78:5000/${TAG} .
docker push 10.129.13.78:5000/${TAG}
```

## Deploy

```bash
kubectl set image deploy/aither-ai-platform -n aither-inference \
  ai-platform=10.129.13.78:5000/${TAG}
kubectl rollout status deploy/aither-ai-platform -n aither-inference --timeout=120s
```

## Verify

```bash
kubectl get pods -n aither-inference -l app=aither-ai-platform
kubectl logs -n aither-inference deploy/aither-ai-platform --tail=10
```

## Rollback

```bash
kubectl rollout undo deploy/aither-ai-platform -n aither-inference
```
Previous image: `10.129.13.78:5000/ai-platform:u1-3-models-fix` (revision 18)

## Health Check

```bash
curl -s http://10.129.13.78:30902/health
# Expected: {"status":"ok","service":"ai-platform"}
```
