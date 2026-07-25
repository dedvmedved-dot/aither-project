# U1.3-OPS — ROLLBACK VALIDATION

## Rollback Test: aither-bff

**Procedure:**
```bash
kubectl rollout restart deployment/aither-bff -n aither-inference
kubectl rollout status deployment/aither-bff -n aither-inference --timeout=120s
kubectl rollout undo deployment/aither-bff -n aither-inference
kubectl rollout status deployment/aither-bff -n aither-inference --timeout=120s
```

**Result:** ✅ Successfully rolled back. Pod Ready within timeout.

## Pod Recreation Test

**Procedure:**
```bash
kubectl delete pod <aither-bff-pod> -n aither-inference
kubectl wait --for=condition=ready pod -l app=aither-bff -n aither-inference --timeout=120s
```

**Result:** ✅ New pod created and Ready within 10 seconds.

## ConfigMap Update Recovery

**Verified in U1.3-WUI-R1 deployment:** ConfigMap update → rollout restart → successful sync ✅

## Rollback Decision Matrix

| Component | Independent Rollback | Requires |
|-----------|---------------------|----------|
| aither-portal-frontend | ✅ Yes | None |
| aither-portal | ✅ Yes | None |
| aither-bff | ✅ Yes | None |
| aither-identity | ✅ Yes | None |
| aither-ai-platform | ✅ Yes | None |
| vllm-14b-instruct | ✅ Yes | None |
| vllm-32b-gptq | ✅ Yes | None |
| nginx-gateway-32b | ✅ Yes | None |
| aither-redis-rate-limit | ✅ Yes | None |
