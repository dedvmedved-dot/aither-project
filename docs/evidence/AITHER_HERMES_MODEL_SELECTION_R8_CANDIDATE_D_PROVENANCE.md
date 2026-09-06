# Aither — R8 Candidate D Provenance

TASK: AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-D-GPT-OSS-20B
CANDIDATE: D
MODEL: openai/gpt-oss-20b

## Identity

- MODEL_REPOSITORY: openai/gpt-oss-20b
- MODEL_REVISION: 6cee5e81ee83917806bbde320786a8fb61efebee (immutable HF sha)
- MODEL_COMMIT_DATE: 2025-08-26
- PUBLISHER: OpenAI
- LICENSE: apache-2.0
- GATED: no

## Architecture (verified from config.json)

- architectures: GptOssForCausalLM
- model_type: gpt_oss
- num_hidden_layers: 24
- hidden_size: 2880
- intermediate_size: 2880
- num_attention_heads: 64
- num_key_value_heads: 8 (GQA)
- head_dim: 64
- num_local_experts: 32
- experts_per_token / num_experts_per_tok: 4
- max_position_embeddings: 131072 (128K)
- initial_context_length: 4096
- sliding_window: 128
- rope_scaling: YaRN (factor 32, original 4096 -> 128K, beta_fast 32, beta_slow 1)
- rope_theta: 150000
- vocab_size: 201088
- transformers_version: 4.55.0.dev0

## Quantization (official checkpoint)

- quant_method: mxfp4
- modules_to_not_convert: self_attn, mlp.router, embed_tokens, lm_head (remain higher precision)
- MXFP4 applies to the MoE expert weights only.

## Verdict

PROVENANCE=PASS (official repo pinned to immutable sha, architecture/config/quantization verified).
