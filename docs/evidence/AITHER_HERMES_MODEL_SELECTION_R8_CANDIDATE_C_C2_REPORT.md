# Aither — R8 Candidate C-C2 Runtime Feasibility and Preflight — Report

TASK: AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-C-C2-RUNTIME-FEASIBILITY-AND-PREFLIGHT
BASELINE: 80f441e77fecaccbf245d0841e053e33556c5d05
CANDIDATE: moonshotai/Kimi-Linear-48B-A3B-Instruct
BASE MODEL REVISION: e1df551a447157d4658b573f9a695d57658590e9

REPRESENTATION: cyankiwi/Kimi-Linear-48B-A3B-Instruct-AWQ-4bit
REPRESENTATION REPOSITORY: cyankiwi/Kimi-Linear-48B-A3B-Instruct-AWQ-4bit
REPRESENTATION REVISION: 5d029d1844aa64ec302e14466be7d0353c6e697f
REPRESENTATION QUANTIZATION: compressed-tensors int4 (group_size 32, symmetric, weight-only)
REPRESENTATION WEIGHT BYTES: ~30.5 GB (7 safetensors)
REPRESENTATION_PROVENANCE: PASS (static)

BACKEND: vLLM
BACKEND VERSION: 0.27.1
IMAGE DIGEST: sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967
GPU: 2x RTX 6000 24GiB / Turing / sm75
RUNTIME DTYPE: half (requested)
QUANT KERNEL: compressed-tensors int4 (Marlin-class)
TP: 2

## Result

SM75_RUNTIME: NOT_REACHED (tokenizer failed before GPU work)
TP2_RUNTIME: NOT_REACHED
RUNTIME_DTYPE_COMPATIBILITY: NOT_REACHED
STARTUP_16K: FAIL
STARTUP_32K/56K/58K/60K/64K: NOT_RUN
RUNTIME_64K_FEASIBILITY: NOT_REACHED
64K_SAFE_HEADROOM: NOT_REACHED
BASIC_CHAT_SMOKE: NOT_RUN
PREFLIGHT: NOT_RUN
R7_C1_BENCHMARK_RUN: NO

## Exact blocker

STARTUP_16K failed with:
```
tokenization_kimi.py:19: from transformers.models.gpt2.tokenization_gpt2 import bytes_to_unicode
ImportError: cannot import name 'bytes_to_unicode' from 'transformers.models.gpt2.tokenization_gpt2'
```

Root cause: the Kimi Linear custom tokenizer (tokenization_kimi.py wrapping tiktoken.model) imports
`bytes_to_unicode` from GPT2, which was removed in transformers 5.x. vLLM 0.27.1 bundles transformers
5.15.0; the checkpoint is authored for transformers 4.57.1.

This is a tokenizer/transformers version incompatibility, NOT an sm75/Turing, quantization-kernel,
TP2, or dtype incompatibility, and NOT a model-quality issue.

Failure class: BACKEND_RUNTIME_ERROR.

## Classification

CANDIDATE_C_C2_RUNTIME_PREFLIGHT: FAIL (blocked at startup, before any runtime/GPU qualification)

CANDIDATE_STATUS: exact technical blocker — BACKEND_RUNTIME_ERROR (tokenizer/transformers version
incompatibility). Resolution requires Architect authorization (a vLLM build bundling transformers 4.x,
or an authorized patch of tokenization_kimi.py to use `get_byte_encoder`).

## Production

QWEN38_SCALED_DOWN: YES (restored)
N8_QWEN32_CHANGED: NO
ROUTING_CHANGED: NO
.agent_CHANGED: NO
SECRETS_EXPOSED: NO
MODEL_WEIGHTS_DOWNLOADED: YES (kept on n7 /data/models, not deleted)

RESULT: READY_FOR_CHATGPT_CONNECTOR_VERIFICATION (exact blocker documented)

Hermes does not assign PASSED/ACCEPTED. Final C-C2 acceptance belongs to ChatGPT after independent
GitHub Connector audit.
