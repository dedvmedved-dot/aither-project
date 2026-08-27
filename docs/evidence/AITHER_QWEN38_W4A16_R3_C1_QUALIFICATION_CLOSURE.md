# AITHER QWEN38 W4A16 R3-C1 QUALIFICATION CLOSURE — Evidence

- TASK ID: `AITHER-QWEN38-W4A16-R3-C1-QUALIFICATION-CLOSURE`
- EXECUTOR: HERMES
- MODE: FORCE_MAJEURE / MANUAL / HERMES
- BASELINE SHA: `d6a8de8a3176502c64c53cfca298ddb4cede12f4`
- PARENT SHA: `d6a8de8a3176502c64c53cfca298ddb4cede12f4`
- BRANCH: `aither-v2`

This closure addresses the mandatory gaps left by R3
(`AITHER-QWEN38-W4A16-PREQUANTIZED-CANDIDATE-QUALIFICATION-R3`). R3 performed the main
qualification; this task closes the specific missing gates and corrects R3's `FINAL SHA`.

---

## 1. Checkpoint integrity (full SHA256 manifest)

- Candidate: `philbert440/Qwen3.8-27B-W4A16-AWQ`
- Revision: `7908d42a71077a5e4dc458f273682b12dfe384a0`
- Local path: `/data/models/Qwen3.8-27B-W4A16-LAB` (n8 hostPath)
- FILE_COUNT: **14** (matches expectation)
- TOTAL_BYTES: **19,561,037,206** (~19.56 GB, matches expectation)
- Full deterministically-sorted SHA256 manifest (all 14 files): see
  `docs/evidence/AITHER_QWEN38_W4A16_R3_SHA256.txt`

Key hashes match R3's recorded values exactly:

| file | sha256 (prefix) |
|---|---|
| model.safetensors (18,698,467,264 B) | `15c5b070…` |
| model-mtp.safetensors (849,400,424 B) | `90fa0e3e…` |
| chat_template.jinja | `c3cf9e34…` |

Result: **CHECKPOINT_INTEGRITY = PASS** (no mismatch, no re-download required).

## 2. Startup / backend proof (re-verified on running lab)

- `Using MarlinLinearKernel for CompressedTensorsWNA16` — Worker_TP0 + Worker_TP1.
- Engine config: `quantization=compressed-tensors`, `dtype=torch.float16`,
  `tensor_parallel_size=2`, `max_seq_len=65536`, `max_num_seqs=1`,
  `gpu_memory_utilization=0.9`, `enforce_eager=True`.
- `Enforce eager set, disabling torch.compile and CUDAGraphs` — CUDAGraph memory **0.0 GiB**.
- reasoning_parser=`qwen3`, tool_call_parser=`qwen3_xml`, enable_auto_tool_choice=True.
- W4A16_ACTIVE: **YES**. ACTIVE_KERNEL: **MarlinLinearKernel**. TP=2. 64K. max-num-seqs=1.
- KV cache 8.38 GiB / 263,650 tokens. Model weights ~9.9 GiB consumed per GPU.

## 3. A reference (production FP8, n7) — before maintenance

Decode D2048 (temperature=0, top_p=1), all runs:

| run | wall_s | completion_tokens | tps |
|---|---|---|---|
| 1 | 221.024 | 2048 | 9.266 |
| 2 | 218.069 | 2048 | 9.392 |
| 3 | 218.174 | 2048 | 9.387 |

**A_D2048_TPS (median) = 9.387**. Drift vs R3 reference (9.33): **+0.6%** (< 10%, no drift).

Streaming latency (>=5 runs):

| run | ttft_s | itl_s |
|---|---|---|
| 1 | 0.2073 | 0.1076 |
| 2 | 0.1857 | 0.1078 |
| 3 | 0.1844 | 0.1056 |
| 4 | 0.1845 | 0.1057 |
| 5 | 0.1844 | 0.1056 |

**A_TTFT_P50 = 0.1845 s**. **A_ITL_P50 = 0.1057 s** (R3 reference ITL ≈ 0.1076 s, ~2% off).

## 4. B D2048 (W4A16 lab, n8) — the missing measurement

Decode D2048 (temperature=0, top_p=1), all runs:

| run | wall_s | completion_tokens | tps |
|---|---|---|---|
| 1 | 213.620 | 2048 | 9.587 |
| 2 | 214.697 | 2048 | 9.539 |
| 3 | 209.147 | 2048 | 9.792 |

**B_D2048_TPS (median) = 9.587**. No extrapolation — measured directly.

## 5. B TTFT / ITL (W4A16 lab, n8) — the missing latency measurements

Streaming (>=5 runs):

| run | ttft_s | itl_s |
|---|---|---|
| 1 | 0.1975 | 0.1033 |
| 2 | 0.1680 | 0.1022 |
| 3 | 0.1666 | 0.1029 |
| 4 | 0.1684 | 0.1028 |
| 5 | 0.1671 | 0.1047 |

**B_TTFT_P50 = 0.1680 s**. **B_ITL_P50 = 0.1029 s**.

- TTFT_CHANGE_PERCENT = (0.1680 − 0.1845) / 0.1845 = **−8.9%** (W4A16 faster).
- ITL_CHANGE_PERCENT = (0.1029 − 0.1057) / 0.1057 = **−2.6%** (W4A16 faster).

