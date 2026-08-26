# AITHER QWEN3.8-27B INFERENCE OPTIMIZATION AUDIT R1 — Evidence

TASK: AITHER-QWEN38-INFERENCE-OPTIMIZATION-AUDIT-R1
MODE: FORCE_MAJEURE_MANUAL_READ_ONLY_AUDIT
EXECUTOR: HERMES
DATE: 2026-08-26

## 1. Baseline SHA
`d0008362dae9f29f60fe2599663fa85ff9819d98` (worktree clean, production не менялся).

## 2. Live workload identity
- Deployment `vllm-qwen38-27b-fp8`, pod `vllm-qwen38-27b-fp8-66594db7fc-4dhx5`, node `bootsmam-k8s-clnt01-n7-gpu`, ns `aither-inference`.
- Image: `vllm/vllm-openai@sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967`.

## 3. vLLM/GPU/driver/CUDA/PyTorch
- vLLM 0.27.1 (V1 engine), torch 2.13.0+cu130, CUDA 13.0, NCCL 2.30.7 (backend=nccl, distributed tcp://127.0.0.1).
- Driver 590.48.01.
- GPU: 2× Quadro RTX 6000, Turing sm_75, 23040 MiB each.

## 4. Exact runtime command
`--model /model --served-model-name qwen3.8-27b --tensor-parallel-size 2 --host 0.0.0.0 --port 8000 --gpu-memory-utilization 0.90 --max-model-len 65536 --max-num-seqs 1 --dtype half --enforce-eager --reasoning-parser qwen3`

## 5. Quantization config / Marlin / native FP8
- checkpoint: FP8 E4M3 weight-only (`quantization_config` in model config; `quantization=fp8` in engine).
- runtime path: **Marlin FP8 weight-only** (`Selected MarlinFP8ScaledMMLinearKernel for Fp8LinearMethod`; warning «GPU does not have native support for FP8 computation… Weight-only FP8 compression will be used leveraging the Marlin kernel»).
- compute dtype: FP16 (`dtype=torch.float16`); KV dtype: auto→FP16.
- `MARLIN_FP8_ACTIVE = YES`; `NATIVE_FP8_COMPUTE = NO` (Turing sm_75).

## 6. GPU topology / PCIe / NVLink
- GPU0↔GPU1 = **SYS** (cross-NUMA: PCIe + SMP/QPI).
- GPU0: NUMA 0, CPU 0-27,56-83; GPU1: NUMA 1, CPU 28-55,84-111.
- PCIe: Gen3; **GPU0 = x8 (current 8/max 16), GPU1 = x16**.
- `NVLINK_INSTALLED = NO` (all links inactive — RTX 6000 не имеет NVLink).

## 7. CPU/NUMA
2 sockets / 2 NUMA nodes (0-27,56-83 и 28-55,84-111), 112 threads. Idle power ~62-64 W/250 W, P0, SM 1275 MHz, temp ~34°C.

## 8. Idle telemetry
GPU used 19063 MiB / free 3439 MiB per GPU (64K idle). KV cache 2.67 GiB/GPU, 83,614 tokens.

## 9. Decode benchmarks (temperature=0, top_p=1, stream=false)
| Test | Prompt tok | Completion tok | Wall s | Output tok/s |
|---|---:|---:|---:|---:|
| D1 128 | 38 | 128 | 14.0 | 9.16 |
| D2 512 | 37 | 512 | 54.9 | 9.32 |
| D3 2048 | 39 | 2048 | 218.1 | 9.39 |

vLLM metric: `inter_token_latency_seconds` sum/count = 2730.53 s / 24706 → **110.5 ms/token ≈ 9.05 tok/s**.

## 10. Prefill (из 64K cutover, effective wall; включает decode-хвост)
| Test | Prompt tok | Wall s | Note |
|---|---:|---:|---|
| P1 ~8K | 8393 | 19.3 | ~442 tok/s effective |
| P2 ~32K | 32012 | 367.5 | включал queueing |
| P3 ~48K | 48012 | 308.8 | — |
| P4 ~60K | 60012 | 460.2 | — |

vLLM prompt throughput во время prefill: 3200–6000 tokens/s.

## 11. vLLM metrics available
`inter_token_latency_seconds`, `generation_tokens_total`, `prompt_tokens_total`, `kv_cache_usage_perc`, `num_requests_running/waiting`. `TTFT_DIRECT = NOT_AVAILABLE_NONSTREAMING` (отдельного TTFT-метрика нет).

## 12. NCCL / TP evidence
NCCL 2.30.7, world_size=2, backend=nccl, `disable_custom_all_reduce=False` (custom all-reduce доступен). GPU0↔GPU1 SYS (cross-NUMA) + GPU0 x8 — inter-GPU comm идёт по медленному пути.

## 13. Direct vs Portal overhead
`PORTAL_OVERHEAD = NOT_MEASURED` (auth path для direct vLLM не автоматизирован в этом read-only audit).

## 14. Bottleneck classification
- **Decode**: ~9.2 tok/s; GPU idle power 25%, temp 34°C, util низкий → **не compute-saturating**. Класс: `MIXED` (inter-GPU comm over SYS + enforce-eager kernel-launch overhead + FP16 compute on Turing), confidence **MEDIUM**.
- **Prefill**: 3200–6000 tok/s prompt rate; класс `COMPUTE_BOUND` (FP16 на Turing), confidence **MEDIUM**.

## 15. enforce-eager / CUDA Graphs assessment
- `ENFORCE_EAGER_CURRENT = YES`; `CUDA_GRAPHS_ACTIVE = DISABLED` (cudagraph_mode=NONE, enforce_eager=True).
- Decode latency-bound → удаление enforce-eager (CUDA Graphs) — наиболее вероятный decode-win.

## 16. CUDA Graph memory headroom
Idle free ~3.4 GiB/GPU. `CUDA_GRAPHS_MEMORY_HEADROOM = LIKELY` (граф decode-шага компактен; но требует controlled validation).

## 17. FP8 tuning assessment
Модель уже FP8 weight-only; native FP8 compute отсутствует; дальнейший FP8 tuning даст мало. `FP8_TUNING_PRIORITY = LOW`.

## 18. INT8 W8A8 candidate (design only)
Turing имеет INT8 tensor cores (sm_75), поэтому W8A8 может дать аппаратное ускорение compute. Требует calibration + проверки toolchain Qwen3.8 (hybrid DeltaNet-слои). `INT8_W8A8_CANDIDATE = CONDITIONAL`.

## 19. W4A16 candidate (design only)
AWQ/GPTQ/Marlin W4A16 снижает weight-bandwidth; decode на Turing может выиграть. Quality risk medium-high + calibration. `W4A16_CANDIDATE = CONDITIONAL`.

## 20. NVLink current/future
`NVLINK_INSTALLED = NO`. SYS-topology + GPU0 x8 — реальный inter-GPU comm bottleneck. После физ. установки — A/B (тот же model/TP=2/64K, PCIe vs NVLink). `NVLINK_CANDIDATE = GO_FOR_TEST`.

## 21. Quality gate design (future)
Russian prose, Linux/K8s/Python/Bash/code, math/LaTeX, tables, long-context recall 8K/32K/60K, multi-turn, Continue, hallucination consistency.

## 22. Prioritized next tests
1. **CUDA Graphs A/B** (FP8 + remove enforce-eager) — decode win, low risk.
2. NVLink TP=2 A/B (после установки железа).
3. INT8 W8A8 A/B (если CUDA Graphs не даст >=10%).
4. W4A16 A/B (если нужно снизить weight-bandwidth).

## 23. Performance gates (future)
- Keep: decode +10% без quality/64K/OOM регрессий.
- Strong win: decode +20%.
- Reject: decode регрессия / quality degradation / 64K loss / instability / VRAM loss.

## 24. Rollback gates (future A/B)
startup failure / CUDA OOM / health≠200 / KV<65536 / 60K fail / decode regression / unstable latency / restart.

## 25. Health before/after + restart counts
До и после audit: Portal/Identity/qwen3-32b/qwen3.8 Ready; restart counts без изменений (0 у inference pod); `no benchmark-induced restart`.

## 26. HOLD preserved
`.agent/CURRENT_TASK.json` = `AITHER-ARCHITECT-HOLD-ALL-AUTOMATION-R1`.

## 27. Contracts unchanged
QWEN38 max-model-len=65536; backend 600s; Portal nginx 630s; VPS2 nginx 630s.

## 28. Changed paths
Только `docs/evidence/AITHER_QWEN38_INFERENCE_OPTIMIZATION_AUDIT_R1.md`.

## 29. AI_CODEX_USED: NO
## 30. AUTOMATED_RUNNER_USED: NO
## 31. SECRETS_EXPOSED: NO
