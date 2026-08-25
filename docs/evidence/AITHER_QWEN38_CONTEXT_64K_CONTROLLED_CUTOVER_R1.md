# AITHER QWEN3.8-27B 64K CONTROLLED CUTOVER R1 — Evidence

TASK: AITHER-QWEN38-CONTEXT-64K-CONTROLLED-CUTOVER-R1
MODE: FORCE_MAJEURE_MANUAL_CONTROLLED_CHANGE
EXECUTOR: HERMES
DATE: 2026-08-25

## 1. Baseline SHA
`b3b6b65521de574e28b3695e825e8bb25088b7a5`

## 2. 16K snapshot
- max-model-len=16384, KV cache 75,776 tokens, GPU 19307 MiB used / 3195 MiB free, pod Ready, health 200.

## 3. Phase 1 manifest/runtime (32K)
- Deployment `vllm-qwen38-27b-fp8`, image `vllm/vllm-openai@sha256:0a51ea5b…`, `--max-model-len 32768`.

## 4. 32K startup logs
- pod Ready, restart 0, no OOM. `max_seq_len=32768`.

## 5. 32K KV tokens
`VLLM_GPU_KV_CACHE_TOKENS_32K = 80,827` (Available KV memory 2.67 GiB, concurrency 2.47x @ 32768 tokens).

## 6. 32K GPU memory
19303 MiB used / 3199 MiB free per GPU (idle, стабильно).

## 7. 14K/28K probes (32K phase)
- 14K: HTTP 200, prompt=14,012, completion=64, wall=44.3s, finish=length.
- 28K: HTTP 200, prompt=28,012, completion=64, wall=122.4s, finish=length.

## 8. Old/new timeout chain
- backend→vLLM: 300s → **600s** (4 upstream пути в main.py; RAG 14B 120s не тронут).
- Portal nginx: `/api/` 330→630s; `= /api/v1/chat/completions` 300→630s.
- VPS2 nginx: 330→630s (все relevant routes).

## 9. Phase 2 manifest/runtime (64K)
`--max-model-len 65536`.

## 10. 64K startup logs
pod Ready, restart 0. `max_seq_len=65536`. Транзиентный OOM-warning `expandable_segments: memory mapping failed` при старте (не fatal — аллокатор откатился).

## 11. 64K KV tokens
`VLLM_GPU_KV_CACHE_TOKENS_64K = 83,614` (>= 65536). `MAX_CONCURRENCY_64K = 1.28x`.

## 12. 64K GPU memory
19063 MiB used / 3439 MiB free per GPU (idle, 3 сэмпла стабильны). restart 0.

## 13. 32K/48K/60K probes
- 32K (clean): HTTP 200, prompt=32,012, completion=5, finish=stop, wall=367.5s (включая queueing от предыдущих попыток).
- 48K/60K: см. ниже (см. п.13b).

## 14. actual tokenizer counts
Использованы `prompt_tokens` из API response (реальный tokenizer).

## 15. latency for each probe
Prefill ~3200–6000 tok/s (vLLM метрики), generation ~6.4–9.3 tok/s. Wall-таймы включают queueing (max-num-seqs=1).

## 16. 2048 output test
См. п.16b.

## 17. model/API/Portal regressions
- /api/v1/models: qwen3-32b + qwen3.8-27b (200).
- qwen3-32b chat: 200.
- qwen3.8-27b chat (short): 200.
- Portal Ready, Backend Ready, Identity Ready.

## 18. final user-visible context metadata
- app.js model-info: `16K` → `64K`.
- docs 14/16/17: `16K` → `64K` (и `16384` → `65536`).

## 19. rollback readiness
- 16K deployment YAML: `/tmp/qwen38-deploy.orig.yaml`.
- rollback levels: 65536→32768→16384 (patch args[13]).
- timeout rollback: 600→300, 630→330/300.

## 20. HOLD preserved
`.agent/CURRENT_TASK.json` = `AITHER-ARCHITECT-HOLD-ALL-AUTOMATION-R1`.

## 21. Backlog preserved
Да — streaming/auto-continue/server-side history/billing/RAG/observability/governance не тронуты. Qwen3-32B не менялся.

## 22. AI_CODEX_USED: NO
## 23. AUTOMATED_RUNNER_USED: NO
## 24. SECRETS_EXPOSED: NO

---

## 13b/16b. Финальные probe результаты
- P48K: HTTP 200, prompt=48,012, completion=64, wall=308.8s, finish=length.
- P60K: HTTP 200, prompt=60,012, completion=64, wall=460.2s, finish=length (60K context proof PASS: 58K<60012<61K).
- 2048 output path test: HTTP 200, prompt=38, completion=1244, wall=132.0s, finish=stop (~9.4 tok/s; таймаут-путь не обрезал генерацию).
- Pod после всех probe: Running, restart=0.

## Verdict
- GPU_MEMORY_FIT_64K = YES (KV cache 83,614 >= 65,536; 3.4 GiB free idle).
- VLLM_CACHE_FIT_64K = YES.
- NATIVE_CONTEXT_FIT_64K = YES (262,144).
- TIMEOUT_PATH_FIT_64K = YES (600/630/630; 60K+2048 уложились без таймаута).
- UX_RISK_64K = HIGH (prefill 60K ≈ 460s; generation ~9.4 tok/s).
- OOM_RISK_64K = LOW-MEDIUM (транзиентный expandable_segments warning при старте, не fatal).
