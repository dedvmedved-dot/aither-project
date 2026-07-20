# nginx-gateway-32b Root Cause Analysis

## Symptom

One of two nginx-gateway-32b replicas was in **CrashLoopBackOff** with **242 restarts** over 20 hours. The other replica was healthy and serving traffic. No user-facing impact because one replica remained Running.

## Root Cause

**Nginx uses hostname in proxy_pass, but one Kubernetes node (n7) has no ClusterDNS.**

1. **nginx.conf** (ConfigMap `nginx-gateway-32b`) contains:
   ```
   proxy_pass http://vllm-32b-gptq.aither-inference.svc:8000;
   ```

2. When nginx starts, it resolves the upstream hostname. On a node with working DNS (n8), this succeeds because CoreDNS pods are available.

3. On **node n7** (`bootsmam-k8s-clnt01-n7-gpu`), kubelet reports:
   ```
   MissingClusterDNS — kubelet does not have ClusterDNS IP configured.
   ```
   Both CoreDNS pods are scheduled only on n8:
   ```
   coredns-674b8bbfcf-2h5vp   n8
   coredns-674b8bbfcf-b2w7k   n8
   ```

4. nginx falls back to `/etc/resolv.conf` (Default policy), which cannot resolve `vllm-32b-gptq.aither-inference.svc`.
   Result: nginx exits with `host not found in upstream`.

5. The healthy replica runs on n8, where CoreDNS is available.

## Why This Happened Only to Gateway

vLLM 14B and 32B pods also show `MissingClusterDNS` warning but use `wait-for-it.sh` or have retry logic. nginx exits immediately on DNS resolution failure at startup with no retry.

## Remediation

Replace hostname with **ClusterIP** (`10.99.3.103`) in nginx.conf. Service ClusterIP is stable, does not change, and does not require DNS resolution.

**Changes made:**
- `proxy_pass http://vllm-32b-gptq.aither-inference.svc:8000` → `proxy_pass http://10.99.3.103:8000`
- Applied in all 3 locations: `/v1/completions`, `/health`, `/v1/models`
- Applied via `kubectl patch configmap nginx-gateway-32b` (runtime operation, NOT committed)

## Long-term Fix (out of scope)

Deploy CoreDNS on node n7 to provide ClusterDNS for all pods on that node. This would fix `MissingClusterDNS` for all pods (vLLM 14B, vLLM 32B, gateway) and allow using hostname-based proxy_pass.

## Verification

| Check | Result |
|---|---|
| New pod on n7 created | ✅ `nginx-gateway-32b-5d447469b9-28kng` |
| Status: 1/1 Running | ✅ |
| Restart count: 0 | ✅ |
| 32B completion regression | ✅ HTTP 200 |
| 32B chat adapter regression | ✅ HTTP 200 |

## External Audit Note

ChatGPT external audit accepted the immediate remediation as MVP-compatible because:
- nginx-gateway-32b returned to 2/2 Running and Ready.
- 32B completion and 32B chat adapter still returned HTTP 200.
- No BFF/Portal/vLLM/GPU/TP/Redis/OAuth/Monitoring changes were made.

However, the remediation is tactical, not production-ready:
- MissingClusterDNS on n7 remains unresolved.
- Gateway runtime ConfigMap differs from GitHub source-of-truth.
- Gateway uses hardcoded ClusterIP 10.99.3.103.
- Long-term fix requires infrastructure stabilization and repo-backed manifest alignment.
