# RUNBOOK: Upgrade

## ai-platform Upgrade

### 1. Build New Image
```bash
cd /root/aither-project/aither-v2/services/ai-platform
TAG="ai-platform:u1.3-$(date +%Y%m%d-%H%M)"
docker build -t 10.129.13.78:5000/$TAG .
docker push 10.129.13.78:5000/$TAG
```

### 2. Deploy to K8s
```bash
ssh n8 "kubectl set image deploy/aither-ai-platform -n aither-inference \
  ai-platform=10.129.13.78:5000/$TAG && \
  kubectl rollout status deploy/aither-ai-platform -n aither-inference --timeout=120s"
```

### 3. Verify
```bash
curl -s http://10.129.13.78:30902/health  # Should return 200
curl -s http://10.129.13.78:30902/version  # Should show new version
```

### 4. Functional Test
```bash
# Test both models
curl -s -X POST http://10.129.13.78:30902/v1/chat/completions \
  -H "Authorization: Bearer <key>" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-14b-instruct","messages":[{"role":"user","content":"test"}],"max_tokens":5}'
```

### Rollback (if needed)
```bash
ssh n8 "kubectl rollout undo deploy/aither-ai-platform -n aither-inference"
```

## VPS2 nginx Config Upgrade

### 1. Update Source File
Edit `/root/aither-project/aither-v2/services/portal-frontend/nginx-failover-vps2.conf`.

### 2. Validate
```bash
docker run --rm -v $(pwd)/nginx-failover-vps2.conf:/etc/nginx/conf.d/default.conf:ro \
  nginx:alpine nginx -t
```

### 3. Apply
```bash
docker cp nginx-failover-vps2.conf aither-failover-nginx:/etc/nginx/conf.d/default.conf
docker exec aither-failover-nginx nginx -t
docker exec aither-failover-nginx nginx -s reload
```

### 4. Verify
```bash
curl -sk https://localhost:443/v1/models -H "Authorization: Bearer <key>"
```

## Gateway Config Upgrade

### 1. Update ConfigMap
Edit the nginx.conf in ConfigMap `nginx-gateway-32b`.

### 2. Apply
```bash
ssh n8 "kubectl apply -f - << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-gateway-32b
  namespace: aither-inference
data:
  nginx.conf: |
    <updated config>
EOF"
```

### 3. Restart
```bash
ssh n8 "kubectl rollout restart deploy/nginx-gateway-32b -n aither-inference"
```

## vLLM Model Update (Major)
**WARNING:** 5-10 minute outage. Schedule maintenance window.

```bash
# Update Deployment with new model or parameters
ssh n8 "kubectl apply -f <updated-deployment.yaml>"
ssh n8 "kubectl rollout status deploy/vllm-32b-gptq -n aither-inference --timeout=600s"
```

Run full health checklist after any vLLM change.
