# AITHER QWEN38 GGUF AD-Q4 LLAMACPP FULL QUALIFICATION R2 — Evidence

- TASK: `AITHER-QWEN38-GGUF-AD-Q4-LLAMACPP-FULL-QUALIFICATION-R2`
- EXECUTOR: HERMES
- MODE: FORCE_MAJEURE / MANUAL / HERMES
- BASELINE SHA: `3b5c6f4b93fa4488742b1e0d19ac35894d30e21a`
- PARENT SHA: `53e8326246e856c9bf563c07b887684e372bd860`
- BRANCH: `aither-v2`
- FINAL SHA: `<after-commit>`

## 0. Deferred technical debt (recorded, NOT executed)

`AITHER-QWEN38-GGUF-LLAMACPP-R1-C1-QUALIFICATION-CLOSURE` = **DEFERRED**.
Recorded in canonical `aither-v2/docs/stage10/technical-review/TECHNICAL-DEBT-REGISTER.md`.
R1 Q5 evidence was NOT modified to pretend the gaps are closed.

## 1. Provenance (re-resolved at execution)

- HF_REPO: `AtomicChat/Qwen3.8-27B-GGUF`
- HF_REVISION: `ca10ebceb1887be9d33b838770a36b39d75a8a4c`
- Q4 FILE: `Qwen3.8-27B-AD-Q4_K_M.gguf`
- Q4 BYTES: **17,120,781,792** (~17.1 GB)
- Q4 SHA256: `9f21564b0c962fd397509672a4a6d11a008c6b80cc6573295bb562832492abf0` (matches remote OID)
- BASE_MODEL: `Qwen/Qwen3.8-27B`, QUANT: AD-Q4_K_M (imatrix)
- PUBLISHED KL: 0.01126, TOP-1: 95.59% (matches task snapshot)
- Static GGUF: arch `qwen35`, context_length 262144, block_count 65, embedding 5120,
  head 24/kv 4, rope.freq_base 10000000, `nextn_predict_layers=1` (MTP present, OFF).

## 2. llama.cpp runtime (SAME digest as R1 — isolates quantization variable)

- IMAGE DIGEST: `sha256:150b59966fb5b2cb1a8fa9d226267c56ebd22c520c7b3640331cde87f3c4fb01`
- VERSION: `0.3.0-dev (build 10666, commit 4e97ac86e)`; CUDA PASS, Turing sm_75 PASS.
- Lab manifest uses immutable digest (R2 requirement), NOT floating tag.

## 3. Lab deployment (isolated, n8)

- `llamacpp-qwen38-27b-gguf-q4-lab`, alias `qwen3.8-27b-gguf-ad-q4-lab`, ClusterIP only.
- Args: `--ctx-size 65536 --n-gpu-layers 99 --split-mode layer --tensor-split 1,1 --parallel 1 --jinja`.
- MTP OFF proof: `blk.64.nextn.*` + `blk.64.ffn_up.weight` ignored at load. Speculation OFF.
- Both GPUs active (layer split). CPU offload: NO. GPU0 ~10.15 GiB / GPU1 ~10.72 GiB used.

## 4. FP8 reference recheck (n7, untouched)

- D128 9.206 / D512 9.249 / D2048 9.273 → **aggregate 9.243** (vs R1 9.265, −0.24%, no drift).
- TTFT P50 0.1758 s, ITL P50 0.1078 s. 60K semantic 3/3 PASS.

## 5. Q4 core decode (short context ~95 tok, temperature=0 top_p=1)

| len | run1 | run2 | run3 | median |
|---|---|---|---|---|
| D128 | 23.541 | 22.273 | 23.614 | **23.541** |
| D512 | 24.225 | 23.830 | 24.232 | **24.225** |
| D2048 | 24.335 | 24.210 | 24.331 | **24.331** |

- **Q4_BASE_AGGREGATE = 24.03 tok/s**
- GAIN vs FP8 = +160%. GAIN vs Q5 (20.39) = **+17.9%** → Q4_STRONG_SPEED_GAIN (>+10%).

## 6. Mandatory context-scaling decode matrix (27 runs, all 9 cells complete)

| Context | D128 | D512 | D2048 | aggregate |
|---|---|---|---|---|
| 8K | 23.95 | 23.83 | 23.75 | 23.84 |
| 32K | 22.21 | 22.09 | 22.01 | 22.10 |
| 60K | 20.88 | 20.75 | 20.69 | 20.77 |

(all cells cv ≤0.1%; 60K uses 1635-paragraph prompt = 58,948 tokens to stay under 64K limit)

Context penalties:
- D128: 8K→32K −7.3%, 8K→60K −12.8%, 32K→60K −6.0%
- D512: 8K→32K −7.3%, 8K→60K −12.9%, 32K→60K −6.1%
- D2048: 8K→32K −7.3%, 8K→60K −12.9%, 32K→60K −6.0%

