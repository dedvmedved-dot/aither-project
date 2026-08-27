# AITHER QWEN38 W4A16 PREQUANTIZED CANDIDATE QUALIFICATION R3 — Evidence

- TASK ID: `AITHER-QWEN38-W4A16-PREQUANTIZED-CANDIDATE-QUALIFICATION-R3`
- EXECUTOR: HERMES
- MODE: FORCE_MAJEURE / MANUAL / HERMES
- BASELINE SHA: `15ff86d2779e55e44a233eee45d6235a19baeafa`
- FINAL SHA: `d6a8de8a3176502c64c53cfca298ddb4cede12f4`
- PARENT SHA: `15ff86d2779e55e44a233eee45d6235a19baeafa`
- BRANCH: `aither-v2`

## 1. Changed paths
- `aither-v2/services/inference/k8s/vllm-qwen38-27b-w4a16-lab.yaml` (lab-манифест, reproducibility; lab удалён после теста)
- `docs/evidence/AITHER_QWEN38_W4A16_PREQUANTIZED_CANDIDATE_QUALIFICATION_R3.md`

## 2. Candidate provenance (Phase A)
- CANDIDATE_REPO: `philbert440/Qwen3.8-27B-W4A16-AWQ`
- CANDIDATE_REVISION: `7908d42a71077a5e4dc458f273682b12dfe384a0`
- BASE_MODEL: `Qwen/Qwen3.8-27B` (base_model_relation=quantized)
- LICENSE: apache-2.0
- ARCHITECTURE: `qwen3_5` (`Qwen3_5ForConditionalGeneration`) — совпадает с production FP8.
- QUANT_METHOD: compressed-tensors W4A16 (AWQ), BITS=4, GROUP_SIZE=128, ZERO_POINT=asymmetric (symmetric=false, zp int8), format=pack-quantized; vision-encoder исключён из квантования (ignore-список).
- REMOTE_CODE_REQUIRED: NO (архитектура в transformers 5.15.0).
- Chat-template SHA256 `c3cf9e34abf4f9e3…` — совпадает с production FP8.

## 3. Download / integrity
- Path: `/data/models/Qwen3.8-27B-W4A16-LAB` (n8 hostPath).
- TOTAL: 19,561,037,206 bytes (~19.56 GB), FILE_COUNT=14.
- Ключевые SHA256: `model.safetensors` 18,698,467,264 B (`15c5b070…`), `model-mtp.safetensors` 849,400,424 B (`90fa0e3e…`).
- Скачивание выполнялось curl с resume (первая попытка через huggingface_hub зависла и OOMKilled из-за default memory 512Mi LimitRange; исправлено явным memory 2–6Gi).

## 4. Static vLLM 0.27.1 compatibility
- `CompressedTensorsWNA16` scheme → `MarlinLinearKernel`; `get_min_capability()=75` («Turing and up»).
- TURING_SUPPORTED: YES (sm_75). TP2: YES. QWEN38 (qwen3_5): YES. AWQ/compressed-tensors: YES.
- (Исправление R2: «4-bit Marlin требует Ampere+» — неверно для vLLM 0.27.1.)

## 5. Startup / backend proof
- `Using MarlinLinearKernel for CompressedTensorsWNA16` (Worker_TP0+TP1).
- W4A16_ACTIVE: YES. ACTIVE_KERNEL: MarlinLinearKernel. TP=2. MAX_MODEL_LEN=65536. MAX_NUM_SEQS=1.
- Model loading: 8.84 GiB (vs FP8 14.46 GiB). KV cache: 8.38 GiB / 263,650 tokens. enforce-eager=YES (без CUDA Graph).

## 6. VRAM A/B
- A (FP8 prod): 19309 MiB used / 3193 MiB free (per GPU).
- B (W4A16): 19055 MiB used / 3447 MiB free.
- VRAM_FREE_GAIN: ~254 MiB/GPU — **WEAK** (<1 GiB). Выигрыш от меньших весов ушёл в расширение KV-cache.

## 7. Decode performance A/B (temperature=0, top_p=1)
- A: D128 9.23, D512 9.26, D2048 9.33 tok/s.
- B: D128 9.44, D512 9.48 tok/s (D2048 не замерен до лимита; тенденция ≈9.5).
- AGGREGATE_DECODE_GAIN ≈ +2.3% — **MARGINAL** (<10%).

