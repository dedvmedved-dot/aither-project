# RUNBOOK: System Startup

## Prerequisites
- Access to VPS2 (130.17.1.90) via SSH
- Access to K8s cluster (n8: 10.129.13.78)
- `OPENCONNECT_PASSWORD` and `OPENCONNECT_GROUP` environment variables
- SSL certificates at `/root/ssl-cert/`

## Procedure

### 1. Start VPN Tunnel
```bash
cd /root/aither-project/aither-v2
export OPENCONNECT_PASSWORD="<from-secret-store>"
export OPENCONNECT_GROUP="<from-secret-store>"
bash scripts/deploy-vps2-edge.sh
```

Wait for output: `✅ tun0 ready` and `✅ Route to 10.129.13.78 present`.

### 2. Verify VPN
```bash
ip link show tun0         # Should show UP
ip route get 10.129.13.78 # Should use dev tun0
ping -c 2 10.129.13.78    # Should get replies
```

### 3. Verify K8s Cluster
```bash
ssh n8 "kubectl get nodes"     # Both nodes Ready
ssh n8 "kubectl get pods -n aither-inference"  # All Running
```

### 4. Verify AI Services
```bash
API_KEY="<your-api-key>"
# Models list
curl -s https://localhost:443/v1/models -H "Authorization: Bearer $API_KEY"

# 14B test
curl -s -X POST https://localhost:443/v1/chat/completions \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-14b-instruct","messages":[{"role":"user","content":"ping"}],"max_tokens":5}'

# 32B test
curl -s -X POST https://localhost:443/v1/chat/completions \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-32b-gptq","messages":[{"role":"user","content":"ping"}],"max_tokens":5}'
```

Expected: HTTP 200 on all three.

### 5. Run Health Checklist
Follow `03_HEALTH_CHECKLIST.md`.

## Expected Total Time
- VPN startup: 30-60 seconds
- K8s verification: 10 seconds
- Service verification: 30 seconds
- Total: ~2 minutes (if K8s pods already running)
