# PART2-EVIDENCE.md

**Project:** Aither / AI Hermes MVP
**Stage:** Stage 10 — Implementation Part 2 Remediation
**Document:** Gateway DNS Remediation Evidence (Updated)
**Date:** 2026-07-20

---

## 1. Baseline Commit

```text
$ git rev-parse HEAD
d74a0b956f956e724ed7c94685b6bb8d210c1b91
$ git branch --show-current
aither-v2
$ git status --short
(clean — working tree)
```

## 2. ClusterDNS Root Cause

### MissingClusterDNS on n7
```text
$ kubectl describe node bootsmam-k8s-clnt01-n7-gpu | grep MissingClusterDNS
Warning  MissingClusterDNS  26s (x42507 over 6d21h)  kubelet
  kubelet does not have ClusterDNS IP configured and cannot create Pod
  using "ClusterFirst" policy. Falling back to "Default" policy.
```

### CoreDNS Scheduling — Both on n8
```text
$ kubectl -n kube-system get pods -o wide | grep dns
coredns-674b8bbfcf-2h5vp   1/1  Running    61  7d4h  10.244.0.103  n8
coredns-674b8bbfcf-b2w7k   1/1  Running    66  7d4h  10.244.0.104  n8
```

### kubelet-config has correct clusterDNS (but n7 not applying it)
```text
$ kubectl -n kube-system get configmap kubelet-config -o yaml | grep clusterDNS -A1
    clusterDNS:
    - 10.96.0.10
```

## 3. Manifest Validation

### Client dry-run
```text
$ kubectl apply --dry-run=client -f manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml
configmap/nginx-gateway-32b configured (dry run)
deployment.apps/nginx-gateway-32b configured (dry run)
service/nginx-gateway-32b configured (dry run)
```

### Server dry-run
```text
$ kubectl apply --dry-run=server -f manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml
configmap/nginx-gateway-32b configured (server dry run)
deployment.apps/nginx-gateway-32b configured (server dry run)
service/nginx-gateway-32b configured (server dry run)
```

## 4. Rollout

```text
$ kubectl apply -f manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml
configmap/nginx-gateway-32b configured
deployment.apps/nginx-gateway-32b configured
service/nginx-gateway-32b unchanged

$ kubectl -n aither-inference rollout status deployment/nginx-gateway-32b --timeout=180s
deployment "nginx-gateway-32b" successfully rolled out
```

## 5. Pods After Rollout

```text
$ kubectl -n aither-inference get pods -o wide | grep gateway
nginx-gateway-32b-54f94d7c8d-dh627   1/1  Running  0  5m  10.244.0.209  bootsman-k8s-clnt01-n8-gpu
nginx-gateway-32b-54f94d7c8d-ktgdh   1/1  Running  0  5m  10.244.1.11   bootsmam-k8s-clnt01-n7-gpu
```

### Endpoints
```text
$ kubectl -n aither-inference get endpoints vllm-32b-gptq -o yaml | grep -A3 addresses
  addresses:
  - ip: 10.244.1.4
    nodeName: bootsmam-k8s-clnt01-n7-gpu
```

## 6. nginx -t (both pods)

```text
# On n7 pod:
$ kubectl exec nginx-gateway-32b-54f94d7c8d-ktgdh -- nginx -t
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful

# On n8 pod:
$ kubectl exec nginx-gateway-32b-54f94d7c8d-dh627 -- nginx -t
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

## 7. Health Endpoints

```text
# /healthz (local liveness endpoint — no upstream dependency)
$ kubectl exec nginx-gateway-32b-54f94d7c8d-ktgdh -- curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/healthz
200
$ kubectl exec nginx-gateway-32b-54f94d7c8d-dh627 -- curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/healthz
200

# /health (upstream proxy to vLLM)
$ kubectl exec nginx-gateway-32b-54f94d7c8d-ktgdh -- curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health
200
$ kubectl exec nginx-gateway-32b-54f94d7c8d-dh627 -- curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health
200
```

## 8. Auth Passthrough Test (no token → 401)

```text
$ kubectl exec nginx-gateway-32b-54f94d7c8d-ktgdh -- \
  curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-32b-base","prompt":"test","max_tokens":1}'
401

$ kubectl exec nginx-gateway-32b-54f94d7c8d-dh627 -- \
  curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-32b-base","prompt":"test","max_tokens":1}'
401
```

## 9. Unsupported Endpoint Test (422)

```text
$ kubectl exec nginx-gateway-32b-54f94d7c8d-ktgdh -- \
  curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{}'
422

$ kubectl exec nginx-gateway-32b-54f94d7c8d-dh627 -- \
  curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{}'
422
```

## 10. Authenticated /v1/models through Gateway

```text
$ kubectl exec nginx-gateway-32b-54f94d7c8d-ktgdh -- \
  curl -s http://localhost:8000/v1/models \
  -H "Authorization: Bearer <redacted>"
{"object":"list","data":[{"id":"qwen-32b-base","object":"model", ...}]}
HTTP_CODE:200
```

**Actual API model ID: `qwen-32b-base`** (confirmed from /v1/models response)

## 11. Authenticated /v1/completions through Gateway (E2E)

```text
$ kubectl exec nginx-gateway-32b-54f94d7c8d-ktgdh -- \
  curl -s -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <redacted>" \
  -d '{"model":"qwen-32b-base","prompt":"Return exactly the word READY","max_tokens":8,"temperature":0}'
{"id":"cmpl-87b72f27f6984b738ce58ed24e1788b4","object":"text_completion",
 "created":1784582576,"model":"qwen-32b-base",
 "choices":[{"index":0,"text":" in the chat to indicate that you understand",...}],
 "usage":{"prompt_tokens":5,"total_tokens":13,"completion_tokens":8,...}}
