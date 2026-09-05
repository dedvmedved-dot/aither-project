# Aither — R8 Candidate C-C2-R1 Startup / Runtime evidence

TASK: AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-C-C2-R1-TOKENIZER-COMPATIBILITY-CLOSURE-AND-RUNTIME-RESUME
CANDIDATE: moonshotai/Kimi-Linear-48B-A3B-Instruct (AWQ-4bit compressed-tensors int4, patched tokenizer)
BACKEND: vLLM 0.27.1

## Startup (16K) — tokenizer fixed, model loads

- TOKENIZER_LOAD=PASS (patched import resolved)
- ARCHITECTURE_LOAD=PASS (KimiLinearForCausalLM recognized)
- QUANTIZATION_CONFIG_LOAD=PASS (compressed-tensors int4 recognized)
- QUANT_KERNEL_INIT=PASS ("Using MarlinExperts" / "MoEPrepareAndFinalizeNoDPEPModular")
- TP2_INIT=PASS (rank0/rank1 workers; TP world size 2)
- DTYPE_INIT=PASS (FP16; Triton kernels compiled with torch.float16)
- MODEL_WEIGHTS_GPU_LOAD=PASS (7/7 shards, 30.74s)
- HEALTH=PASS (/health 200); V1_MODELS=PASS (max_model_len=16384)
- GPU residency: ~20.6 GiB used / ~1.9 GiB free per GPU at 16K

## KDA runtime — FAIL (exact sm75 blocker)

First inference triggered Triton JIT compilation of the KDA/GLA kernels. The worker crashed with:

```
triton.runtime.errors.OutOfResources: out of resource: shared memory,
Required: 102400, Hardware limit: 65536.
Reducing block sizes or num_stages may help.
```

Root cause: the KDA chunk kernel (`chunk_gated_delta_rule_fwd_kernel`) requires 102400 bytes (100 KiB)
of shared memory, but Turing (sm75) hardware limit is 65536 bytes (64 KiB). This is a hard,
reproducible sm75 incompatibility (worker crash -> pod RESTARTS=1; subsequent inference hangs on the
same kernel path).

## Classification

- KDA_RUNTIME=FAIL (sm75 shared-memory limit)
- SM75_RUNTIME=FAIL
- Failure class: KDA_RUNTIME_INCOMPATIBLE (KDA Triton kernel needs 100 KiB shared memory > 64 KiB sm75)
- Startup 32K..64K, preflight, performance: NOT_RUN (blocked at first inference at 16K)

This is a hardware/runtime incompatibility, NOT a model-quality failure.
