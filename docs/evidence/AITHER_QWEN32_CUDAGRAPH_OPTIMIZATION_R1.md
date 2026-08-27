# AITHER QWEN32 CUDAGRAPH OPTIMIZATION R1 — Evidence (BASELINE MISMATCH)

- TASK ID: `AITHER-QWEN32-CUDAGRAPH-OPTIMIZATION-R1`
- EXECUTOR: HERMES
- MODE: FORCE_MAJEURE / MANUAL / HERMES
- BASELINE SHA: `be0114e781799ac6d29d25a447f3bd6480b6f455`
- FINAL SHA: `<sha>`
- PARENT SHA: `be0114e781799ac6d29d25a447f3bd6480b6f455`
- BRANCH: `aither-v2`

## 1. Changed paths
- `aither-v2/deploy/vllm-qwen3-32b-awq.yaml` — исправлен `limits.cpu` 16 → 8 (см. §5). CUDA-graph candidate НЕ применялся.
- `docs/evidence/AITHER_QWEN32_CUDAGRAPH_OPTIMIZATION_R1.md` — этот evidence.

## 2. Pre-runtime snapshot (baseline A)
- Pod `vllm-qwen3-32b-awq-86cb6c9845-n2xpg`, node n8, Ready 1/1, restartCount 0.
- image `vllm/vllm-openai@sha256:6cf9808ca8810fc6c3fd0451c2e7784fb224590d81f7db338e7eaf3c02a33d33` (не изменялся).
- vLLM `0.8.5`, torch `2.6.0+cu124`, CUDA `12.4`.
- `/proc/1/cmdline`: `--quantization awq --dtype auto --tensor-parallel-size 2 --gpu-memory-utilization 0.90 --max-model-len 65536 --max-num-seqs 4 --enforce-eager --generation-config vllm --served-model-name qwen3-32b --enable-auto-tool-choice --tool-call-parser hermes`.
- GPU idle: 20567 MiB used / ~1935 MiB free (МЕНЬШЕ, чем у Qwen3.8 — ~3.1 GiB free).

## 3. CUDA graph capability discovery (vLLM 0.8.5)
- vLLM 0.8.5 (отличается от Qwen3.8 0.27.1). CUDA Graph активируется удалением `--enforce-eager` (hybrid eager + CUDA graph). Флаг `--max-seq-len-to-capture` доступен. Default capture sizes `[1, 2, 4, 8]` (max-num-seqs=4).
- CUDAGRAPH_SUPPORTED: YES.

## 4. Baseline A performance
- Decode (temp=0, top_p=1): D128 19.58, D512 19.75, D2048 19.41 tok/s (aggregate ≈ 19.58).
- Latency: TTFT_p50 0.0755s, ITL_p50 0.0501s.
- Long-context 8K/32K/60K: PASS. Tool (basic/auto/forced/required/no-tool): PASS.

## 5. BASELINE MISMATCH — manifest cpu limit violates LimitRange
- Канонический манифест `deploy/vllm-qwen3-32b-awq.yaml` содержит `limits.cpu: "16"`.
- В namespace действует LimitRange `aither-limits` (создан 2026-08-17): `max.cpu = 8`.
- Старый pod (создан 2026-08-10, ДО LimitRange) имел cpu 16 и был «grandfathered».
- Попытка `kubectl apply` манифеста (для удаления `--enforce-eager`) привела к `Error creating: pods ... is forbidden: maximum cpu usage per Container is 8, but limit is 16` → новый pod не создавался → deployment 0/1 (production outage для agent-fast → qwen3-32b).

Это pre-existing manifest/runtime drift: `deploy/` манифест не обновлялся после введения LimitRange. Канонический манифест как-есть НЕ применим.

## 6. Restore (не CUDA-graph)
Для восстановления production deployment:
- `limits.cpu` 16 → 8 (единственное допустимое значение по LimitRange; это изменение ресурса вне предписанного scope, но необходимое для восстановления).
- `--enforce-eager` оставлен (candidate НЕ применялся).
- Deployment восстановлен: pod Ready 1/1, restartCount 0, /health 200, basic chat "OK", AUTO tool structured PASS, cpu_limit=8.

## 7. Immutability gates
- QWEN3.8 / Portal-BFF / Routing / Identity / nginx / Gateway / frontend: NO CHANGED.
- QWEN3-32B image / quantization / dtype / TP / max-model-len / max-num-seqs / gpu-memory-utilization / tool parser / served-name / generation-config: NO CHANGED.
- .agent: NO CHANGED. AI_CODEX_USED: NO. AUTOMATED_RUNNER_USED: NO. SECRETS_EXPOSED: NO.

## 8. Decision / result
- CUDA graph candidate НЕ тестировался (baseline manifest invalid).
- DECISION: НЕ ПРИМЕНЁН.
- RESULT: `BASELINE_MISMATCH`.

## 9. Recommendation (для ChatGPT)
Требуется отдельное санкционированное задание на исправление `deploy/vllm-qwen3-32b-awq.yaml` `limits.cpu` (16 → 8) для соответствия LimitRange. После этого CUDA-graph A/B (remove --enforce-eager) можно выполнить повторно. Дополнительно: у Qwen3-32B свободно ~1.9 GiB/GPU при max-num-seqs=4 (capture sizes [1,2,4,8]) — риск OOM при CUDA-graph capture высок (по аналогии с Qwen3.8 R1/R2, где при 3.1 GiB free оба профиля OOM).
