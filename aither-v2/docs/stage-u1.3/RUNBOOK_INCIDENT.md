# RUNBOOK: Incident Response

## Incident Severity Levels

| Level | Description | Response Time |
|---|---|---|
| P1 | Total outage — all routes down | Immediate |
| P2 | Partial outage — one model or route down | <30 min |
| P3 | Degraded performance — slow responses | <2 hours |
| P4 | Non-critical — cosmetic, documentation | Next business day |

## Common Incidents

### INC-01: API Returns 504 Gateway Timeout

**Symptoms:**
- `curl` returns HTTP 504 from Internet routes
- Test Zone (:30902) works fine

**Diagnosis:**
```bash
# Check VPN
ip link show tun0
ping -c 2 10.129.13.78
docker logs vpn-cisco --tail=20
```

**Fix:**
```bash
# Option A: Restart VPN
docker restart vpn-cisco
sleep 30
ping -c 2 10.129.13.78

# Option B: Full VPS2 redeploy
bash scripts/deploy-vps2-edge.sh
```

### INC-02: Model Returns Error or Times Out

**Symptoms:**
- HTTP 502 or 504 from ai-platform
- One model fails, other works

**Diagnosis:**
```bash
ssh n8 "kubectl get pods -n aither-inference | grep vllm"
ssh n8 "kubectl logs -n aither-inference deploy/vllm-14b-instruct --tail=30"
ssh n8 "kubectl logs -n aither-inference deploy/vllm-32b-gptq --tail=30"
```

Look for: OOM, CUDA error, "engine dead", "queue full"

**Fix:**
```bash
# Restart the affected vLLM pod
ssh n8 "kubectl rollout restart deploy/vllm-14b-instruct -n aither-inference"
# Wait 5-10 minutes for model to load
ssh n8 "kubectl logs -n aither-inference deploy/vllm-14b-instruct -f"
```

### INC-03: K8s Pod CrashLoopBackOff

**Symptoms:**
- `kubectl get pods` shows CrashLoopBackOff status
- Service unavailable

**Diagnosis:**
```bash
ssh n8 "kubectl get pods -n aither-inference"
ssh n8 "kubectl describe pod <pod-name> -n aither-inference | tail -30"
ssh n8 "kubectl logs <pod-name> -n aither-inference --tail=50"
```

**Fix:**
- If config issue: fix ConfigMap/Secret, rollout restart
- If image issue: rollback to previous image
- If resource issue: check node resources

### INC-04: VPS2 Out of Disk Space

**Symptoms:**
- `df -h` shows >90% usage
- Docker pull/push fails
- nginx can't write logs

**Diagnosis:**
```bash
df -h /
du -sh /var/lib/docker/*
du -sh /root/*
```

**Fix:**
```bash
# Clean Docker
docker system prune -a --volumes  # CAUTION: removes unused images

# Clean old logs
find /var/log -name "*.log" -mtime +7 -delete
```

### INC-05: API Key Not Working

**Symptoms:**
- HTTP 401 on all requests

**Diagnosis:**
- Check if key was revoked
- Check if identity pod is running

**Fix:**
```bash
# Check identity service
ssh n8 "kubectl get pods -n aither-inference -l app=aither-identity"
ssh n8 "kubectl logs -n aither-inference deploy/aither-identity --tail=20"

# Generate new key (requires admin token)
# See user documentation
```

## Escalation
If incident cannot be resolved within response time:
1. Notify platform team lead
2. If GPU issue: contact infrastructure team
3. If VPN issue: contact network team
4. Document incident in post-mortem
