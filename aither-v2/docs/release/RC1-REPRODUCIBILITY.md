# Aither MVP RC1 — Reproducibility Guide

## Purpose

This document describes how to reproduce the Aither MVP RC1 deployment
from scratch on a clean Kubernetes cluster. Following these steps in order
must produce an identical working system.

---

## 1. Environment Requirements

### Hardware

- **2 GPU nodes** with NVIDIA GPUs (tested on 2× NVIDIA A100 80GB)
- **Minimum RAM:** 64 GB per node
- **Disk:** 200 GB+ SSD per node (for model storage, container images)

### Software Versions (tested)

| Component | Version |
|---|---|
| Kubernetes | v1.33.5 |
| kubelet | v1.33.5 |
| containerd | 2.2.1 |
| CNI | Flannel |
| OS | Astra Linux (kernel 6.6.28-1-generic) |
| NVIDIA Driver | 550.x (via GPU Operator) |
| Container Runtime | containerd://2.2.1 |

### Required CLI Tools

- `kubectl` (matching cluster version)
- `curl`
- `base64`
- `bash` (≥ 4.0)
- `grep`, `awk`, `sed`

---

## 2. Prerequisites

### 2.1 Cluster Access

```bash
# Verify cluster access
kubectl get nodes
kubectl get pods -A
```

Expected output: 2 nodes ready, core system pods running.

### 2.2 GPU Operator

The cluster must have NVIDIA GPU Operator installed to enable GPU
acceleration for vLLM pods.

---

## 3. Deployment Sequence

### Step 1 — Clone Repository

```bash
git clone https://github.com/dedvmedved-dot/aither-project.git
cd aither-project
git checkout aither-v2
```

### Step 2 — Create Namespace

```bash
kubectl create namespace aither-inference
```

### Step 3 — Apply Manifests

Apply in the following order:

```bash
# vLLM 32B GPTQ model service
kubectl apply -f manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml

# BFF API
kubectl apply -f manifests/mvp-roadmap/05-bff/bff-mvp.yaml

# Portal
kubectl apply -f manifests/mvp-roadmap/07-portal/portal-mvp.yaml
```

### Step 4 — Create Secrets

```bash
# Gateway auth token (shared secret between BFF and Gateway)
kubectl create secret generic aither-bff-auth \
  -n aither-inference \
  --from-literal=BFF_32B_GATEWAY_AUTH_TOKEN='<your-secret>'

# vLLM API key (if required)
kubectl create secret generic vllm-api-key \
  -n aither-inference \
  --from-literal=api-key='<your-api-key>'
```

### Step 5 — Verify Pods

```bash
kubectl get pods -n aither-inference -o wide
```

Expected:
- `vllm-32b-gptq-*` — 1/1 Running on GPU node
- `nginx-gateway-32b-*` — 2/2 Running (one per node)
- `aither-bff-*` — 1/1 Running
- `aither-portal-*` — 1/1 Running

### Step 6 — Verify Gateway Connectivity

```bash
# Health check
kubectl exec -n aither-inference deployment/nginx-gateway-32b -- \
  curl -s http://localhost:8000/healthz

# Expected: 200 OK ("ok")
```

### Step 7 — Run Diagnostics

```bash
bash scripts/check-gateway-32b.sh
```

Expected: `Passed: 33  Failed: 0  Warnings: 0`

### Step 8 — Run Authenticated E2E Test

```bash
export GATEWAY_TOKEN='<token-from-secret>'
bash scripts/test-gateway-32b-e2e.sh
```

Expected: All tests PASS.

### Step 9 — Validate Evidence

Key validation points:
- Gateway `/health` returns 200
- Gateway `/v1/models` returns model `qwen-32b-base`
- Gateway `/v1/completions` with valid token returns HTTP 200 and non-empty completion
- Gateway `/v1/completions` without token returns HTTP 401
- Gateway blocks `/v1/chat/completions` with 422
- Response model ID matches requested model ID
- Pods on both nodes are Running + Ready=True

### Step 10 — Check DNS

```bash
# Create a test pod on each node with dnsPolicy: ClusterFirst
kubectl run dns-test --image=busybox:1.36 -- sleep 30
kubectl exec dns-test -- nslookup kubernetes.default.svc.cluster.local
```

Expected: resolves to `10.96.0.1` via `10.96.0.1` (CoreDNS).

---

## 4. Expected Outcomes

| Check | Expected |
|---|---|
| Namespace exists | `aither-inference` |
| Gateway pods | 2/2 Running |
| vLLM pod | 1/1 Running |
| BFF pod | 1/1 Running |
| Portal pod | 1/1 Running |
| Gateway healthz | 200 |
| Gateway upstream health | 200 |
| Authenticated completion | HTTP 200, non-empty |
| Auth required | 401 without token |
| Model consistency | Response model == requested model |
| dnsPolicy | ClusterFirst |
| Diagnostic script | 33 PASS, exit 0 |
| E2E test | All PASS |

---

## 5. Known Limitations

- CoreDNS runs on control-plane node only (n8); both gateway nodes resolve
  via ClusterIP `10.96.0.10` — no impact on functionality.
- Chat completions are blocked at Gateway level (model does not support chat).
- Rate limiting is configured in BFF and Portal layers.
- All secrets must be supplied out-of-band (no default credentials in repo).
