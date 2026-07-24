# RUNBOOK: System Shutdown

## Procedure

### Option A: Graceful (preserve data)

#### 1. Notify Users
Send notification that system will be unavailable.

#### 2. Stop VPS2 Edge Services
```bash
docker stop aither-failover-nginx
docker stop vpn-cisco
```

#### 3. Scale Down K8s Workloads (optional — preserve GPU)
```bash
ssh n8 "kubectl scale deploy/aither-ai-platform -n aither-inference --replicas=0"
```

Note: Do NOT scale down vLLM deployments unless needed — model reload takes 5-10 minutes.

### Option B: Full Shutdown

#### 1. Stop VPS2 Services
```bash
docker stop aither-failover-nginx vpn-cisco ai-platform-test
```

#### 2. Stop K8s Inference
```bash
ssh n8 "
kubectl scale deploy/vllm-14b-instruct -n aither-inference --replicas=0
kubectl scale deploy/vllm-32b-gptq -n aither-inference --replicas=0
kubectl scale deploy/aither-ai-platform -n aither-inference --replicas=0
kubectl scale deploy/nginx-gateway-32b -n aither-inference --replicas=0
"
```

### Verification
```bash
docker ps | grep aither        # No aither containers
ssh n8 "kubectl get pods -n aither-inference | grep Running"  # No Running pods
```

## Rollback
Reverse the startup procedure using `RUNBOOK_STARTUP.md`.
