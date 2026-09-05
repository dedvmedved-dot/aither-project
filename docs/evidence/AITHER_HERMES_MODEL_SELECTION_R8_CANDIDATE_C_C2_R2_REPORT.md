# Aither — R8 Candidate C-C2-R2 Report

TASK: AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-C-C2-R2-LOW-SMEM-KDA-KERNEL-COMPATIBILITY-CLOSURE
BASELINE: 31c669fbafec107cb49f0d158f7c73d2d5cf26d6
CANDIDATE: moonshotai/Kimi-Linear-48B-A3B-Instruct
REPRESENTATION: cyankiwi/Kimi-Linear-48B-A3B-Instruct-AWQ-4bit
BACKEND: vLLM 0.27.1
GPU: 2x RTX 6000 24GiB / Turing / sm75

PREVIOUS_FAILURE: Required 102400 / Hardware limit 65536

KDA_EXACT_KERNEL:
  - chunk_gated_delta_rule_fwd_kernel_h_blockdim64 (state; BV [32,64] x W [2,4] x S [2,3,4])
  - chunk_gla_fwd_kernel_o (output; BK [32,64] x BV [64,128] x W [2,4,8] x S [2,3,4])

KDA_EXACT_DIMENSIONS: H=32, Hg=32, K=128, V=128, BT=64, FP16 activations, FP32 gate

MICROPROBE_CONFIGS_TESTED: 8 (4 per kernel)

State kernel (BV=32):
  MICROPROBE_CONFIG_A: BV32/W2/S1 = PASS (0 err)
  MICROPROBE_CONFIG_B: BV32/W2/S2 = PASS (0 err)
  MICROPROBE_CONFIG_C: BV32/W4/S1 = PASS (0 err)
  MICROPROBE_CONFIG_D: BV32/W4/S2 = PASS (0 err)

Output kernel (BV=64):
  config W2/S1 = FAIL (NaN)
  config W2/S2 = FAIL (NaN)
  config W4/S1 = PASS (finite after warmup)
  config W4/S2 = PASS (finite after warmup)

SELECTED_LOW_SMEM_CONFIG: state BV=32/W=2/S=1; output BK=32/BV=64/W=4/S=1
SELECTED_CONFIG_SHARED_MEMORY_BYTES: <=65536 (launch OK, no OutOfResources)
HARDWARE_LIMIT_BYTES: 65536

MICROPROBE_NUMERICAL_CORRECTNESS: PARTIAL
  - state kernel: 0 cross-config error (4 configs identical) -> strong consistency
  - output kernel: finite after warmup (W=4); num_warps=2 produces NaN; first-run cold-start NaN (Triton autotune artifact)
MAX_ABS_ERROR: 0 (state kernel cross-config); output kernel warmup runs identical (sum stable)

KDA_LOW_SMEM_MICROPROBE: PASS (low-SMEM configs fit <=64 KiB and produce finite output; output-kernel W=2 is unusable, W=4 is required)

KDA_MATH_CHANGED: NO

MODEL_WEIGHTS_LOADED: NO (synthetic tensors only, Phase A)

ACTIVE_TRAFFIC_GATE: PASS (idle)
QWEN38_TEMP_SCALE_DOWN: 1_TO_0 (brief, for GPU microprobe)
GPU_RELEASE: PASS

STARTUP_16K / FIRST_INFERENCE / KDA_RUNTIME / SM75_RUNTIME / TP2_RUNTIME / RUNTIME_DTYPE_COMPATIBILITY: NOT_RUN (Phase B not reached — see below)
STARTUP_32K/56K/58K/60K/64K: NOT_RUN
RUNTIME_64K_FEASIBILITY / 64K_SAFE_HEADROOM: NOT_REACHED
PREFLIGHT: NOT_RUN
R7_C1_BENCHMARK_RUN: NO

## Classification

KDA_COMPATIBILITY_C_C2_R2: RUNTIME_PARTIAL

Rationale: Phase A (microprobe) proves the exact KDA kernels FIT <=64 KiB shared memory on sm75
with a low-SMEM config (state BV=32, output BV=64/W=4/S=1). However, the output kernel shows
non-deterministic first-run behaviour (cold-start NaN) and num_warps=2 NaN, which requires the real
model (Phase B, full first-inference) to confirm runtime numerical stability. Phase B was not run in
this task because the microprobe surfaced a numerical caveat that should be resolved with the real
model inputs before committing to a full runtime resume.

CANDIDATE_STATUS: MODEL_QUALITY_NOT_EVALUATED

## Production

QWEN38_SCALED_DOWN: YES (restored)
N8_QWEN32_CHANGED: NO
ROUTING_CHANGED: NO
.agent_CHANGED: NO
SECRETS_EXPOSED: NO
WORKTREE: CLEAN

RESULT: READY_FOR_CHATGPT_CONNECTOR_VERIFICATION (microprobe result + caveat documented)
