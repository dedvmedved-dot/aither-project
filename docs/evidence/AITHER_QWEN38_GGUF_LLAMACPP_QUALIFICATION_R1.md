# AITHER QWEN38 GGUF LLAMACPP QUALIFICATION R1 — Evidence

- TASK: `AITHER-QWEN38-GGUF-LLAMACPP-QUALIFICATION-R1`
- EXECUTOR: HERMES
- MODE: FORCE_MAJEURE / MANUAL / HERMES
- BASELINE SHA: `53e8326246e856c9bf563c07b887684e372bd860`
- PARENT SHA: `53e8326246e856c9bf563c07b887684e372bd860`
- BRANCH: `aither-v2`
- FINAL SHA: `<after-commit>`

---

## 1. Remote provenance (verified)

- HF_REPO: `AtomicChat/Qwen3.8-27B-GGUF`
- HF_REVISION: `ca10ebceb1887be9d33b838770a36b39d75a8a4c` (lastModified 2026-08-18)
- GGUF_FILE: `Qwen3.8-27B-AD-Q5_K_M.gguf`
- REMOTE_BYTES: **20,232,512,992** (~20.2 GB)
- REMOTE_HASH (Xet/LFS OID sha256): `32b2b7fcb2a1686dd2737304c86f31ed514d4a705e26b8e409d9bb9657434403`
- LOCAL_SHA256: `32b2b7fcb2a1686dd2737304c86f31ed514d4a705e26b8e409d9bb9657434403` → **MATCH** (byte-identical)
- BASE_MODEL: `Qwen/Qwen3.8-27B` (base_model_relation=quantized, quantized_by=AtomicChat)
- LICENSE: cardData license=None (Qwen family base; not redistributed)
- PUBLISHED METRICS: AD-Q5_K_M = 20.2 GB, KL divergence 0.00419, top-1 97.34% (matches task snapshot)

## 2. Static GGUF inspection (read-only parser)

- GGUF version: 3, tensors: 866, kv: 44
- `general.architecture` = **qwen35** ✓ (recognized)
- `qwen35.context_length` = **262144** (native 256K — 60K is well within native, no YaRN needed)
- `qwen35.block_count` = 65, `embedding_length` = 5120, head_count 24 / kv 4
- `qwen35.rope.freq_base` = 10000000.0 (10M, matches Qwen3.8 FP8)
- `qwen35.nextn_predict_layers` = **1** (MTP head present — kept OFF)
- `general.quantization_version` = 2; tensor types: f32×360, q8_0×131, q4_K×1, q5_K×188, q6_K×186
- chat_template: Jinja, vision-aware, with `<tool_call>`/`</tool_call>`, `<tool_response>`, `<think>` tokens

## 3. llama.cpp runtime provenance

- IMAGE: `ghcr.io/ggml-org/llama.cpp:server-cuda` (floating tag; pinned by digest in manifest)
- IMMUTABLE DIGEST: `sha256:150b59966fb5b2cb1a8fa9d226267c56ebd22c520c7b3640331cde87f3c4fb01`
- VERSION: `0.3.0-dev (build 10666, commit 4e97ac86e)` — `system_fingerprint: b10666-4e97ac86e`
- CUDA BACKEND: active — 2× Quadro RTX 6000, compute capability 7.5 (Turing sm_75) → PASS
- NOTE: task snapshot tag `server-cuda13` no longer exists; current tag scheme is `server-cuda-bNNNN`
  (latest pinned ≈ b7549) with floating `server-cuda` = build 10666. The first attempted build
  (b4819, Feb 2025) does NOT recognize qwen35; build 10666 (v0.3.0-dev) DOES.

## 4. Lab deployment (isolated, n8)

- Deployment: `llamacpp-qwen38-27b-gguf-lab` (ClusterIP only, no ingress/routing/alias)
- Served alias: `qwen3.8-27b-gguf-ad-q5-lab`
- Node: `bootsman-k8s-clnt01-n8-gpu`, 2× RTX 6000, topology GPU0<->GPU1 = SYS
- Args: `--ctx-size 65536 --n-gpu-layers 99 --split-mode layer --tensor-split 1,1 --parallel 1 --jinja`
- Startup proof: n_slots=1, n_ctx_slot=65536, `llama_server: model loaded`, listening :8000.
- **MTP OFF proof**: startup log shows MTP/nextn tensors ignored —
  `blk.64.nextn.eh_proj.weight`, `blk.64.nextn.enorm/hnorm/shared_head_norm.weight`,
  `blk.64.ffn_up.weight` — all "unused tensor ... ignoring". No `--spec-type draft-mtp`, no draft model.
- SPECULATIVE DECODING: OFF (default, no spec flags set).
- CPU offload: NONE (`-ngl 99` = full offload).

## 5. GPU placement

- GPU0 idle: 11,645 MiB used / 23,040 total. GPU1 idle: 12,123 MiB used.
- Both GPUs active (layer split). No single-GPU or CPU fallback. **MULTI_GPU_ACTIVE = YES**.
- Host RAM: 28 GB used / 754 GB total.

## 6. OpenAI-compatibility

- `GET /v1/models` → alias `qwen3.8-27b-gguf-ad-q5-lab` ✓
- `POST /v1/chat/completions` non-stream ✓, stream ✓ (SSE, delta.content + delta.reasoning_content)
- finish_reason + usage metadata ✓ → **OPENAI API = PASS**

