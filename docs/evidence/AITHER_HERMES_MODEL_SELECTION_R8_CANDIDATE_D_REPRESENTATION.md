# Aither — R8 Candidate D Representation

TASK: AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-D-GPT-OSS-20B

## Representation candidates

- Official native MXFP4 (HF safetensors): requires vLLM sm80+ -> NOT viable on sm75.
- Native MXFP4 GGUF: `ggml-org/gpt-oss-20b-GGUF` -> `gpt-oss-20b-MXFP4.gguf` = 12.11 GB (official ggml-org).
- Standard GGUF quants: `unsloth/gpt-oss-20b-GGUF` -> Q4_K_M 11.62 GB, Q5_K_M 11.72 GB, Q8_0 12.11 GB.

## Selection

SELECTED_REPRESENTATION = ggml-org/gpt-oss-20b-MXFP4.gguf (native MXFP4, official) — 12.11 GB.
Fallback = unsloth Q4_K_M (11.62 GB) if native MXFP4 GGUF fails to load on sm75.

## Static 64K memory feasibility (architecture-correct)

- Weights: 12.11 GB (MXFP4 MoE + higher-precision attention/router/embeddings/lm_head).
- KV cache: GQA 8 KV-heads, head_dim 64, 24 layers.
  - per token (fp16) = 2 x 24 x 8 x 64 x 2 B = 48 KB.
  - full-attention 64K worst-case = 48 KB x 65536 = 3.0 GB.
  - sliding_window=128 on most layers materially reduces the practical KV footprint.
- Runtime: CUDA context ~0.5 GB, MoE/workspace buffers ~1-2 GB.
- Estimated 64K total: ~12.1 + ~3.0 + ~2 = ~17 GB (fits 22.5 GB single GPU, or split 2 GPUs).

STATIC_64K_FEASIBILITY = PASS (plausible; runtime to be confirmed in Phase C)