**CONTEXT_SENSITIVITY_AVERAGE (8K→60K) = −12.9% → MODERATE_CONTEXT_PENALTY**.

## 7. Prefill / TTFT / ITL

- Q4 TTFT P50 (short context): 0.2402 s. ITL P50: 0.0409 s (= 1/24.4, consistent with decode).
- Un-cached prefill: 8K ≈ 9.1 s (~988 tok/s), 32K ≈ 30.9 s (~876 tok/s), 60K ≈ 71.4 s (~825 tok/s).
  (llama.cpp prefix-caches identical prompts → subsequent runs show ms-level prompt_ms; decode unaffected.)

## 8. Long-context semantic (3 reps per context, distinct markers, all 3 facts required)

- 8K: 3/3 PASS (ALPHA/BETA/GAMMA, DELTA/EPSILON/ZETA, ETA/THETA/IOTA all retrieved)
- 32K: 3/3 PASS
- 60K: 3/3 PASS (58,999 tokens, no garbage, no OOM)

## 9. Tool calling (full suite)

- basic PASS, NO-TOOL PASS, AUTO PASS, FORCED PASS, REQUIRED PASS
- STREAMING TOOL PASS, MULTI-TURN TOOL PASS
- TOOL ERROR RECOVERY PASS (turn1 `get_current_weather` Xyzzyville → error → turn2 graceful
  apology + spelling suggestion). NOTE: initial harness used max_tokens=256 which the reasoning
  phase consumed before the tool call; re-run at max_tokens=512 → correct tool call + graceful
  error handling. This is a harness artifact, not a model defect.

## 10. Quality A/B + quantization sensitivity

- Quality (8 domains): russian/linux/k8s/python/json/math/reasoning/instruction PASS; bash
  heuristic false (identical to FP8/Q5 reference, content acceptable). **No major regression.**
- Quant sensitivity: **21/22 PASS** (only `date_math` returned empty — reasoning phase consumed
  max_tokens; not a systematic quantization loss).

## 11. Consistency + stability

- Consistency: **20/20 identical** (sha256 61db2d39…).
- Stability: **100 sequential** (basic/Russian/JSON/AUTO/FORCED/D2048/8K/32K/60K), 2055.8 s.
  unexpected 5xx=0, OOM=0, restarts=0, malformed=0, tool corruption=0.
  (`empty=10` = the 10× "Say exactly: OK" prompts with max_tokens=64 consumed by thinking phase —
  harness artifact, not instability.)

## 12. VRAM/RAM

| context | GPU0 used | GPU1 used |
|---|---|---|
| idle | ~10.15 GiB | ~10.72 GiB |
| 60K | ~10.18 GiB | ~10.74 GiB |

- vs Q5 (~11.6 / 12.1 GiB): **Q4 frees ~1.4 GiB/GPU** (smaller weights).
- Host RAM ≈ 28 GiB used (weights on GPU).

## 13. Q4 vs Q5 decision

Q4: +17.9% decode, +18% at 60K still, all tools PASS, 3/3 semantic, 20/20 consistency, clean
stability. BUT published KL 0.01126 (vs Q5 0.00419) and top-1 95.59% (vs 97.34%) show a real,
if modest, quantization-quality gap; my functional suite shows no major regression but the
published metrics indicate a measurable difference under real workload.

**DECISION: Q4_AND_Q5_REQUIRE_PRODUCTION_LIKE_AB** — both are technically qualified
(Q4 = speed-optimal, Q5 = quality-optimal); a production-like A/B is needed to trade off the
+18% decode gain against the higher quantization loss.

MTP_FUTURE_TEST: MAYBE (stable non-spec baseline, ~1.4 GiB/GPU extra free vs Q5, but upstream
MTP risk noted — separate Architect authorization required).

## 14. Teardown + restore

- Q4 lab removed, service removed, n8 GPUs released (0 MiB / 0%).
- Q4 + Q5 checkpoints kept at `/data/models/Qwen3.8-27B-GGUF-LAB/`.
- Qwen3-32B restored 0→1: Ready 1/1, health 200, restartCount 0, basic/AUTO/FORCED/8K PASS.
- Production Qwen3.8 (n7): Ready, restartCount 0, basic/AUTO/60K PASS, agent-deep unchanged.

## 15. Compliance

- QWEN3.8 production changed: NO. QWEN3-32B manifest changed: NO. Portal/BFF/Identity/nginx: NO.
- `.agent/*`: NO. Direct DB writes: NO. Model weights not committed.
- AI_CODEX_USED: NO. AUTOMATED_RUNNER_USED: NO. SECRETS_EXPOSED: NO.
