# Aither — R8 Candidate C-C1 Code-path proof

TASK: `AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-C-C1-BACKEND-COMPATIBILITY-CLOSURE`
CANDIDATE: moonshotai/Kimi-Linear-48B-A3B-Instruct
REVISION: e1df551a447157d4658b573f9a695d57658590e9
BACKEND AUDITED: vLLM 0.27.1 (image sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967)

## 1. Exact config (immutable revision e1df551a)

- architectures: KimiLinearForCausalLM
- model_type: kimi_linear
- dtype: bfloat16
- hidden_size 2304, num_hidden_layers 27, num_attention_heads 32, num_key_value_heads 32
- linear_attn_config: full_attn_layers=[4,8,12,16,20,24,27], kda_layers (20 layers), head_dim 128, num_heads 32, short_conv_kernel_size 4
- q_lora_rank: null; kv_lora_rank 512; mla_use_nope true
- num_experts 256, num_experts_per_token 8, num_shared_experts 1
- **`use_full_rank_gate`: ABSENT** (not present in config.json)
- **`gate_lower_bound`: ABSENT**

## 2. HF configuration_kimi.KimiLinearConfig

- The HF custom `KimiLinearConfig.__init__` contains NO `use_full_rank_gate` and NO `gate_lower_bound` parameter.
- These flags are vLLM-runtime concepts, not part of the standalone Kimi-Linear HF config.

## 3. vLLM registry mapping

`vllm/model_executor/models/registry.py`:
```
"KimiLinearForCausalLM": ("vllm.models.kimi_k3", "KimiLinearForCausalLM"),
```

## 4. Layer attention selection (vllm/models/kimi_k3/nvidia/model.py)

Lines 796-804:
```python
if kda_config.get("use_full_rank_gate", False):
    self.self_attn = KimiK3DeltaAttention(...)
else:
    self.self_attn = KimiLinearGatedDeltaNetAttention(...)
```

`KimiLinearGatedDeltaNetAttention` is imported at model.py:44 as an alias:
```python
from vllm.model_executor.layers.mamba.gdn.base import (
    KimiGatedDeltaNetAttention as KimiLinearGatedDeltaNetAttention,
)
```

Since `use_full_rank_gate` is absent in the exact config, `kda_config.get("use_full_rank_gate", False)`
evaluates to **False**, therefore the exact Candidate C enters the **else** branch:

**ACTUAL_KDA_CLASS = KimiLinearGatedDeltaNetAttention** (= KimiGatedDeltaNetAttention, shared GDN base).

## 5. KimiK3DeltaAttention (NOT used by Candidate C)

`vllm/models/kimi_k3/nvidia/kda.py`:
- class KimiK3DeltaAttention(GatedDeltaNetAttention) at line 286
- assert `use_full_rank_gate` True at lines 327-328: "KimiK3DeltaAttention requires a full-rank gate"
- FlashKDA SM90/SM10x/SM12x gating at kda.py:154-238 ("FlashKDA requires CUDA SM90/SM10x/SM12x")

This path is reachable ONLY when `use_full_rank_gate=True`. The exact Candidate C config does NOT set it,
so Candidate C does NOT instantiate KimiK3DeltaAttention and does NOT reach the FlashKDA SM90 gate.

## 6. Shared Kimi GDN prefill/decode backend (kimi_gdn_linear_attn.py)

Lines 271-286:
```python
self.gate_lower_bound = kda_config.get("gate_lower_bound", None)  # None for Candidate C
...
backend = additional_config.get("kda_prefill_backend", "auto")
backend = "triton" if backend == "auto" else backend
assert backend == "triton", "The shared Kimi GDN layer only supports the Triton KDA prefill backend"
```

- ACTUAL_PREFILL_BACKEND = **triton** (forced; "auto" resolves to "triton").
- ACTUAL_DECODE_BACKEND = **triton** (fused_recurrent KDA op, Triton-based).
- `use_safe_gate = False` (gate_lower_bound is None).

## 7. FLA KDA Triton ops (vllm/third_party/flash_linear_attention/ops/)

Scanned: kda.py, fused_recurrent.py, chunk.py, fused_norm_gate.py, fused_sigmoid_gating.py,
cumsum.py, wy_fast.py, solve_tril.py, layernorm_guard.py, chunk_scaled_dot_kkt.py, chunk_delta_h.py.

- NO `is_device_capability(...)` / `get_device_capability()` / `has_device_capability(...)` calls.
- NO hardcoded sm75/sm80/sm90 checks.
- NO `assert dtype == bfloat16` (no BF16-only assertion).
- Kernels use Triton `dtype.element_ty` generically; `out_dtype`/`residual_dtype` default to input dtype.

Conclusion: the Triton KDA kernels are compute-capability-agnostic and dtype-generic.

## 8. Verdict

- EXACT_CONFIG_USE_FULL_RANK_GATE = ABSENT (runtime default False).
- ACTUAL_KDA_CLASS = KimiLinearGatedDeltaNetAttention (shared GDN, Triton).
- FLASHKDA_RESTRICTION_APPLIES = NO (only KimiK3DeltaAttention / full-rank-gate path).
- MANDATORY_SM_CAPABILITY = NONE_PROVEN (no compute-capability check in the Triton path).
