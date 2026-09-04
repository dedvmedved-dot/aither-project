# Aither — R8 Candidate C-C1 Backend Compatibility

TASK: AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-C-C1-BACKEND-COMPATIBILITY-CLOSURE
CANDIDATE: moonshotai/Kimi-Linear-48B-A3B-Instruct (rev e1df551a447157d4658b573f9a695d57658590e9)
HARDWARE: 2× NVIDIA RTX 6000 (Turing sm75), 24 GiB each

## Correction of previous claim

Previous claim: HARDWARE_BACKEND_INCOMPATIBLE_FOR_HERMES_64K (FlashKDA SM90 restriction).
This claim was REJECTED: it conflated the Kimi-K3 full-rank-gate path with the standalone Kimi-Linear path.

## vLLM 0.27.1

- registry maps KimiLinearForCausalLM -> vllm.models.kimi_k3.
- `use_full_rank_gate` absent in exact config -> False.
- model.py:796-804 selects `KimiLinearGatedDeltaNetAttention` (shared GDN base), NOT `KimiK3DeltaAttention`.
- Shared Kimi GDN forces Triton prefill (`assert backend == "triton"`); decode is Triton fused_recurrent.
- FlashKDA SM90 gate is inside KimiK3DeltaAttention only; NOT reached by Candidate C.

VLLM_COMPATIBILITY = PASS (exact path uses compute-capability-agnostic Triton; no sm75 gate).

## SM75 compatibility

- The Triton KDA ops contain no `is_device_capability`/sm75/sm80/sm90 checks.
- No mandatory op in the Candidate C path requires an unsupported ISA without fallback.
- Optional optimized paths (FlashKDA/FlashInfer GDN) target SM90/SM100/SM120, but they are NOT the
  Candidate C path and are not mandatory.

SM75_COMPATIBILITY = PASS (static; runtime untested).

## llama.cpp

- Project build 10666 (commit 4e97ac86e): no Kimi Linear architecture (no kimi/kda/linear_attn strings).
- Upstream (latest): not verifiable from this environment (no web access configured).

LLAMACPP_PROJECT_BUILD = FAIL (current build lacks support)
LLAMACPP_UPSTREAM = UNPROVEN

## Classification

- No proven sm75 blocker in the exact Candidate C code path.
- TP2 statically valid (num_heads 32 % 2 == 0).
- At least one plausible low-bit representation exists (AWQ-4bit / GPTQ-Int4 / GGUF Q4).

BACKEND_COMPATIBILITY_C_C1 = PASS_STATIC
