# Aither — R8 Candidate C-C2-R2 KDA Source Analysis

TASK: AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-C-C2-R2-LOW-SMEM-KDA-KERNEL-COMPATIBILITY-CLOSURE

## Exact failing call chain (from C-C2-R1 runtime)

KimiLinearGatedDeltaNetAttention (kimi_gdn_linear_attn.py) -> kda.py `chunk_gated_delta_rule_fwd_h`
(state) + `chunk_gla_fwd_o_gk` (output).

Two KDA-path Triton kernels are autotuned:

1. `chunk_gated_delta_rule_fwd_kernel_h_blockdim64` (chunk_delta_h.py)
   - autotune: BV [32,64] x num_warps [2,4] x num_stages [2,3,4]
   - default selected BV=32/W=4/S=2 (launched OK in C-C2-R1)

2. `chunk_gla_fwd_kernel_o` (kda.py)
   - autotune: BK [32,64] x BV [64,128] x num_warps [2,4,8] x num_stages [2,3,4]
   - default selected BV=64 -> OutOfResources (shared memory 102400 > 65536)

## Root cause of C-C2-R1 failure

`chunk_gla_fwd_kernel_o` default autotune selects BV=64 with num_stages>=2, requiring 100 KiB shared
memory; Turing (sm75) provides 64 KiB. The vendored `_CHUNK_DELTA_H_NUM_STAGES` and the `chunk_gla`
autotune both exclude num_stages=1.

## Candidate C exact dimensions

- H=32, Hg=32, K=128 (head_dim), V=128, BT=64 (FLA_CHUNK_SIZE), dtype=FP16 (activations), gate=FP32.

## Vendored FLA vs upstream low-SMEM policy

- vLLM 0.27.1 chunk_gla autotune: BV in [64,128], num_stages in [2,3,4] (no low-SMEM stage).
- Upstream FLA (per Architect audit) narrows the search on lower-SMEM GPUs (num_stages=1/2, BV=32).
- The correction is a config-space restriction (num_stages=1, BV=64) only; no math change.
