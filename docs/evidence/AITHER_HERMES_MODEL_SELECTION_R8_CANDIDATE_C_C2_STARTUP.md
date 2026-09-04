# Aither — R8 Candidate C-C2 Startup evidence

TASK: AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-C-C2-RUNTIME-FEASIBILITY-AND-PREFLIGHT
CANDIDATE: moonshotai/Kimi-Linear-48B-A3B-Instruct (AWQ-4bit compressed-tensors int4)
BACKEND: vLLM 0.27.1 (image sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967)

## Startup attempts

### Attempt 1 (16K)

- manifest error: `--enable-auto-tool-choice requires --tool-call-parser`.
- Classification: MANIFEST_ERROR (not a model incompatibility).
- Fix: added `--tool-call-parser kimi_k3` (vLLM 0.27.1 ships vllm/tool_parsers/kimi_k3_tool_parser.py).

### Attempt 2 (16K) — FAIL

- Error during tokenizer load:
  ```
  tokenization_kimi.py:19: from transformers.models.gpt2.tokenization_gpt2 import bytes_to_unicode
  ImportError: cannot import name 'bytes_to_unicode' from 'transformers.models.gpt2.tokenization_gpt2'
  ```
- Root cause: the Kimi Linear custom tokenizer (tokenization_kimi.py) wraps the tiktoken model and
  imports `bytes_to_unicode` from GPT2. That symbol was removed in transformers 5.x.
- vLLM 0.27.1 bundles transformers **5.15.0**; the Kimi Linear checkpoint is authored for
  transformers **4.57.1** (config.json `transformers_version`).
- The failure occurs at tokenizer construction, BEFORE any GPU/quantization/sm75 code runs.

## Classification

- STARTUP_16K = FAIL
- Failure class: **BACKEND_RUNTIME_ERROR** — tokenizer/transformers version incompatibility
  (model custom tokenizer requires transformers 4.x `bytes_to_unicode`; vLLM 0.27.1 ships transformers 5.15.0).

This is NOT an sm75/Turing incompatibility, NOT a quantization-kernel incompatibility, NOT a TP2 or
dtype failure, and NOT a model-quality issue. It is a backend/tokenizer version mismatch.

Resolution options (require Architect authorization, not performed in C-C2):
1. use a vLLM build bundling transformers 4.x compatible with the model tokenizer; or
2. patch tokenization_kimi.py to use `get_byte_encoder` (transformers 5.x equivalent).
