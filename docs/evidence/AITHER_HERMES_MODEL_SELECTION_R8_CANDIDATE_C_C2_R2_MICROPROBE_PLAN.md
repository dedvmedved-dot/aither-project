# Aither — R8 Candidate C-C2-R2 KDA Microprobe Plan

TASK: AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-C-C2-R2-LOW-SMEM-KDA-KERNEL-COMPATIBILITY-CLOSURE

- PURPOSE: prove whether the exact vendored vLLM 0.27.1 KDA Triton kernels execute on sm75 with a
  low-SMEM config (<=65536 bytes shared memory), without loading the 48B model.
- EXACT_IMPORT_PATHS: vllm.third_party.flash_linear_attention.ops.chunk_delta_h
  (chunk_gated_delta_rule_fwd_kernel_h_blockdim64); vllm.third_party.flash_linear_attention.ops.kda
  (chunk_gla_fwd_kernel_o, chunk_gla_fwd_o_gk).
- EXACT_KERNEL: as above (raw JITFunction, autotune config forced via KERNEL.configs).
- CANDIDATE_DIMENSIONS: H=32, Hg=32, K=128, V=128, BT=64; FP16 activations, FP32 gate/decay.
- CONFIG_MATRIX: state BV=32 x W[2,4] x S[1,2]; output BK=32 x BV=64 x W[2,4] x S[1,2].
- EXPECTED_SHARED_MEMORY_LIMIT: 65536 bytes (sm75).
- EXPECTED_PASS_CONDITION: compile + launch without OutOfResources, finite output.
- EXPECTED_HARD_FAIL_CONDITION: OutOfResources (shared memory >65536) for ALL configs.
- NUMERICAL_REFERENCE: cross-config consistency (parallelization configs must agree exactly); plus
  finite-output gate.
- REQUIRES_EXCLUSIVE_N7=YES (GPU occupied by Qwen3.8; brief scale-down required for the probe).
- EXPECTED_GPU_MEMORY: ~10 MB tensors + Triton CUDA context.

Note: the probe runs the exact vendored kernels (not a reimplementation). Numerical correctness is
established via cross-config consistency (state kernel 0 error) and finite-output gate.
