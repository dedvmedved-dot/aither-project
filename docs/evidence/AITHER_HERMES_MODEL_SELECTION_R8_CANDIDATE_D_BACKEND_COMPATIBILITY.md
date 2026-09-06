# Aither — R8 Candidate D Backend Compatibility

TASK: AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-D-GPT-OSS-20B
HARDWARE: 2x NVIDIA RTX 6000 24GiB / Turing / sm75

## vLLM 0.27.1

- image digest: sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967
- GptOssForCausalLM registry support: present (gpt_oss model_type).
- MXFP4 quantization: `vllm/model_executor/layers/quantization/mxfp4.py`
  `get_min_capability() -> 80` (requires Ampere sm80+).
- compressed-tensors w4a4 mxfp4 scheme: "On SM100+ with FlashInfer: true W4A4; otherwise W4A16 via Marlin".

VLLM_GPT_OSS_ARCH_SUPPORT = PASS (architecture recognized)
VLLM_MXFP4_SM75 = FAIL (official MXFP4 quantization requires sm80+)
VLLM_RUNTIME_PATH = NOT_VIABLE (official native MXFP4 cannot run on sm75 via vLLM 0.27.1)

This is a backend/hardware limitation, NOT a Candidate D model-quality rejection.

## llama.cpp (project build)

- build 10666 (commit 4e97ac86e), runtime image digest sha256:150b59966fb5b2cb1a8fa9d226267c56ebd22c520c7b3640331cde87f3c4fb01
- binary contains "gpt-oss" arch token (grep -a on libllama.so -> 1 match) and "mxfp4" (1 match).
- qwen2 arch token present (167 matches) as a positive-control for the grep method.

LLAMACPP_CURRENT_BUILD_GPT_OSS = PASS (gpt-oss architecture token present)
LLAMACPP_NATIVE_MXFP4_SM75 = UNPROVEN (mxfp4 token present; native MXFP4 GGUF execution on sm75 not yet runtime-proven)
LLAMACPP_TOOL_PROTOCOL = UNPROVEN (to be established in Phase C preflight)

## Backend selection

SELECTED_BACKEND = llama.cpp (build 10666, existing pinned project backend)
Reason: vLLM official MXFP4 requires sm80+; llama.cpp build 10666 has gpt-oss arch support and is the existing pinned project backend (no upgrade required).

No backend replacement/upgrade required.
