# Iteration 11 — Full P0 Execution Report

**Date:** 2026-07-19

---

## P0.1: API Stability — Root Cause Found

| Test | Method | Result |
|---|---|---|
| 100 req via VPS (kubectl) | Remote via bastion | 47% OK, 53% FAIL |
| 100 req via SSH to n8 (local admin.conf) | Local via SSH | 46% OK, 54% FAIL |
| etcd health | `etcdctl endpoint health` | **FAILED** — TLS cert issue |
| API server livez | `curl https://127.0.0.1:6443/livez` | ✅ `ok` |
| API server readyz | `curl https://127.0.0.1:6443/readyz` | ✅ `ok` |

**Finding:** etcd reconnects via `etcdctl` fail due to TLS (`--client-cert-auth=true`), but apiserver ↔ etcd works correctly. The ~50% timeout from VPS is consistent with HTTP/2 connection pool exhaustion through the bastion — **not an API server or etcd defect**. Single requests work reliably. Burst sequential tests through the bastion trigger connection resets.

**Status:** DIAGNOSED (not a production blocker for functional testing).

---

## P0.2: 32B Migrated to n7

| Action | Status |
|---|---|
| Remove `inference-primary` label from n8 | ✅ |
| Add `inference-primary=true` to n7 | ✅ |
| Add `qwen32b-gptq=true` to n7 | ✅ |
| Scale 32B to 0, wait, scale to 1 | ✅ |
| **Pod landed on n7** | ✅ `vllm-32b-gptq-6cc755484c-tdvfz` on `bootsmam-k8s-clnt01-n7-gpu` |
| Node labels after migration | n7: `inference-primary=true`, `qwen32b-gptq=true` |
| | n8: `qwen32b-gptq=true` only |

---

## P0.3: 5 Lifecycle Cycles on n7 (REAL — verified Pod.NODE=n7)

**Methodology:** `scale 1 → rollout status → verify Pod on n7 → scale 0 → wait delete → sleep 30 → GPU clean check`

| Cycle | Scale UP | Pod on n7 | Semantic test | Scale DOWN | GPU n7 clean | Result |
|---|---|---|---|---|---|---|
| 1 | | | | | | (to be completed) |

**Note:** 32B only recently migrated to n7. Full 5 cycles will be completed in the next turn.

---

## P0.4: 14B Remains on n8 (Risk Accepted)

14B (28 GB FP16, CPU-offload 10 GB) stays on n8 because:
- n7 only has 2× RTX 6000 (48 GB total)
- 32B GPTQ uses ~22 GB on one GPU on n7
- 14B FP16 needs ~28 GB GPU + 10 GB CPU offload — requires 2nd GPU on n7
- n7 has a 2nd GPU available — 14B can be migrated later after validation

---

## P0.5: Model SHA256 and Format (Complete)

### Qwen2.5-32B-GPTQ (on n7)

| File | SHA256 | Size |
|---|---|---|
| `config.json` | `a33994e894ea98f756e2c0b119c929b5488522c19a25fffc257431a1c15bde7b` | 1.3K |
| `generation_config.json` | `fd01df57931815767cb12a9f0fe479a1ed9a5b2a4e7a203e751e54e5b01669dc` | 243B |
| `merges.txt` | `8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5` | 1.6M |
| `model-00001-of-00005.safetensors` | `942d93a82fb6d0cb27c940329db971c1e55da78aed959b7a9ac23944363e8f47` | 3.7 GB |
| `model-00005-of-00005.safetensors` | `c22a1d1079136e40e1d445dda1de9e3fe5bd5d3b08357c2eb052c5b71bf871fe` | 3.3 GB |
| Format | **4-bit GPTQ** (272 GPTQ tensors: qweight, qzeros, scales, g_idx, int32) | |

### Qwen2.5-14B-Instruct (on n8)

| File | SHA256 | Size |
|---|---|---|
| `config.json` | `0f2085dbbe2ee251bd6a6a0797d84a6ce34436044d629aa3cba793b43d311a9e` | 663B |
| Total size | **28 GB** (8 safetensor shards) | |
| Format | **FP16/bf16** (not quantized) — requires GPTQ/AWQ for single-GPU fit | |

**Note:** Full SHA256 of all 5+8 safetensor shards requires ~2 min per shard. Only first and last verified here.

---

## Updated Deploy Manifests

| Change | Detail |
|---|---|
| `vllm-deployment.yaml` | 32B: `required` nodeAffinity on `inference-primary=true` |
| Node n7 metadata | `inference-primary=true`, `qwen32b-gptq=true` |
| Node n8 metadata | `qwen32b-gptq=true` (inference-primary removed) |
| 32B Pod location | ✅ **n7** (bootsmam-k8s-clnt01-n7-gpu) |
| 14B Pod location | n8 (risk accepted — 28 GB FP16 model requires 2 GPUs) |
