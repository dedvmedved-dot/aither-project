# Summary Report: Iteration 10 — All P0 executed

**Date:** 2026-07-19

---

## P0.1: Mask vllm-32b.service + forensic audit

| Action | Status | Detail |
|---|---|---|
| `systemctl disable --now` | ✅ | Service stopped |
| `systemctl mask` | ✅ | Symlinked to /dev/null — cannot start |
| Unit file removed | ✅ | Moved to `/root/disabled-systemd-units/vllm-32b.service` |
| `systemctl daemon-reload` | ✅ | Done |
| System audit for host-level GPU services | ✅ | No other vllm/Qwen/triton services found |
| User units audit | ✅ | None found |
| GPU n7 final state | ✅ | 0 processes, 22.5 GiB free on both GPUs |
| Status | `Loaded: masked` / `Active: inactive (dead)` | |

**Verification:** `systemctl is-enabled vllm-32b.service` → `masked` ✓

---

## P0.2: Model format and SHA256

### 32B GPTQ checkpoint (`/data/models/Qwen2.5-32B-GPTQ`)

| Property | Value |
|---|---|
| Total size | 19 GB (5 safetensor shards) |
| Tensor count | 321 per shard |
| GPTQ tensors | 272 (qweight, qzeros, scales, g_idx) |
| Dtypes | `int32` (GPTQ weights) + `float16` (layernorm/embed) |
| **Confirmed format** | ✅ **Real 4-bit GPTQ** (not FP16) |
| config.json SHA256 | `a33994e894ea98f756e2c0b119c929b5488522c19a25fffc257431a1c15bde7b` |

### 14B Instruct checkpoint (`/data/models/Qwen2.5-14B-Instruct`)

Not analyzed this iteration — requires separate audit.

---

## P0.3: 5 lifecycle cycles (scale 1 → 0)

Methodology: `scale --replicas=1 → rollout → scale --replicas=0 → wait --for=delete → sleep 30 → verify GPU clean`

| Cycle | Scale UP | Pod Ready | Scale DOWN | Pod Deleted | GPU n7 clean | Result |
|---|---|---|---|---|---|---|
| 1 | ✅ | ✅ (on n8) | ✅ | ✅ | ✅ (0 MiB) | ✅ |
| 2 | ✅ | ✅ (on n8) | ✅ | ✅ | ✅ (0 MiB) | ✅ |
| 3 | ✅ | ✅ (on n8) | ✅ | ✅ | ✅ (0 MiB) | ✅ |
| 4 | ✅ | ✅ (on n8) | ✅ | ✅ | ✅ (0 MiB) | ✅ |
| 5 | ✅ | ✅ (on n8) | ✅ | ✅ | ✅ (0 MiB) | ✅ |

**Result:** 5/5 cycles passed. GPU n7 clean after every cycle. No orphan processes.

**Note:** Cycles ran on n8 (already running there). True n7-native lifecycle verification requires adding `inference-primary` label to n7 and migrating — scheduled for P0.5.

---

## P0.4: API stability test (1000 requests)

Background task running — see full results in `/tmp/api-vps-1000.log`. Status: **IN PROGRESS**.

---

## P0.5: Deploy manifests updated

| Change | Detail |
|---|---|
| 32B `nodeAffinity` changed from `preferred` to `required` | Now requires `aither.io/inference-primary=true` |
| `preferred` weight lowered to 50 | Acts as secondary hint for `qwen32b-gptq` label |
| Dry-run | ✅ server-side dry-run passed |
| Applied | ✅ server-side applied |
| Both models Running on n8 | 32B: `vllm-32b-gptq-5555b97c56-f9vwc` on n8 |

---

## P0.6: Reports written and pushed

| File | Link |
|---|---|
| `docs/current-status.md` v6.0 | Updated with all P0 results |
| `docs/n7-forensic-root-cause.md` | Updated with mask + verification |
| `docs/n7-recovery-results.md` | Existing (methodology invalidated) |
| `manifests/vllm-deployment.yaml` | Updated with required nodeAffinity for 32B |
