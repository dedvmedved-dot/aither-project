# Aither — R8 Candidate C-C2-R1 Report

TASK: AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-C-C2-R1-TOKENIZER-COMPATIBILITY-CLOSURE-AND-RUNTIME-RESUME
BASELINE: 26846ebd50a46a7a1c13449f5bebf414d3bb8adb
CANDIDATE: moonshotai/Kimi-Linear-48B-A3B-Instruct
BASE MODEL REVISION: e1df551a447157d4658b573f9a695d57658590e9
REPRESENTATION: cyankiwi/Kimi-Linear-48B-A3B-Instruct-AWQ-4bit
REPRESENTATION REVISION: 5d029d1844aa64ec302e14466be7d0353c6e697f
BACKEND: vLLM 0.27.1
IMAGE DIGEST: sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967

## Tokenizer correction (closed)

- TRANSFORMERS_DOWNGRADE_PERFORMED: NO
- BACKEND_CHANGED: NO
- MODEL_REPRESENTATION_CHANGED: NO
- TIKTOKEN_MODEL_MATCH: YES
- SPECIAL_TOKENS_MATCH: NO (additional_special_tokens only; immaterial)
- TOKENIZER_CONFIG_COMPATIBLE: YES (identical)
- CHAT_TEMPLATE_COMPATIBLE: YES (identical)
- TOKENIZATION_SEMANTICS_EQUIVALENT: YES
- PATCH_SOURCE: MINIMAL_EQUIVALENT_PATCH (base import line)
- PATCH_SCOPE: tokenization_kimi.py line 19 (import source)
- PATCH_CHANGES_TOKENIZATION_SEMANTICS: NO
- TOKENIZER_IMPORT / INSTANTIATION / ROUNDTRIP: PASS
- TOKENIZER_BASE_EQUIVALENCE: 100%

## Runtime (resumed from 16K)

- TOKENIZER_LOAD_RUNTIME=PASS
- ARCHITECTURE_LOAD=PASS
- QUANT_KERNEL_INIT=PASS (MarlinExperts)
- TP2_INIT=PASS (world size 2)
- RUNTIME_DTYPE=FP16
- SM75_RUNTIME=FAIL
- KDA_RUNTIME=FAIL
- STARTUP_16K: model loaded + /health 200, but first inference crashed the worker.

## Exact blocker

```
triton.runtime.errors.OutOfResources: out of resource: shared memory,
Required: 102400, Hardware limit: 65536
```

KDA chunk kernel (`chunk_gated_delta_rule_fwd_kernel`) requires 100 KiB shared memory; Turing (sm75)
provides 64 KiB. Hard sm75 runtime incompatibility -> worker crash (RESTARTS=1) + subsequent inference hangs.

## Classification

- KDA_RUNTIME=FAIL; SM75_RUNTIME=FAIL
- Failure class: KDA_RUNTIME_INCOMPATIBLE
- STARTUP_32K..64K / RUNTIME_64K_FEASIBILITY / PREFLIGHT / PERFORMANCE: NOT_RUN

CANDIDATE_C_C2_R1_RUNTIME_PREFLIGHT: FAIL
CANDIDATE_STATUS: exact technical blocker — KDA_RUNTIME_INCOMPATIBLE (sm75 shared-memory limit)

This is a hardware/runtime incompatibility, NOT a model-quality failure, and NOT the earlier tokenizer blocker
(which is now closed). The tokenizer fix was correct; the subsequent KDA shared-memory limit is a separate,
newly-proven sm75 blocker.

## Production

QWEN38_SCALED_DOWN: YES (restored)
N8_QWEN32_CHANGED: NO
ROUTING_CHANGED: NO
.agent_CHANGED: NO
SECRETS_EXPOSED: NO
R7_C1_BENCHMARK_RUN: NO

RESULT: READY_FOR_CHATGPT_CONNECTOR_VERIFICATION (exact blocker documented)