## 8. Latency (A, production reference)
- A TTFT_p50 0.2523 s, A ITL_p50 0.1076 s. (B отдельно не замерен — decode покрыл throughput.)

## 9. Hard gates
- 8K/32K/60K: PASS. AUTO/FORCED/REQUIRED/no-tool tool: PASS.
- Quality (frozen corpus): Russian PASS, Linux/K8s PASS, Python PASS (с max_tokens=500 — иначе thinking съедает бюджет), Bash PASS, JSON PASS, reasoning/math PASS. MAJOR-регрессии нет.
- Consistency (10× deterministic): 10/10 идентичны. 100 sequential: 0 errors (428 s).
- 0 OOM, 0 unexpected restarts, 0 unexpected 5xx.

## 10. CUDA Graph retry headroom
- DELTA_FREE_VRAM ≈ 254 MiB/GPU → **NO** (маржинально; свободно те же ~3.4 GiB, что и у FP8).

## 11. Lab teardown + restore (mandatory)
- Lab Deployment/Service `vllm-qwen38-27b-w4a16-lab` удалены. n8 GPU освобождены.
- Qwen3-32B восстановлен (scale 0→1): Ready 1/1, restartCount 0, health 200, basic OK, AUTO tool PASS, 60K PASS, cpu requests=8/limits=8.
- Production Qwen3.8 (n7): Ready 1/1, restartCount 0, health 200, basic OK, AUTO tool PASS — не изменён.

## 12. Immutability / compliance
- QWEN3.8 production changed: NO. AGENT-DEEP routing changed: NO. QWEN3-32B Git manifest changed: NO. Portal/BFF/Identity/nginx/Gateway/frontend: NO. `.agent/*`: NO.
- AI_CODEX_USED: NO. AUTOMATED_RUNNER_USED: NO. SECRETS_EXPOSED: NO.

## 13. Conclusion
W4A16 на Turing sm_75 для Qwen3.8-27B **работает** (Marlin 4-bit, TP=2, 64K, tool/quality/stability без регрессий), но даёт **маржинальный выигрыш**: decode ≈ +2.3% (ниже порога 10%) и VRAM-выигрыш **WEAK** (~254 MiB/GPU — экономия весов перешла в KV-cache). Кандидат проходит hard-gates (qualified), но НЕ является compelling-заменой FP8 и НЕ подходит для CUDA-graph-retry (свободной VRAM по-прежнему ~3.4 GiB). Production-замена не авторизована.

## 14. C1 QUALIFICATION CLOSURE

Закрытие пробелов R3 выполнено задачей `AITHER-QWEN38-W4A16-R3-C1-QUALIFICATION-CLOSURE`.
Полный детальный evidence: `docs/evidence/AITHER_QWEN38_W4A16_R3_C1_QUALIFICATION_CLOSURE.md`.

- **B D2048**: измерен, median **9.587 tok/s** (runs 9.587/9.539/9.792, temperature=0, top_p=1).
- **Corrected aggregate**: A 9.292, B 9.502, gain **+2.26%** (MARGINAL).
- **B TTFT**: P50 **0.1680 s**. **B ITL**: P50 **0.1029 s** (TTFT −8.9%, ITL −2.6% vs A).
- **Streaming tool**: PASS (structured `get_current_weather` `{"city":"Moscow"}`, valid JSON,
  корректная реконструкция chunks, без parser corruption).
- **Multi-turn tool**: PASS (turn1 tool-call → tool result → turn2 корректно использует результат).
- **Consistency**: PRIOR 10 + ADDITIONAL 10 = TOTAL **20**, IDENTICAL **20/20**, PASS.
- **Full SHA256 manifest**: 14 файлов, 19,561,037,206 B — `docs/evidence/AITHER_QWEN38_W4A16_R3_SHA256.txt`.
- **Qwen3-32B FORCED after restore**: PASS (restore scale 0→1, FORCED tool call валиден).
- **Qwen3.8 60K after restore**: PASS (58,951 prompt tokens, корректный ответ, без OOM).

Примечание (независимая находка): Qwen3-32B на 60K контексте деградирует (`!!!!…`) — native
`max_position_embeddings=40960`, `rope_scaling=None`, при deployment-овере `max-model-len=65536`.
Это pre-existing ограничение конфигурации Qwen3-32B, вне scope C1, манифест не менялся.
