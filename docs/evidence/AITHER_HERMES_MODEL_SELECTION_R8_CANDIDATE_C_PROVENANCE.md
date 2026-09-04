# Aither — R8 Candidate C Provenance

TASK: `AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-C`
CANDIDATE: C
VERIFICATION DATE: 2026-09-04

## Candidate canonical identity

- **Canonical name:** `moonshotai/Kimi-Linear-48B-A3B-Instruct`
- **Publisher:** Moonshot AI (Kimi)
- **Exact immutable revision (sha):** `e1df551a447157d4658b573f9a695d57658590e9`
- **License:** MIT
- **Gated:** no

## Architecture

- **Architecture:** `KimiLinearForCausalLM` (`model_type: kimi_linear`; custom `configuration_kimi` / `modeling_kimi`, trust_remote_code required)
- **Class:** MoE (sparse)
- **Total parameters:** ~48B
- **Active parameters:** ~3B (8 experts/token)
- hidden_size=2304, num_hidden_layers=27, num_attention_heads=32, num_key_value_heads=32, head_dim=72, intermediate_size=9216
- **MoE:** num_experts=256, num_experts_per_token=8, num_shared_experts=1, moe_intermediate_size=1024, sigmoid router, moe_renormalize=true
- **Attention:** hybrid linear + full attention
  - `linear_attn_config`: full_attn_layers=[4,8,12,16,20,24,27] (7 full-attention layers)
  - kda_layers (20 layers) use KDA = Kernel/Delta Attention (linear attention)
  - head_dim=128, num_heads=32, short_conv_kernel_size=4
- **MLA:** kv_lora_rank=512, mla_use_nope=true (Multi-head Latent Attention, NoPE)
- dtype=bfloat16

## Context

- **Native / model_max_length:** 1048576 (1M)

## Tokenizer / chat template

- Tokenizer: Moonshot (bos 163584, eos 163586)
- Chat template: Kimi Linear jinja (trust_remote_code)
- Tool/function-call format: Kimi Linear native (to be confirmed at runtime — not reached, blocked at backend gate)
- Reasoning control: to be confirmed (not reached)

## Runtimes / official guidance

- HF Transformers (trust_remote_code=True) + FLA (flash-linear-attention) KDA kernel
- vLLM: "latest vllm" recommended; official example uses `--tensor-parallel-size 4 --max-model-len 1048576 --trust-remote-code`
- llama.cpp: GGUF mirrors exist (bartowski), but support status unverified

## Quantizations (available)

- Official BF16; FP8-DYNAMIC (nm-testing), AWQ-4bit/8bit (cyankiwi), nvfp4 (Firworks), GGUF (bartowski), MLX, GPTQ-Int4

## Sources

- https://huggingface.co/moonshotai/Kimi-Linear-48B-A3B-Instruct

## Provenance verdict

PROVENANCE = PASS (repository, architecture, MoE, Delta Attention/KDA, MLA, context, tokenizer, license, revision all verified).