## 7. FP8 reference A (n7, re-verified, temperature=0 top_p=1)

- D128 9.171 / D512 9.340 / D2048 9.283 → **aggregate 9.265 tok/s**
- TTFT P50 **0.1755 s**, ITL P50 **0.1081 s**
- 8K PASS, 32K PASS, 60K PASS (58998 tokens, PELICAN-3382 retrieved)
- basic/AUTO/FORCED/REQUIRED/no-tool/streaming/multi-turn: PASS
- Quality: 7/8 (bash heuristic false, content acceptable). No drift vs historical (agg 9.292, +0.3%).

## 8. W4A16 accepted reference (secondary)

- Aggregate 9.502 tok/s, TTFT 0.1680 s, ITL 0.1029 s, gain vs FP8 +2.26%.

## 9. GGUF / llama.cpp benchmark B

Decode (temperature=0, top_p=1, all runs):

| len | run1 | run2 | run3 | median |
|---|---|---|---|---|
| D128 | 20.029 | 20.079 | 20.070 | **20.070** |
| D512 | 20.522 | 20.253 | 20.523 | **20.522** |
| D2048 | 20.588 | 20.491 | 20.585 | **20.585** |

- **B_GGUF_AGGREGATE = 20.39 tok/s**
- GAIN_VS_FP8 = (20.39 − 9.265)/9.265 = **+120%**
- GAIN_VS_W4 = (20.39 − 9.502)/9.502 = **+115%**
- Latency: TTFT P50 **0.2407 s** (+37% vs FP8 0.1755 — slower prefill), ITL P50 **0.0484 s** (−55% vs FP8 — 2.2× faster decode)
- Prompt processing (from `timings`): short ≈ 351 tok/s, 60K ≈ 766 tok/s (prefill+decode 80.0s for 58998 tokens)

## 10. Long context (semantic retrieval, markers begin/middle/end)

- 8K: PASS (7990 tok, PELICAN-3382, 12.6 s)
- 32K: PASS (31606 tok, PELICAN-3382, 39.2 s)
- 60K: PASS (58998 tok, PELICAN-3382, 80.0 s) — no garbage, no repeated punctuation, no OOM

## 11. Tool calling (hard gate)

- basic PASS, NO-TOOL PASS, AUTO PASS, FORCED PASS, REQUIRED PASS
- STREAMING TOOL PASS (reconstructed `get_current_weather` `{"city":"Moscow"}`, valid JSON)
- MULTI-TURN TOOL PASS (turn2 used result: "clear, 5°C")

## 12. Quality A/B (frozen corpus)

- Russian PASS, Linux/K8s PASS, Python PASS, Bash (heuristic false, content ok), JSON PASS,
  math PASS, instruction PASS → **no major regression** (bash false identical to FP8 reference).

## 13. Deterministic consistency

- temperature=0, 20 runs → **20/20 identical** (sha256 `a4d75bae…`), CONSISTENCY=PASS.

## 14. Stability (100 sequential mixed)

- Mix: basic / Russian / code / JSON / AUTO / FORCED / 8K / 32K / 60K.
- Total 1329.4 s. unexpected 5xx=0, OOM=0, restarts=0, malformed=0, tool corruption=0 → **PASS**.

## 15. VRAM/RAM profile

- Idle: GPU0 11.6 GiB / GPU1 12.1 GiB used. 60K: GPU0 11.7 GiB / GPU1 12.1 GiB (KV pre-allocated).
- vs FP8 vLLM (~19 GiB/GPU) → GGUF frees ~7 GiB/GPU at same 64K context.
- Host RAM at 60K: 28 GiB used (weights on GPU).

## 16. Classification

- PERFORMANCE CLASS: **MAJOR_WIN** (+120% aggregate decode vs FP8).
- AD_Q4_NEXT_TEST: **YES** (Q5 shows ≥10% gain; llama.cpp tool/long-context compatibility full;
  AD-Q4 could plausibly be faster still — ChatGPT decides R2).
- MTP_FUTURE_TEST: **MAYBE** (stable non-spec baseline; ~7 GiB/GPU free VRAM headroom; but upstream
  MTP allocation issues noted in task — separate Architect authorization required).

## 17. Teardown + restore

- LAB_REMOVED=YES, LAB_SERVICE_REMOVED=YES, N8_GPUS_RELEASED=YES (0 MiB / 0% after teardown).
- GGUF checkpoint kept at `/data/models/Qwen3.8-27B-GGUF-LAB/` (not deleted).
- Qwen3-32B restored 0→1: Ready 1/1, health 200, restartCount 0, basic/AUTO/FORCED/8K/32K PASS.
  (Known pre-existing 60K defect NOT re-tested as required — out of scope.)
- Production Qwen3.8 (n7): Ready 1/1, restartCount 0, health 200, basic/AUTO PASS, 60K PASS (from
  reference). agent-deep → qwen3.8-27b unchanged.

## 18. Immutability / compliance

- Qwen3.8 production changed: NO. Qwen3-32B Git manifest changed: NO.
- agent-deep / agent-fast routing changed: NO. Portal/BFF/Identity/nginx/Gateway: NO.
- `.agent/*`: NO. Direct DB writes: NO. Model weights not committed.
- AI_CODEX_USED: NO. AUTOMATED_RUNNER_USED: NO. SECRETS_EXPOSED: NO.
