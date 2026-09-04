# Aither — R8 Candidate C Report

TASK: `AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-C`
CANDIDATE: C
MODEL: `moonshotai/Kimi-Linear-48B-A3B-Instruct`
MODEL REVISION: `e1df551a447157d4658b573f9a695d57658590e9`
ARCHITECTURE: KimiLinearForCausalLM (MoE + Delta Attention/KDA + MLA + short-conv)
TOTAL PARAMETERS: ~48B (256 experts)
ACTIVE PARAMETERS: ~3B (8/token)
NATIVE CONTEXT: 1M (1048576)

## Verdict

- PROVENANCE = PASS (model verified)
- BACKEND_COMPATIBILITY = FAIL
- SM75_COMPATIBILITY = FAIL
- TP2_COMPATIBILITY = NOT_REACHED (blocked earlier)

## Backend finding (decisive)

The Kimi Linear KDA (Kernel/Delta Attention) kernel requires CUDA SM90/SM10x/SM12x
(Hopper/Blackwell/Rubin). vLLM 0.27.1's `kimi_k3` implementation explicitly gates on
`capability.major in (9, 10, 12)` and "FlashKDA requires CUDA SM90/SM10x/SM12x".

The available LAB hardware is 2× NVIDIA RTX 6000 = Turing = sm75, which is NOT supported.

llama.cpp build 10666 (server-cuda) contains no Kimi Linear architecture implementation.

No backend is architecture-correct AND sm75-compatible AND 64K-capable.

## Status

RESULT = CANDIDATE_C_BACKEND_INCOMPATIBLE

CANDIDATE STATUS = **HARDWARE_BACKEND_INCOMPATIBLE_FOR_HERMES_64K**

This is a hardware/backend incompatibility, NOT a model-quality failure. No model weights were
downloaded, no maintenance window was opened, and production Qwen3.8 remained untouched.

Final decision belongs to ChatGPT after independent GitHub Connector audit.
