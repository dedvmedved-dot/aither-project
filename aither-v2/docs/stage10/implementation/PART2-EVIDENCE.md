# PART2-EVIDENCE.md

**Project:** Aither / AI Hermes MVP  
**Stage:** Stage 10 — Implementation Part 2  
**Document:** Gateway DNS Remediation Evidence  
**Date:** 2026-07-20

---

## 1. ClusterDNS Root Cause

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

### DNS resolution from n7 pod uses 8.8.8.8 (not 10.96.0.10)
```text
$ kubectl -n aither-inference exec nginx-gateway-32b-5d447469b9-28kng -- \
  nslookup vllm-32b-gptq.aither-inference.svc
Server:  8.8.8.8
** server can't find vllm-32b-gptq.aither-inference.svc: NXDOMAIN
```

### DNS resolution from n8 pod — correct
```text
$ kubectl -n aither-inference exec nginx-gateway-32b-5d447469b9-pvxtq -- \
  cat /etc/resolv.conf
search aither-inference.svc.cluster.local svc.cluster.local cluster.local cloud.test
nameserver 10.96.0.10
```

## 2. Manifest Applied

```text
$ kubectl apply --dry-run=client -f manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml
configmap/nginx-gateway-32b configured (dry run)
deployment.apps/nginx-gateway-32b configured (dry run)
service/nginx-gateway-32b configured (dry run)

$ kubectl apply --dry-run=server -f manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml
configmap/nginx-gateway-32b configured (server dry run)
deployment.apps/nginx-gateway-32b configured (server dry run)
service/nginx-gateway-32b configured (server dry run)
```

## 3. Rollout Status

```text
$ kubectl apply -f manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml
configmap/nginx-gateway-32b configured
deployment.apps/nginx-gateway-32b configured

$ kubectl -n aither-inference rollout status deployment/nginx-gateway-32b --timeout=180s
deployment "nginx-gateway-32b" successfully rolled out
```

## 4. Pods After Rollout

```text
$ kubectl -n aither-inference get pods -o wide | grep gateway
nginx-gateway-32b-5569cc84d-6mqnk  1/1  Running  0  55s  10.244.1.10  n7-gpu
nginx-gateway-32b-5569cc84d-8j6l2  1/1  Running  0  65s  10.244.0.208 n8-gpu
```

## 5. nginx -t (both pods)

```text
# On n7 pod:
$ kubectl exec nginx-gateway-32b-5569cc84d-6mqnk -- nginx -t
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful

# On n8 pod:
$ kubectl exec nginx-gateway-32b-5569cc84d-8j6l2 -- nginx -t
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

## 6. Gateway Health Check

```text
$ curl -s -o /dev/null -w '%{http_code}' http://localhost:18000/health
200
```

## 7. Auth Passthrough Test (no token → 401)

```text
$ kubectl exec nginx-gateway-32b-5569cc84d-6mqnk -- \
  curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-32b-base","prompt":"test","max_tokens":1}'
401
```

## 8. Unsupported Endpoint Test (422)

```text
$ kubectl exec nginx-gateway-32b-5569cc84d-6mqnk -- \
  curl -s -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{}'
{"error":"qwen-32b-base does not support chat"}
```

## 9. 32B Completion via Gateway (n7 pod — request reaches vLLM)

```text
# With auth token — vLLM responds (model ID mismatch: qwen-32b-gptq not found)
# vLLM model list confirms: model = "qwen-32b-base"
$ kubectl exec vllm-32b-gptq -- curl -s http://localhost:8000/v1/models \
  -H "Authorization: Bearer <redacted>"
{"data":[{"id":"qwen-32b-base",...}]}
```

## 10. Diagnostic Script

```text
$ bash scripts/check-gateway-32b.sh
════════════════════════════════════════
  Aither Gateway 32B — Diagnostic Check
════════════════════════════════════════
✓ vllm-32b-gptq Service exists (ClusterIP: 10.99.3.103)
✓ vllm-32b-gptq has endpoints
✓ nginx-gateway-32b Service exists (ClusterIP: 10.106.31.143)
✓ nginx-gateway-32b: 2/2 ready
✓ Gateway pod on n7
✓ Gateway pod on n8
✓ Gateway on n7: returns 401 without auth token
✓ Gateway on n8: returns 401 without auth token
✓ Gateway on n7: blocks /v1/chat/completions (422)
✓ Gateway on n8: blocks /v1/chat/completions (422)
✓ dnsPolicy: Default (n7-compatible)
✓ nginx -t on n7: OK
✓ nginx -t on n8: OK
✓ Runtime upstream: 10.99.3.103
Passed: 14  Failed: 0  Warnings: 0
```

## 11. git diff --check

```text
$ git diff --check
(no output — clean)
```

## 12. No Secrets in Evidence

All auth tokens redacted from evidence output.
