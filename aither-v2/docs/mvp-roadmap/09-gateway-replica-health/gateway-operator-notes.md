# Gateway Operator Notes

## Stage 09 — nginx-gateway-32b Replica Health

### Service Info

| Property | Value |
|---|---|
| Deployment | nginx-gateway-32b |
| Namespace | aither-inference |
| Image | nginx:alpine |
| Port | 8000 |
| Selector | app=nginx-gateway,model=qwen-32b-gptq |
| Upstream | vllm-32b-gptq (ClusterIP: 10.99.3.103:8000) |

### Known Issues

#### 1. MissingClusterDNS on node n7 (cluster-level)

Both CoreDNS pods run on node n8. Node n7 (bootsmam-k8s-clnt01-n7-gpu) does not have ClusterDNS configured. This causes `MissingClusterDNS` warning on all pods scheduled on n7.

**Impact on gateway:** nginx on n7 cannot resolve Kubernetes service hostnames during initial startup (before remediation). Using ClusterIP avoids this issue.

**Mitigation applied:** nginx-gateway-32b ConfigMap uses ClusterIP `10.99.3.103` instead of hostname `vllm-32b-gptq.aither-inference.svc`.

**Long-term fix:** Deploy CoreDNS on n7.

#### 2. Many stale ReplicaSets

The gateway deployment has accumulated 9 stale ReplicaSets. This does not affect operation but clutters `kubectl get rs`. Cleanup recommended.

### Health Check

```bash
# Check gateway pods
kubectl get pods -n aither-inference -l app=nginx-gateway -o wide

# Expected: 2/2 Running, 0 CrashLoopBackOff

# Check gateway health
kubectl exec -n aither-inference deploy/nginx-gateway-32b -- curl -s http://localhost:8000/health

# Check gateway upstream connectivity
kubectl exec -n aither-inference deploy/nginx-gateway-32b -- curl -s http://10.99.3.103:8000/v1/models
```

### Regression Test After Any Gateway Change

```bash
# 1. Create API token with full scopes (one-time)
# 2. Test 32B completion:
TOKEN="athr_<token>"
POD=$(kubectl get pods -n aither-inference -l app=aither-portal -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n aither-inference $POD -- curl -s -X POST http://aither-bff:8000/api/v1/completions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"32b","prompt":"test"}'

# 3. Test 32B chat adapter:
kubectl exec -n aither-inference $POD -- curl -s -X POST http://aither-bff:8000/api/v1/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"32b","messages":[{"role":"user","content":"test"}]}'
```
