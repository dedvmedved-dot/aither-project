# PART2-RUNTIME-GIT-CONSISTENCY.md

**Project:** Aither / AI Hermes MVP
**Stage:** Stage 10 — Implementation Part 2 Remediation
**Document:** Git/Runtime Consistency Verification (Updated)
**Date:** 2026-07-20

---

## 1. Purpose

Verify that the committed Gateway manifest matches the applied Kubernetes configuration and the actual running nginx configuration using a **reproducible structural comparison**.

## 2. Methodology

Three distinct verification methods are applied:

### Method A: `kubectl diff` (Structural)

```bash
kubectl diff -f manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml
```

Uses Kubernetes server-side comparison. Returns empty output when the local manifest is equivalent to the applied configuration. Generated fields (`uid`, `resourceVersion`, `creationTimestamp`, `managedFields`, `status`, `pod-template-hash`) are automatically excluded by the server.

Fields compared:
- ConfigMap: `data.nginx.conf`
- Deployment: `spec.replicas`, `spec.template.spec.dnsPolicy`, `spec.template.spec.containers[0].image`, `spec.template.spec.containers[0].ports`, `spec.template.spec.containers[0].startupProbe`, `spec.template.spec.containers[0].readinessProbe`, `spec.template.spec.containers[0].livenessProbe`, `spec.template.spec.volumes`, `spec.template.spec.containers[0].resources`
- Service: `spec.ports`, `spec.selector`, `spec.type`

### Method B: 5-Level Upstream Comparison

Compare the proxy_pass target for `/v1/completions` across all layers:

| Level | Source | Command |
|---|---|---|
| 1 | Service ClusterIP | `kubectl get svc vllm-32b-gptq -o jsonpath='{.spec.clusterIP}'` |
| 2 | Git manifest | `awk '/location \/v1\/completions/,/}/' <manifest> \| grep proxy_pass` |
| 3 | Runtime ConfigMap | `kubectl get configmap nginx-gateway-32b -o jsonpath='{.data.nginx\.conf}'` |
| 4 | Running nginx (n7) | `kubectl exec <pod-n7> -- nginx -T` |
| 5 | Running nginx (n8) | `kubectl exec <pod-n8> -- nginx -T` |

Acceptance: **All 5 values must be identical**.

### Method C: Service + Deployment Field Verification

Compare structured fields using `kubectl get ... -o json` and `diff`:

```bash
diff <(kubectl -n aither-inference get deployment nginx-gateway-32b -o json | jq '{spec: .spec}' | ...) \
     <(cat manifest.yaml | ...)
```

## 3. Results

### 3.1. Method A: `kubectl diff`

```text
$ kubectl diff -f manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml
(no output — zero drift)
```

### 3.2. Method B: 5-Level Upstream Consistency

| Level | Value | Match |
|---|---|---|
| 1. Service ClusterIP | `10.99.3.103:8000` | ✅ |
| 2. Git manifest upstream | `10.99.3.103:8000` | ✅ |
| 3. Runtime ConfigMap upstream | `10.99.3.103:8000` | ✅ |
| 4. Running nginx upstream (n7) | `10.99.3.103:8000` | ✅ |
| 5. Running nginx upstream (n8) | `10.99.3.103:8000` | ✅ |

**Unique values: 1 — ALL MATCH.**

### 3.3. Method C: Deployment Field Verification

| Field | Git | Runtime | Match |
|---|---|---|---|
| `spec.replicas` | 2 | 2 | ✅ |
| `spec.template.spec.dnsPolicy` | Default | Default | ✅ |
| `spec.template.spec.containers[0].image` | nginx:alpine | nginx:alpine | ✅ |
| `spec.template.spec.containers[0].ports[0].containerPort` | 8000 | 8000 | ✅ |
| `startupProbe.httpGet.path` | /healthz | /healthz | ✅ |
| `readinessProbe.httpGet.path` | /health | /health | ✅ |
| `livenessProbe.httpGet.path` | /healthz | /healthz | ✅ |
| `ConfigMap volume name` | config | config | ✅ |
| `mountPath` | /etc/nginx/nginx.conf | /etc/nginx/nginx.conf | ✅ |
| `resources.requests.cpu` | 50m | 50m | ✅ |
| `resources.requests.memory` | 64Mi | 64Mi | ✅ |
| `resources.limits.cpu` | 500m | 500m | ✅ |
| `resources.limits.memory` | 256Mi | 256Mi | ✅ |

## 4. Service Field Verification

| Field | Git | Runtime | Match |
|---|---|---|---|
| `metadata.name` | nginx-gateway-32b | nginx-gateway-32b | ✅ |
| `metadata.namespace` | aither-inference | aither-inference | ✅ |
| `spec.selector.app` | nginx-gateway | nginx-gateway | ✅ |
| `spec.selector.model` | qwen-32b-gptq | qwen-32b-gptq | ✅ |
| `spec.ports[0].port` | 8000 | 8000 | ✅ |
| `spec.ports[0].targetPort` | 8000 | 8000 | ✅ |
| `spec.type` | ClusterIP | ClusterIP | ✅ |

## 5. Runtime-Only Changes Status

| Type | Before Part 2 | After Remediation |
|---|---|---|
| Git manifest upstream | `vllm-32b-gptq.aither-inference.svc:8000` | `10.99.3.103:8000` |
| Runtime ConfigMap upstream | `10.99.3.103:8000` (manual patch) | `10.99.3.103:8000` (from apply) |
| dnsPolicy (Git) | `ClusterFirst` | `Default` |
| dnsPolicy (runtime) | `ClusterFirst` (fallback to Default) | `Default` (explicit) |
| nginx resolver | absent | `10.96.0.10 valid=30s` |
| Probes | absent | startup + readiness + liveness |
| Runtime-only changes | ✅ **ELIMINATED** | Zero manual patches |

## 6. Future Drift Prevention

| Measure | Status |
|---|---|
| Gateway manifest committed to Git | ✅ |
| `kubectl apply` is the only deployment method | ✅ |
| No more `kubectl edit` or `kubectl patch` on gateway | ✅ |
| Diagnostic script verifies 5-level upstream consistency | ✅ (`check-gateway-32b.sh`) |
| Structural `kubectl diff` verifies zero deployment drift | ✅ |
| E2E test validates authenticated completion through Gateway | ✅ (`test-gateway-32b-e2e.sh`) |

## 7. Conclusion

**Zero drift verified through three complementary methods:**

1. **`kubectl diff`** — structural server-side comparison returns empty (no differences)
2. **5-level upstream consistency** — Service ClusterIP = Git = Runtime ConfigMap = Running nginx (both pods)
3. **Field-by-field verification** — all 13 deployment fields + 7 service fields match

No runtime-only changes remain. The previous runtime-only ClusterIP patch has been committed and is now the source of truth. Any future drift will be caught by `kubectl diff` and the diagnostic script.
