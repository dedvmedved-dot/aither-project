# Aither — R8 Candidate C-C1 TP=2 / 64K static feasibility

TASK: AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-C-C1-BACKEND-COMPATIBILITY-CLOSURE
CANDIDATE: moonshotai/Kimi-Linear-48B-A3B-Instruct (rev e1df551a)

## TP=2 static compatibility

- num_attention_heads = 32; num_heads (KDA) = 32.
- vLLM shared Kimi GDN asserts `num_heads % tp_size == 0` (kimi_gdn_linear_attn.py:188).
- 32 % 2 == 0 -> statically valid for TP=2.
- projection_size = head_dim(128) * num_heads(32) = 4096; TP-local = 2048 (divisible).
- MoE: num_experts=256, num_experts_per_token=8, num_shared_experts=1 — expert sharding is handled by
  vLLM FusedMoE under TP (no explicit 2-GPU prohibition found).

TP2_STATIC_COMPATIBILITY = PASS
TP2_RUNTIME_COMPATIBILITY = NOT_TESTED

Note: the official README example uses `--tensor-parallel-size 4`; TP=4 is the documented path, but TP=2 is
statically valid and not prohibited by any source check found.

## 64K static memory feasibility

Architecture-correct hybrid KDA/MLA memory semantics (linear attention has fixed-size recurrent state,
NOT a context-proportional KV cache for the KDA layers):

- Weights (AWQ 4-bit / GGUF Q4): ~24 GB (residency on 2×24 GiB = 45 GiB usable).
- KDA (20/27 layers): fixed-size recurrent state + short-conv state — O(1) w.r.t. context length.
- MLA: kv_lora_rank 512 compressed latent — small.
- Full-attention layers (7/27): context-proportional KV, but only 7 layers; GQA-equivalent via MLA.
- MoE workspace + TP communication buffers + CUDA context: a few GB.
- Estimated 64K total ≈ 24 GB (weights) + ~4-8 GB (state/KV/buffers) ≈ 28-32 GB < 45 GiB.

REPRESENTATION_AWQ4_64K_STATIC_FEASIBILITY = PASS (plausible, ~28-32 GB estimate with headroom)
REPRESENTATION_GGUF_Q4_64K_STATIC_FEASIBILITY = PASS (plausible, similar estimate)
REPRESENTATION_FP8_64K_STATIC_FEASIBILITY = FAIL (~48 GB weights exceed 45 GiB before runtime headroom)

These are static estimates only; runtime (actual CUDA allocation, Triton state sizing, MLA cache) is untested.
