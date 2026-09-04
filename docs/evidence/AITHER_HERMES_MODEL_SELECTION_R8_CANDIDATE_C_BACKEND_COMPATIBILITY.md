# Aither — R8 Candidate C Backend / Kernel Compatibility

TASK: `AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-C`
CANDIDATE: Kimi-Linear-48B-A3B-Instruct
HARDWARE: 2× NVIDIA RTX 6000 (Turing, sm75), 24 GiB each

## A. vLLM

- vLLM 0.27.1 (image `vllm/vllm-openai@sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967`) contains `KimiLinearForCausalLM` in its registry, mapped to `vllm.models.kimi_k3`.
- The `vllm/models/kimi_k3/nvidia` implementation contains explicit compute-capability gates:
  - `kda.py:154`: "SM90 is architecture-specific; SM10x and SM12x use family binaries."
  - `kda.py:169-172`: `capability.major in (9, 10, 12)` (requires SM90 / SM10x / SM12x).
  - `kda.py:238`: "FlashKDA requires CUDA SM90/SM10x/SM12x, bfloat16, ..."
  - `chunk_intra.py:535`: `has_device_capability(80)` (sm80+).
  - `low_latency_gemm.py:324`: `is_device_capability((10, 3))` (SM103).
  - `latent_moe_tail.py:114`: `get_device_capability()[0] != 10` (SM10x).
- **The KDA (Kernel/Delta Attention) kernel requires SM90/SM10x/SM12x (Hopper/Blackwell/Rubin).**
- **Turing (sm75) is NOT a supported compute capability.**
- BACKEND_COMPATIBILITY_VLLM = FAIL (sm75 unsupported by required KDA kernels).

## B. llama.cpp / GGUF

- llama.cpp `server-cuda` build 10666 (0.3.0-dev, commit 4e97ac86e) was inspected:
  `strings /app/libllama.so` contains NO "kimi", "kda", "linear_attn", or "delta attn" tokens.
- GGUF mirrors exist (bartowski/moonshotai_Kimi-Linear-48B-A3B-Instruct-GGUF), but the inspected
  llama.cpp build has no Kimi Linear architecture implementation.
- BACKEND_COMPATIBILITY_LLAMACPP = FAIL (architecture not supported in available build).

## C. Memory (for reference — backend already incompatible)

- 48B MoE (256 experts): BF16 ≈ 96 GB (no), FP8 ≈ 48 GB (no, exceeds 45 GB), Q4/AWQ ≈ 24 GB (fits, tight).
- Even a fitting Q4 representation does not resolve the KDA kernel sm75 incompatibility.

## Verdict

- BACKEND_COMPATIBILITY_VLLM = FAIL (KDA requires SM90/SM10x/SM12x)
- BACKEND_COMPATIBILITY_LLAMACPP = FAIL (no architecture support)
- SM75_COMPATIBILITY = FAIL
- BACKEND_SELECTED = NONE (no backend is architecture-correct AND sm75-compatible AND 64K-capable)

RESULT = CANDIDATE_C_BACKEND_INCOMPATIBLE
