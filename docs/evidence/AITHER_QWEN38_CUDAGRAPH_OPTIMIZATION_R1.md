# AITHER QWEN38 CUDAGRAPH OPTIMIZATION R1 — Evidence (ROLLED BACK)

- TASK ID: `AITHER-QWEN38-CUDAGRAPH-OPTIMIZATION-R1`
- EXECUTOR: HERMES
- MODE: FORCE_MAJEURE / MANUAL / HERMES
- BASELINE SHA: `c2703213c7357e48d11b05d724eb2aacf20f1284`
- FINAL SHA: `<sha>`
- PARENT SHA: `c2703213c7357e48d11b05d724eb2aacf20f1284`
- BRANCH: `aither-v2`

## 1. Changed paths
- `aither-v2/services/inference/k8s/vllm-qwen38-27b-fp8.yaml` — изменялся (удалён `--enforce-eager`), затем ОТКАЧЕН к baseline. Итоговый Git diff по манифесту = пусто.
- `docs/evidence/AITHER_QWEN38_CUDAGRAPH_OPTIMIZATION_R1.md` — этот evidence.

## 2. Pre-runtime identity (baseline A)
- Pod `vllm-qwen38-27b-fp8-57b74959dd-7477b`, node n7, Ready 1/1, restartCount 0.
- Image `vllm/vllm-openai@sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967` (не изменялся).
- vLLM `0.27.1`, torch `2.13.0+cu130`, CUDA `13.0`.
- GPU: 2× Quadro RTX 6000 (Turing), idle 19309 MiB used / 3193 MiB free.
- ENFORCE_EAGER_CURRENT: YES. CUDA_GRAPHS_CURRENT: DISABLED.

## 3. Baseline A (with --enforce-eager, temperature=0 top_p=1)
Decode (3 runs each, median):
- A_D128: 9.12 tok/s. A_D512: 9.16 tok/s. A_D2048: 9.16 tok/s. AGGREGATE ≈ 9.15 tok/s.
Latency (5 runs):
- A_TTFT_P50: 0.2542 s. A_ITL_P50: 0.1087 s.
Long-context: 8K PASS (8.8s), 32K PASS (49.7s), 60K PASS (66.8s).
Agent contract: basic PASS; AUTO/FORCED/REQUIRED structured tool_calls PASS; no-tool PASS; streaming tool PASS.

## 4. Candidate B (remove --enforce-eager)
Manifest patch: удалён только `- --enforce-eager` (Git diff подтверждён — только это изменение). Rollout применён.

Live /proc/1/cmdline (candidate B): `--enforce-eager` ABSENT, все остальные args PRESENT (model, served-model-name qwen3.8-27b, TP=2, max-model-len 65536, max-num-seqs 1, dtype half, reasoning-parser qwen3, enable-auto-tool-choice, tool-call-parser qwen3_xml, generation-config vllm).

## 5. CUDA graph activation proof (candidate B)
Startup logs:
- `enforce_eager=False`.
- `compilation_config mode=<CompilationMode.VLLM_COMPILE: 3>`.
- `cudagraph_mode=<CUDAGraphMode.FULL_AND_PIECEWISE: (2,1)>`, `cudagraph_num_of_warmups=1`, `cudagraph_capture_sizes=[1,2]`, `max_cudagraph_capture_size=2`.
- Worker: `Compiling a graph for compile range (1, 2048) takes 71.09 s`.
- Worker: `Profiling CUDA graph memory: PIECEWISE=2, FULL=1`.

## 6. FAILURE — CUDA graph capture OOM (engine core crash)
При CUDA-graph capture (`determine_available_memory` / `collective_rpc`) engine core упал:
- EngineCore: `RuntimeError: cancelled` при `determine_available_memory()`.
- APIServer: `RuntimeError: Engine core initialization failed`.
- Причина: VRAM исчерпан при захвате графа — idle свободно всего ~3.1 GiB/GPU (19309/23040 MiB занято при gpu-memory-utilization=0.90 + max-model-len=65536), что недостаточно для FULL_AND_PIECEWISE capture (capture_sizes [1,2]).
- Pod ушёл в crash-loop (restartCount 1, startup probe fail).

CUDA_GRAPHS_ACTIVE: NO (capture не завершился — OOM). CAPTURE_SUCCESS: NO.

## 7. Rollback (immediate, per §11/§12/§20)
`--enforce-eager` восстановлен в манифесте, `kubectl apply` → rollout.
- Pod `vllm-qwen38-27b-fp8-57b74959dd-dx22t`, Ready 1/1, restartCount 0.
- /proc/1/cmdline: `--enforce-eager` PRESENT, остальные args PRESENT.
- /health 200. basic chat PASS ("OK"). AUTO tool structured PASS.
- Git манифест = baseline (diff пусто).

## 8. Decision / result
- DECISION: ROLLBACK (candidate B не стартует — CUDA graph capture OOM).
- No performance gain measurable (candidate не запустился).
- RESULT: `FAILED_CUDAGRAPH_NOT_ACTIVE` (graph capture failed with VRAM OOM на 2× Turing RTX 6000 при gpu-memory-utilization=0.90 + max-model-len=65536).

## 9. Immutability gates
- QWEN3-32B CHANGED: NO. PORTAL/BFF CHANGED: NO. ROUTING CHANGED: NO. NGINX/IDENTITY/GATEWAY/FRONTEND CHANGED: NO.
- QWEN3.8 IMAGE CHANGED: NO. MAX-MODEL-LEN CHANGED: NO. MAX-NUM-SEQS CHANGED: NO. TOOL PARSER CHANGED: NO. REASONING PARSER CHANGED: NO.
- .agent CHANGED: NO. AI_CODEX_USED: NO. AUTOMATED_RUNNER_USED: NO. SECRETS_EXPOSED: NO.

## 10. Recommendation (для ChatGPT)
Для CUDA Graphs на Qwen3.8-27B потребуется либо снижение gpu-memory-utilization / max-model-len для высвобождения VRAM под graph capture, либо GPU с большим VRAM. Как отдельное санкционированное задание (изменение VRAM-политики выходит за scope R1: «remove ONLY --enforce-eager»).
