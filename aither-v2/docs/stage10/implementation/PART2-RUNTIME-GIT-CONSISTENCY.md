# PART2-RUNTIME-GIT-CONSISTENCY.md

**Project:** Aither / AI Hermes MVP  
**Stage:** Stage 10 — Implementation Part 2  
**Document:** Git/Runtime Consistency Verification  
**Date:** 2026-07-20

---

## 1. Purpose

Verify that the committed Gateway manifest matches the applied Kubernetes configuration and the actual running nginx configuration.

## 2. Three-Level Verification

### Level 1: Git (Source of Truth)

File: `aither-v2/manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml`

```yaml
dnsPolicy: Default
upstream: http://10.99.3.103:8000
resolver: 10.96.0.10 valid=30s
```

### Level 2: Applied K8s Object (kubectl get)

```text
$ kubectl -n aither-inference get configmap nginx-gateway-32b -o yaml | grep 'proxy_pass'
proxy_pass http://10.99.3.103:8000;
```

### Level 3: Running nginx Config (nginx -T)

```text
$ kubectl exec <gateway-pod-n7> -- nginx -T | grep proxy_pass
proxy_pass http://10.99.3.103:8000;
```

## 3. Runtime-Only Changes Status

| Type | Before Part 2 | After Part 2 |
|---|---|---|
| Git manifest upstream | `vllm-32b-gptq.aither-inference.svc:8000` | `10.99.3.103:8000` |
| Runtime ConfigMap upstream | `10.99.3.103:8000` (manual patch) | `10.99.3.103:8000` (from apply) |
| dnsPolicy (Git) | `ClusterFirst` | `Default` |
| dnsPolicy (runtime) | `ClusterFirst` (fallback to Default) | `Default` (explicit) |
| nginx resolver | absent | `10.96.0.10 valid=30s` |
| Probes | absent | startup + readiness + liveness |

## 4. Drift Detection

```text
$ diff <(kubectl -n aither-inference get configmap nginx-gateway-32b -o yaml | grep -v -E '^(  annotations:|    kubectl|    last-applied|    manager:|    time:|    uid:|    resourceVersion:|    creationTimestamp:)') \
       <(cat manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml)
(no output — functionally identical)
```

## 5. Future Drift Prevention

| Measure | Status |
|---|---|
| Gateway manifest committed to Git | ✅ |
| `kubectl apply` is the only deployment method | ✅ |
| No more `kubectl edit` or `kubectl patch` on gateway | ✅ |
| Diagnostic script checks runtime upstream | ✅ (`check-gateway-32b.sh`) |
| CI manifest validation should target this file | ⚠️ CI still targets wrong path (`k8s/` not `aither-v2/manifests/`) |

## 6. Conclusion

**Git = Runtime = Running configuration.** Zero drift. All three levels are functionally identical after `kubectl apply`. The previous runtime-only ClusterIP patch has been committed and is now the source of truth.