## 6. Corrected aggregate (no extrapolation)

- A: D128 = 9.23, D512 = 9.26, D2048 = 9.387 → **A_AGGREGATE_TPS = 9.292** (mean).
- B: D128 = 9.44, D512 = 9.48, D2048 = 9.587 → **B_AGGREGATE_TPS = 9.502** (mean).
- AGGREGATE_GAIN = (9.502 − 9.292) / 9.292 = **+2.26%** → **MARGINAL** (< 10%).

## 7. Streaming tool (deterministic, forced)

- Model tool call reconstructed from streamed deltas:
  `get_current_weather` arguments `{"city": "Moscow"}`.
- Valid JSON: **YES**. Chunk reconstruction: **correct**. Parser corruption: **none**.
- **STREAMING TOOL = PASS**.

## 8. Multi-turn tool (deterministic)

- Turn 1 (forced tool_choice): model returned `get_current_weather` for Moscow.
- Tool result supplied: `{"city":"Moscow","temperature":5,"unit":"celsius","condition":"clear"}`.
- Turn 2: model used the result — "The current weather in Moscow is clear skies with a
  temperature of 5°C."
- **MULTI-TURN TOOL = PASS**.

## 9. Consistency (deterministic, temperature=0)

- PRIOR (R3): 10 runs, 10/10 identical.
- ADDITIONAL (C1): 10 runs, all identical (sha256 `183338b09e…`, 473 chars each).
- TOTAL: **20**. IDENTICAL: **20/20** (R3 10/10 + C1 10/10).
- **CONSISTENCY = PASS**.

## 10. Candidate smoke before teardown

- basic: PASS ("The capital of France is Paris.").
- AUTO tool: PASS (model chose `get_current_weather` for Paris).
- FORCED tool: PASS (`get_current_weather` for Moscow, valid args).
- 60K context: PASS (58,951 prompt tokens, correct final-sentence retrieval, no OOM).

## 11. Teardown

- Lab Deployment/Service `vllm-qwen38-27b-w4a16-lab` deleted.
- **LAB_REMOVED = YES**. **N8_GPU_RELEASED = YES** (both GPUs 0 MiB used, 0% util).
- Checkpoint `/data/models/Qwen3.8-27B-W4A16-LAB` **kept** (not deleted).

## 12. Restore Qwen3-32B (n8)

- Scale 0→1. Pod Ready 1/1, restartCount 0, health 200.
- Startup: `Application startup complete`, `quantization=awq`, TP=2, `tool_call_parser=hermes`,
  max_model_len=65536, max_num_seqs=4.
- basic: PASS. AUTO tool: PASS. FORCED tool: PASS (`get_current_weather` Moscow, valid args).
- **FORCED after restore = PASS** (the R3 gap).

⚠️ **60K context = FAIL (pre-existing limitation, not a restore regression).** At 58,911
prompt tokens Qwen3-32B returned garbage (`!!!!…`). Root cause: the model checkpoint has
`max_position_embeddings=40960` and `rope_scaling=None`, while the deployment overrides
`max-model-len=65536`. vLLM logs a pre-existing warning: "User-specified max_model_len (65536)
is greater than the derived max_model_len (max_position_embeddings=40960)". This is the
long-standing Qwen3-32B configuration, unchanged by this task (Qwen3-32B Git manifest untouched),
and out of C1 scope. The restore itself is healthy; the 60K limitation is independent of the
W4A16 candidate qualification.

## 13. Production Qwen3.8 (n7) final check

- Pod Ready 1/1, restartCount 0, health 200 — unchanged throughout.
- basic: PASS. AUTO tool: PASS.
- **60K context: PASS** (58,951 prompt tokens, correct answer, no OOM).
- Routing: `AGENT_MODEL_ALIASES["agent-deep"] = "qwen3.8-27b"` confirmed (deterministic map,
  no LLM router). **agent-deep → qwen3.8-27b** unchanged.

## 14. Immutability / compliance

- QWEN3.8 production changed: NO. AGENT-DEEP routing changed: NO.
- QWEN3-32B Git manifest changed: NO. Portal/BFF/Identity/nginx/Gateway/frontend: NO.
- `.agent/*`: NO.
- AI_CODEX_USED: NO. AUTOMATED_RUNNER_USED: NO. SECRETS_EXPOSED: NO.

## 15. Conclusion

C1 closed all R3 gaps with real runtime evidence: B D2048 (9.587 tok/s), B TTFT/ITL
(0.1680 s / 0.1029 s), streaming tool PASS, multi-turn tool PASS, consistency 20/20,
full 14-file SHA256 manifest, Qwen3-32B FORCED-after-restore PASS, production Qwen3.8
60K-after-restore PASS. Corrected aggregate gain **+2.26%** (MARGINAL, < 10%) and VRAM gain
remains WEAK (~254 MiB/GPU). The candidate passes hard gates but is NOT a compelling FP8
replacement. One independent finding: Qwen3-32B cannot actually serve 60K context (native
40960, no rope scaling) — a pre-existing limitation outside this task's scope and unchanged
by it.
