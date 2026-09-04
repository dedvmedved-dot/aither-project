# Aither — R8 Candidate C-C1 Dtype / Quantization compatibility

TASK: AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-C-C1-BACKEND-COMPATIBILITY-CLOSURE
CANDIDATE: moonshotai/Kimi-Linear-48B-A3B-Instruct (rev e1df551a)

## Dtype

- Model config dtype = bfloat16 (checkpoint is BF16).
- Turing (sm75) has NO BF16 tensor cores (BF16 tensor cores start at Ampere sm80); BF16 on sm75 is
  emulated (functional but slower), not tensor-core-accelerated.
- The FLA KDA Triton ops are dtype-generic (use `dtype.element_ty`; `out_dtype`/`residual_dtype` default
  to input dtype). No `assert dtype == bfloat16` found.
- Therefore the KDA kernels accept both FP16 and BF16 at the Triton level.

- BF16_NATIVE_SM75 = NO (no BF16 tensor cores on Turing; emulated path)
- KDA_FP16_SUPPORTED = YES (dtype-generic Triton kernels)
- FP16_MODEL_OVERRIDE_SUPPORTED = UNPROVEN (vLLM `--dtype half` plausibly forces FP16 activations/weights,
  but the checkpoint is BF16 and this has not been executed here)
- ACTIVATION_DTYPE_REQUIRED = NONE_PROVEN (no hardcoded dtype assertion in Candidate C path)

No hard dtype blocker is proven. BF16 (emulated) is the native checkpoint dtype; FP16 is kernel-supported
but requires a vLLM dtype override that remains runtime-unproven.

## Quantization / representation

~48B BF16 (~96 GB) does not fit 45 GiB VRAM. A lower-bit representation is required for any later benchmark.
Full weights were NOT downloaded.

| Representation | Repo (example) | Quant | ~size | publisher | vLLM Kimi-Linear support | sm75 quant-kernel |
|---|---|---|---|---|---|---|
| AWQ 4-bit | cyankiwi/Kimi-Linear-48B-A3B-Instruct-AWQ-4bit | AWQ | ~24 GB | third-party | plausible | unproven |
| GPTQ Int4 | reinforce20001/...-GPTQ-Int4 | GPTQ | ~24 GB | third-party | plausible | unproven |
| GGUF Q4 | bartowski/moonshotai_...-GGUF | Q4_K_M | ~18-24 GB | third-party | n/a (llama.cpp) | unproven |
| FP8 | nm-testing/...-FP8-DYNAMIC | FP8 | ~48 GB | third-party | plausible | unproven (FP8 on sm75 is emulated) |
| nvfp4 | Firworks/...-nvfp4 | nvfp4 | ~24 GB | third-party | plausible | unproven (Blackwell-oriented) |

SELECTED_PLAUSIBLE_REPRESENTATION = AWQ 4-bit (or GGUF Q4_K_M) — ~24 GB weight residency, plausible 64K headroom.

A Hugging Face file existing does not prove runtime compatibility; these are unproven until executed.
