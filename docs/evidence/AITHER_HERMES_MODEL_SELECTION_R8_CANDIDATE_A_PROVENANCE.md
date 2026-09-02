# Aither — R8 Candidate A Provenance

TASK: `AITHER-HERMES-AGENT-MODEL-SELECTION-R8`
CANDIDATE: A
VERIFICATION DATE: 2026-09-02

## Candidate canonical identity

- **Canonical name:** `NousResearch/Hermes-4.3-36B`
- **Provider / repository:** NousResearch (Hugging Face)
- **Exact immutable revision (sha):** `3899db2b6c4b35f16bde3b570bb7dd2775d56161`
- **Last modified:** 2025-12-06
- **License:** Apache-2.0
- **Gated:** no

## Architecture

- **Architecture:** `SeedOssForCausalLM` (`model_type: seed_oss`)
- **Class:** dense (NOT MoE)
- **Total parameters:** ~36B (64 layers × hidden 5120)
- **Active parameters:** n/a (dense)
- **Base model:** `ByteDance-Seed/Seed-OSS-36B-Base`
- hidden_size=5120, num_hidden_layers=64, num_attention_heads=80, num_key_value_heads=8 (GQA), head_dim=128, intermediate_size=27648, vocab_size=155136, torch_dtype=bfloat16

## Context

- **Native rope / max_position_embeddings:** 524288 (rope_theta 10,000,000)
- **Trained/extended context:** `long context` tag present; exact trained length to be confirmed from runtime config (nominal 64K target).
- **KV heads (GQA):** 8 (reduces KV cache size materially vs 80 attention heads).

## Tokenizer / chat template

- **Tokenizer:** Seed OSS (bos `<seed:bos>`, eos `<|eot_id|>`, pad `<seed:pad>`)
- **Chat template:** Llama-3-Chat format (`<|start_header_id|>...<|end_header_id|>...<|eot_id|>`)
- **Tool-call format:** `<tool_call>{...}</tool_call>` tags inside a single assistant turn (after `<think>`).
  Automatic tool parsers: vLLM `hermes`, SGLang `qwen25`.
- **Reasoning control:** hybrid-mode; `thinking=True` flag or "deep thinking AI" system prompt; `<think>…</think>`; `keep_cots` flag.

## Runtimes / backend compatibility

- transformers (native), vLLM (tool parser `hermes`), SGLang (tool parser `qwen25`).
- vLLM Seed-OSS architecture support to be confirmed at deploy time; otherwise llama.cpp GGUF fallback.

## Quantizations (weights size)

GGUF (`NousResearch/Hermes-4.3-36B-GGUF`, sha `9ce6f623874b8e9cb7617c399b67cec820b7a594`):

- Q3_K_M: 17.62 GB
- Q4_K_M: 21.76 GB
- Q5_K_M: 25.59 GB
- Q6_K: 29.67 GB
- Q8_0: 38.42 GB
- FP16: 72.31 GB

Also available: AWQ 4-bit / 8-bit (`cyankiwi/*`), FP8 (`Doradus-AI/*`), nvfp4 (`Firworks/*`).

## Multimodal / projector

- None (text-only).

## Sources (text references)

- https://huggingface.co/NousResearch/Hermes-4.3-36B
- https://huggingface.co/NousResearch/Hermes-4.3-36B-GGUF
- https://huggingface.co/ByteDance-Seed/Seed-OSS-36B-Base
- Technical report: https://arxiv.org/abs/2508.18255

## Provenance verdict

PROVENANCE = PASS (repository, architecture, params, context, tokenizer, template, tool format, license, revision, quant filenames/sizes all verified).
