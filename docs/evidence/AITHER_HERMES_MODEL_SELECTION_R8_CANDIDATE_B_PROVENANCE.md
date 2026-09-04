# Aither — R8 Candidate B Provenance

TASK: `AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-B`
CANDIDATE: B
VERIFICATION DATE: 2026-09-02

## Candidate canonical identity

- **Canonical name:** `Qwen/Qwen3-Coder-30B-A3B-Instruct`
- **Provider / publisher:** Qwen (Alibaba)
- **Exact immutable revision (sha):** `b2cff646eb4bb1d68355c01b18ae02e7cf42d120`
- **License:** Apache-2.0
- **Gated:** no

## Architecture

- **Architecture:** `Qwen3MoeForCausalLM` (`model_type: qwen3_moe`)
- **Class:** MoE (sparse mixture-of-experts)
- **Total parameters:** ~30B
- **Active parameters:** ~3B (8 experts / token)
- hidden_size=2048, num_hidden_layers=48, num_attention_heads=32, num_key_value_heads=4 (GQA), head_dim=128
- intermediate_size=6144, num_experts=128, num_experts_per_tok=8, moe_intermediate_size=768
- torch_dtype=bfloat16, tie_word_embeddings=false

## Context

- **Native / max_position_embeddings:** 262144 (256K), rope_theta 10,000,000
- **KV heads (GQA):** 4 (small KV cache footprint)

## Tokenizer / chat template

- **Tokenizer:** Qwen (vocab_size 151936; bos 151643, eos 151645)
- **Chat template:** Qwen3 jinja (chat_template.jinja)
- **Tool-call format:** Qwen3 native function calling; official vLLM parser `qwen3coder_tool_parser.py` (bundled in FP8 repo)
- **Reasoning control:** Qwen3 `enable_thinking` flag

## Runtimes / backend compatibility

- vLLM native (Qwen3MoeForCausalLM supported; official qwen3coder tool parser)
- llama.cpp GGUF variants available (unsloth, lmstudio-community, etc.)

## Quantizations (weights size)

- FP8 (official `Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8`): **31.20 GB** (4 safetensors: 10+10+10+1.17 GB)
- AWQ 4-bit (`QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ`): **16.83 GB**
- GGUF Q4_K_M / Q8_0 variants available

## Multimodal / projector

- None (text-only).

## Sources (text references)

- https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct
- https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
- https://huggingface.co/QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ

## Provenance verdict

PROVENANCE = PASS (repository, architecture, MoE params, context, tokenizer, template, tool format, license, revision, quant filenames/sizes all verified).
