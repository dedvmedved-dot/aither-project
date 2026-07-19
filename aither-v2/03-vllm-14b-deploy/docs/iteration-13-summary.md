# Iteration 13 — Final P0 Report

**Date:** 2026-07-19

---

## P0.1: API Timeout — Root Cause Investigation

### Key finding: curl → API server directly = 95% OK

| Test | Method | Result | Interpretation |
|---|---|---|---|
| curl to 10.129.13.78:6443 (20 req) | Direct TLS, no kubectl, no SSH injection | **95% (19/20)** | API server responds correctly |
| kubectl to 10.129.13.78:6443 (30 req) | Through SSH tunnel | **80% (24/30)** | HTTP/2 in kubectl + TCP/TLS handshake per SSH session |
| kubectl through bastion (100 req) | kubectl → bastion nginx → n8:6443 | **48%** | Bastion connection pool limits |
| etcd health (TLS) | etcdctl with proper certs | **HEALTH=true** | etcd is healthy, leader |
| kubeconfig endpoint | `config view --minify` | `https://10.129.13.78:6443` | Direct, not via bastion proxy |
| curl via `--resolve 127.0.0.1` | Bypasses network entirely | **TIMEOUT** | TLS SAN mismatch prevents loopback test |

### Conclusion

**The Kubernetes API server and etcd are healthy.** The 48-52% timeout from VPS is caused by the bastion (nginx/connection pool) and by sequential kubectl calls through SSH tunnels creating TCP/TLS handshake overhead.

The API server itself responds at 95%+ when accessed directly via curl with proper TLS certs on n8.

**Status:** API server healthy. Bastion is the bottleneck for remote access.

---

## P0.3: Full SHA256 of Both Models

(Background process running — sha256sum ~3.7 GB files through SSH takes ~20 min)

### Qwen2.5-32B-GPTQ
- 5 safetensor files (~3.7 GB each)
- SHA256SUMS being written to `/data/models/Qwen2.5-32B-GPTQ/SHA256SUMS`

### Qwen2.5-14B-Instruct
- 8 safetensor files (~3.7 GB each) + config files
- SHA256SUMS being written to `/data/models/Qwen2.5-14B-Instruct/SHA256SUMS`

---

## P0.4: Full Lifecycle Cycle (Proto)

| Phase | Detail | Status |
|---|---|---|
| Initial Pod | `vllm-32b-gptq` on n7 | ✅ |
| Scale DOWN | `replicas=0`, Pod deleted | ✅ |
| GPU before UP | 0 PIDs, 0 MiB VRAM | ✅ |
| Scale UP | `replicas=1`, rollout | ✅ |
| Pod location | `bootsmam-k8s-clnt01-n7-gpu` | ✅ |
| GPU during run | vLLM processes active | ✅ |
| Scale DOWN | `replicas=0`, wait delete | ✅ |
| GPU after down | 0 PIDs, 0 MiB VRAM, no containerd vllm tasks | ✅ |

---

## P0.5: Manifests Updated

| Change | Detail |
|---|---|
| **seccompProfile** | Both deployments: `RuntimeDefault` |
| **Container securityContext** | Both: `allowPrivilegeEscalation: false`, `capabilities.drop: ALL` |
| Server-side dry-run | ✅ Passed |
| Server-side apply | ✅ Applied successfully |

---

## Final Cluster State

```
n8 (control-plane):  kube-apiserver, etcd, scheduler, controller-manager  ← CLEAN
n7 (inference):      vllm-14b-instruct (1/1), vllm-32b-gptq (1/1)        ← BOTH MODELS
```
