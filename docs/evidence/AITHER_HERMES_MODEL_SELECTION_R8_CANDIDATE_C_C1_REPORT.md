# Aither — R8 Candidate C-C1 Backend Compatibility Closure Report

TASK: AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-C-C1-BACKEND-COMPATIBILITY-CLOSURE
BASELINE: a41c7eff69f7be1c5e13268b5b2300f4b4b1e822
CANDIDATE: moonshotai/Kimi-Linear-48B-A3B-Instruct
REVISION: e1df551a447157d4658b573f9a695d57658590e9

PREVIOUS_CLAIM: HARDWARE_BACKEND_INCOMPATIBLE_FOR_HERMES_64K
PREVIOUS_CLAIM_AUDIT: REJECTED

## Core correction

The previous analysis treated the private Kimi-K3 full-rank-gate KDA path (KimiK3DeltaAttention /
FlashKDA SM90) as if it were the mandatory standalone Kimi-Linear path. It is not.

EXACT_CONFIG_USE_FULL_RANK_GATE: ABSENT (config.json has no `use_full_rank_gate`; the HF
KimiLinearConfig class has no such parameter; vLLM default is False).

ACTUAL_KDA_CLASS: KimiLinearGatedDeltaNetAttention (= KimiGatedDeltaNetAttention, shared GDN base,
vllm/model_executor/layers/mamba/gdn/kimi_gdn_linear_attn.py)

ACTUAL_PREFILL_BACKEND: triton (forced: `backend = "triton" if backend == "auto" else backend;
assert backend == "triton"`)

ACTUAL_DECODE_BACKEND: triton (fused_recurrent KDA, Triton-based)

FLASHKDA_RESTRICTION_APPLIES: NO (FlashKDA SM90/SM10x/SM12x gate is inside KimiK3DeltaAttention only,
which requires `use_full_rank_gate=True`; Candidate C does not enter that branch)

MANDATORY_SM_CAPABILITY: NONE_PROVEN (the FLA KDA Triton ops contain no compute-capability checks)

OPTIONAL_OPTIMIZATION_CAPABILITIES: SM90/SM100/SM120 (FlashKDA, FlashInfer GDN) — optional, not the
Candidate C path.

BF16_NATIVE_SM75: NO (no BF16 tensor cores on Turing sm75; BF16 is emulated)

FP16_MODEL_OVERRIDE_SUPPORTED: UNPROVEN (vLLM `--dtype half` plausible but untested on this checkpoint)

KDA_FP16_SUPPORTED: YES (dtype-generic Triton kernels)

VLLM_COMPATIBILITY: PASS (static — exact path is compute-capability-agnostic Triton)

LLAMACPP_PROJECT_BUILD: FAIL (build 10666 has no Kimi Linear architecture)

LLAMACPP_UPSTREAM: UNPROVEN

TP2_STATIC_COMPATIBILITY: PASS (num_heads 32 % tp_size 2 == 0, asserted in source)

TP2_RUNTIME_COMPATIBILITY: NOT_TESTED

SELECTED_PLAUSIBLE_REPRESENTATION: AWQ 4-bit (or GGUF Q4_K_M) — ~24 GB

REPRESENTATION_64K_STATIC_FEASIBILITY: PASS (plausible, ~28-32 GB estimate; linear-attention state is
O(1) w.r.t. context; only 7/27 layers have context-proportional KV)

MICROPROBE_REQUIRED: NO (static analysis settles the prior blocker; runtime remains untested)
MICROPROBE_RESULT: NOT_RUN

QWEN38_SCALED_DOWN: NO
QWEN38_RESTORED: NOT_APPLICABLE (production never touched)
N8_QWEN32_CHANGED: NO
ROUTING_CHANGED: NO
.agent_CHANGED: NO
MODEL_WEIGHTS_DOWNLOADED: NO
CANDIDATE_C_DEPLOYED: NO
R7_C1_BENCHMARK_RUN: NO
SECRETS_EXPOSED: NO

BACKEND_COMPATIBILITY_C_C1: PASS_STATIC

CANDIDATE_STATUS: MODEL_QUALITY_NOT_EVALUATED

RESULT: READY_FOR_CHATGPT_CONNECTOR_VERIFICATION

## Note

PASS_STATIC means: the exact standalone Kimi-Linear path has no proven sm75 blocker, TP2 is statically
valid, and a plausible low-bit representation exists with plausible 64K headroom. Runtime compatibility
remains untested — a later GPU microprobe or controlled LAB run would be required before any model-quality
benchmark. No weights were downloaded and no maintenance window was opened in this task.

Hermes does not assign PASSED/ACCEPTED. Final C-C1 acceptance belongs to ChatGPT after independent
GitHub Connector audit.