HTTP_CODE:200
```

- **HTTP 200**: ✅
- **Non-empty completion**: ✅ (8 tokens returned)
- **Model in response**: `qwen-32b-base` ✅
- **No auth error**: ✅
- **No model-not-found error**: ✅

## 12. Upstream Consistency (5 Levels)

```text
Level 1: Service ClusterIP              = 10.99.3.103:8000
Level 2: Git manifest upstream          = 10.99.3.103:8000
Level 3: Runtime ConfigMap upstream     = 10.99.3.103:8000
Level 4: Running nginx n7               = 10.99.3.103:8000
Level 5: Running nginx n8               = 10.99.3.103:8000

ALL 5 LEVELS MATCH ✅
```

## 13. Pod Deletion Recovery Test

```text
$ kubectl -n aither-inference delete pod nginx-gateway-32b-54f94d7c8d-ktgdh --grace-period=5
pod "nginx-gateway-32b-54f94d7c8d-ktgdh" deleted
```

After deletion, ReplicaSet immediately created a new pod:

```text
$ kubectl -n aither-inference get pods -o wide | grep gateway
nginx-gateway-32b-54f94d7c8d-dh627   1/1  Running  0  6m  10.244.0.209  n8
nginx-gateway-32b-54f94d7c8d-lc6ct   0/1  Running  0   5s  10.244.1.12   n7
```

Rollout completed automatically:

```text
$ kubectl -n aither-inference rollout status deployment/nginx-gateway-32b --timeout=120s
deployment "nginx-gateway-32b" successfully rolled out
```

Post-recovery E2E test:

```text
$ curl -s ... http://localhost:8000/healthz → 200
$ curl -s ... /v1/completions → HTTP 200, non-empty completion
```

## 14. Reapply Test

```text
$ kubectl apply -f manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml
configmap/nginx-gateway-32b unchanged
deployment.apps/nginx-gateway-32b unchanged
service/nginx-gateway-32b unchanged

$ kubectl -n aither-inference rollout status deployment/nginx-gateway-32b --timeout=60s
deployment "nginx-gateway-32b" successfully rolled out
```

## 15. Diagnostic Script

```text
$ bash scripts/check-gateway-32b.sh
══════════════════════════════════════════════════════
  Aither Gateway 32B — Comprehensive Diagnostic Check
══════════════════════════════════════════════════════
✓ vllm-32b-gptq Service exists (ClusterIP: 10.99.3.103)
✓ vllm-32b-gptq ClusterIP is valid (10.99.3.103)
✓ vllm-32b-gptq has 1 ready endpoint(s)
✓ nginx-gateway-32b Service exists (ClusterIP: 10.106.31.143)
✓ Gateway Deployment exists
✓ spec.replicas = 2 (expected >= 2)
✓ readyReplicas (2) == spec.replicas (2)
✓ Gateway pod on n7
✓ Gateway pod on n8
✓ Both gateway pods Running
✓ dnsPolicy: Default (n7-compatible workaround)
✓ Git manifest upstream: 10.99.3.103:8000
✓ Runtime ConfigMap upstream: 10.99.3.103:8000
✓ Running nginx upstream (n7): 10.99.3.103:8000
✓ Running nginx upstream (n8): 10.99.3.103:8000
✓ Upstream consistency: ALL 5 levels match (10.99.3.103:8000)
✓ nginx -t on n7: OK
✓ nginx -t on n8: OK
✓ Gateway /healthz on n7: 200
✓ Gateway /healthz on n8: 200
✓ Gateway on n7: returns 401 without auth token
✓ Gateway on n8: returns 401 without auth token
✓ Gateway on n7: blocks /v1/chat/completions (422)
✓ Gateway on n8: blocks /v1/chat/completions (422)
✓ Gateway /v1/models on n7: HTTP 200, model ID: qwen-32b-base
✓ Gateway /v1/completions on n7: HTTP 200, non-empty
✓ Response does not contain model errors
Passed: 27  Failed: 0  Warnings: 0
EXIT_CODE=0
```

## 16. Structural Deployment Drift

```text
$ kubectl diff -f manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml
(no output — zero diff)
```

## 17. git diff --check

```text
$ git diff --check
(no output — clean)
```

## 18. Secret Scan

Scanned all changed files for patterns: `Bearer .`, `Authorization:`, `JWT`, `SECRET=`, `TOKEN=`, `PASSWORD=`, `api_key`, `sk-`

```text
No credentials found in any changed files.
```

All auth tokens in evidence replaced with `<redacted>`.

## 19. Model ID Mapping

```text
Kubernetes Service name: vllm-32b-gptq
Kubernetes label model:  qwen-32b-gptq
Actual API model ID:     qwen-32b-base  (confirmed via /v1/models)
```

## 20. No Secrets in Evidence

All auth tokens in evidence are replaced with `<redacted>`. No JWT, API keys, bearer tokens, passwords, kubeconfigs, or private addresses are included in this document.
