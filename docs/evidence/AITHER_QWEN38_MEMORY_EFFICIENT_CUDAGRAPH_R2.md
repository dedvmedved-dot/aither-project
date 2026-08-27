# AITHER QWEN38 MEMORY-EFFICIENT CUDAGRAPH R2 — Evidence (ROLLED BACK)

- TASK ID: `AITHER-QWEN38-MEMORY-EFFICIENT-CUDAGRAPH-R2`
- EXECUTOR: HERMES
- MODE: FORCE_MAJEURE / MANUAL / HERMES
- BASELINE SHA: `4ce5679fba5f90e4de8acfed0b824b05be95c54a`
- FINAL SHA: `<sha>`
- PARENT SHA: `4ce5679fba5f90e4de8acfed0b824b05be95c54a`
- BRANCH: `aither-v2`

## 1. Changed paths
- `aither-v2/services/inference/k8s/vllm-qwen38-27b-fp8.yaml` — изменялся (удалён `--enforce-eager`, добавлен `--compilation-config`), затем ОТКАЧЕН к baseline. Итоговый diff по манифесту = пусто.
- `docs/evidence/AITHER_QWEN38_MEMORY_EFFICIENT_CUDAGRAPH_R2.md` — этот evidence.
- `docs/evidence/AITHER_QWEN38_CUDAGRAPH_OPTIMIZATION_R1.md` — только FINAL SHA placeholder fix.

## 2. R1 reference
R1 (`AITHER-QWEN38-CUDAGRAPH-OPTIMIZATION-R1`) убрал только `--enforce-eager` → default `FULL_AND_PIECEWISE` + capture_sizes `[1,2]` → CUDA graph capture VRAM OOM → engine core init failure → rollback. Baseline decode ≈ 9.15 tok/s (D128 9.12 / D512 9.16 / D2048 9.16), TTFT 0.254s, ITL 0.109s, 8K/32K/60K PASS.

## 3. Pre-runtime identity + baseline verification
- Pod `vllm-qwen38-27b-fp8-57b74959dd-...`, image `vllm/vllm-openai@sha256:0a51ea5b...` (не изменялся), vLLM 0.27.1, torch 2.13.0+cu130.
- `--enforce-eager` PRESENT; gpu-memory-utilization 0.90; max-model-len 65536; max-num-seqs 1; dtype half; tool-call-parser qwen3_xml; reasoning-parser qwen3.
- GPU idle: 19309 MiB used / 3193 MiB free.
- Baseline verification: D2048 ≈ 8.90–9.21 tok/s (соответствует R1 9.16), 60K smoke PASS, AUTO tool PASS. (D512 первые прогоны показали kernel-warmup артефакт 1.84–4.15 — не drift, объяснимо недостаточным warm-up; D2048 steady-state совпал.)

## 4. Config discovery (vLLM 0.27.1)
- Механизм: `--compilation-config` (JSON, parsed via `json.loads`) задаёт `cudagraph_mode`; `cudagraph_capture_sizes` в том же JSON.
- `CUDAGraphMode` enum: NONE, PIECEWISE, FULL, FULL_DECODE_ONLY=(2,0), FULL_AND_PIECEWISE=(2,1).
- CONFIG_SUPPORTED: YES (`CompilationConfig(cudagraph_mode='FULL_DECODE_ONLY', cudagraph_capture_sizes=[1])` парсится корректно).

## 5. Candidate B (semantic delta)
```
--enforce-eager            YES → NO (removed)
--compilation-config       absent → {"cudagraph_mode":"FULL_DECODE_ONLY","cudagraph_capture_sizes":[1]}
```
Всё остальное IDENTICAL (gpu-memory-utilization 0.90, max-model-len 65536, max-num-seqs 1, dtype half, tool parser qwen3_xml, reasoning parser qwen3).

## 6. Proof of minimal profile (before failure)
Startup logs:
- `enforce_eager=False`.
- `cudagraph_mode=<CUDAGraphMode.FULL_DECODE_ONLY: (2,0)>`.
- `cudagraph_capture_sizes=[1]`, `max_cudagraph_capture_size=1`.
- PIECEWISE: NO. CAPTURE_SIZE_2: NO. CAPTURE_SIZE_1: YES.

## 7. FAILURE — minimal graph still OOM
- Worker: `Compiling a graph for compile range (1, 2048) takes 70.55 s`.
- EngineCore: `RuntimeError: cancelled` при `determine_available_memory()` / `collective_rpc`.
- APIServer: `RuntimeError: Engine core initialization failed`.
- Pod crash-loop (restartCount 1, startup probe fail).
- Причина та же, что в R1: при удалении `--enforce-eager` включается inductor VLLM_COMPILE + CUDA graph capture, что требует доп. VRAM сверх свободных ~3.1 GiB/GPU (gpu-memory-utilization=0.90 + max-model-len=65536 на 2× Turing RTX 6000 24GB). FULL_DECODE_ONLY+[1] не помог — OOM происходит на уровне graph-capture/compilation, а не только от piecewise/размера capture.

CUDA_GRAPHS_ACTIVE: NO. CAPTURE_SUCCESS: NO.

## 8. Rollback
`--enforce-eager` восстановлен, `--compilation-config` удалён (`git checkout` манифеста → baseline). Rollout.
- Pod Ready 1/1, restartCount 0. /proc/1/cmdline: `--enforce-eager` PRESENT.
- /health 200. basic chat PASS ("OK"). AUTO tool structured PASS. 60K smoke PASS.
- Git манифест = baseline (diff пусто).

## 9. Decision / result
- DECISION: ROLLBACK (минимальный decode-only graph также OOM — VRAM недостаточно).
- RESULT: `ROLLED_BACK / MINIMAL_CUDAGRAPH_OOM`.

## 10. Immutability gates
- QWEN3-32B/Portal-BFF/Routing/Identity/nginx/Gateway/frontend: NO CHANGED.
- QWEN3.8 IMAGE / MAX_MODEL_LEN / MAX_NUM_SEQS / GPU_MEMORY_UTILIZATION / TOOL PARSER / REASONING PARSER: NO CHANGED.
- .agent: NO CHANGED. AI_CODEX_USED: NO. AUTOMATED_RUNNER_USED: NO. SECRETS_EXPOSED: NO.

## 11. Recommendation (для ChatGPT)
CUDA Graphs для Qwen3.8-27B на 2× Turing RTX 6000 невозможны при gpu-memory-utilization=0.90 + max-model-len=65536 (свободно ~3.1 GiB/GPU). Требуется отдельное санкционированное R3 задание на изменение VRAM-политики (снижение gpu-memory-utilization и/или max-model-len) либо GPU с большим VRAM. В рамках R1/R2 («remove only --enforce-eager», без изменения VRAM policy) задача невыполнима.
