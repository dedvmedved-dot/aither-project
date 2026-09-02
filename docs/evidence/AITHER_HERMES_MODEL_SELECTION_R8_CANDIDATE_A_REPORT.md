# Aither — R8 Candidate A Report

TASK: `AITHER-HERMES-AGENT-MODEL-SELECTION-R8`
CANDIDATE: A
MODEL: `NousResearch/Hermes-4.3-36B`
MODEL REVISION: `3899db2b6c4b35f16bde3b570bb7dd2775d56161`
QUANTIZATION: Q4_K_M GGUF (sha256 `17823599694fa3503ef54bf748d5078c6ce881f4d01616cafa255dc05d215a08`)
BACKEND: llama.cpp
BACKEND VERSION: 0.3.0-dev (build 10666, commit 4e97ac86e)
IMAGE DIGEST: `sha256:150b59966fb5b2cb1a8fa9d226267c56ebd22c520c7b3640331cde87f3c4fb01`

## Baseline / maintenance

- BASELINE: `440b9836c4d745b5f801fd3f0e9391dfda9c8bdf`
- ARCHITECT_TEMPORARY_N7_MAINTENANCE_AUTHORIZED: YES
- QWEN38_TEMP_SCALE_DOWN: 1_TO_0
- PRE_MAINTENANCE_QWEN38_HEALTH: PASS (Ready, restart 0, canonical imageID)
- ACTIVE_TRAFFIC_GATE: PASS (idle, 200/200 logs = /health probes)
- GPU RELEASE: PASS (both RTX 6000 free after scale-down)
- MEMORY_FEASIBILITY_64K: PASS (Q4_K_M 21.76 GB + Q8_0 KV 64K ≈ 30 GB < 44 GB free)

## Preflight

- PREFLIGHT: PASS (26 deterministic tool calls; JSON validity 26/26, unknown 0, unsafe 0, malformed 0, HTTP5xx 0)

## R7-C1 benchmark results (unchanged semantics)

| Metric | FULL F0 | FULL F1 | ROUTED F0 | ROUTED F1 |
|---|---|---|---|---|
| TASK_SUCCESS | 8.0% | 6.0% | 6.0% | 6.0% |
| ROOT_CAUSE_CORRECT | 78.0% | 78.0% | 76.0% | 76.0% |
| EVIDENCE_DISCOVERY (per-scenario avg) | 23.0% | 23.0% | 21.7% | 21.7% |
| FINAL_SCHEMA_VALID | 98.0% | 98.0% | 98.0% | 98.0% |

Tool metrics (evidence-ID, task-defined global ratios):

| Metric | ALL | FULL | ROUTED |
|---|---|---|---|
| REQUIRED_EVIDENCE_DISCOVERY | 31.5% | 27.4% | 24.7% |
| TOOL_PRECISION | 8.0% | 7.6% | 8.3% |
| TOOL_RECALL | 31.5% | 27.4% | 24.7% |
| TOOL_F1 | 12.7% | 11.9% | 12.5% |
| IRRELEVANT_CALL_RATE | 92.1% | 92.4% | 91.7% |
| DUPLICATE_CALL_RATE | 16.6% | 20.9% | 10.7% |
| ERROR_RECOVERY_RATE | 30.6% | 26.5% | 19.6% |

JSON_TOOL_ARGS_VALID: 98.2% (FULL) / 97.5% (ROUTED)
HALLUCINATED_TOOL_RATE: 0%
UNSAFE_ACTION_RATE: 0%
HTTP_5XX: 0

## Long context

- 56K: 0/5 PASS
- 58K: 0/5 PASS
- 60K: 0/3 PASS
- All 13 cases root_correct=False; token counts within target; markers verified.

## Performance (secondary)

- TTFT: ~90–135 ms
- ITL: ~51 ms
- decode tok/s: ~19.4
- prompt tok/s: ~211–252
- VRAM: 2× RTX 6000, Q4_K_M + Q8_0 KV

## Stability

- 150 SEQUENTIAL: NOT_RUN (functional hard gates FAIL)

## Comparison vs Qwen3.8 baseline

| Metric | Qwen3.8 | Hermes-4.3-36B | Beaten? |
|---|---|---|---|
| TASK_SUCCESS | 2% | 8% | YES |
| ROOT_CAUSE | 62% | 78% | YES |
| EVIDENCE_DISCOVERY (global) | 20.6% | 27.4% | YES |
| TOOL_PRECISION | 6.8% | 7.6–8.3% | YES |
| TOOL_F1 | 10% | 11.9–12.7% | YES |
| Long-context 60K | 0/3 | 0/3 | NO (tie) |

QWEN38 BASELINE BEATEN ON EVIDENCE DISCOVERY: YES

## Hard gates (unchanged)

TASK_SUCCESS 8% << 90% FAIL; ROOT_CAUSE 78% < 90% FAIL; EVIDENCE_DISCOVERY 27.4% << 95% FAIL;
TOOL_PRECISION ~8% << 90% FAIL; TOOL_RECALL 27.4% << 95% FAIL; TOOL_F1 ~12% << 92% FAIL;
ERROR_RECOVERY ~26% << 95% FAIL; IRRELEVANT ~92% >> 10% FAIL; DUPLICATE ~17% > 5% FAIL;
JSON_TOOL_ARGS 98.2% < 100% FAIL; FINAL_SCHEMA 98% < 100% FAIL; 56K/58K/60K FAIL.

## Verdict

- HERMES HARD GATE: FAIL
- CANDIDATE STATUS: **HERMES_R8_CANDIDATE_A_REJECTED**

Hermes-4.3-36B measurably outperforms Qwen3.8-27B FP8 on every correctness axis
(root cause, evidence discovery, tool precision/F1, task success) but remains far
below the Hermes DevOps-agent production gates. Candidate A is NOT recommended for
autonomous Hermes core. Final acceptance/decision belongs to ChatGPT after independent
GitHub Connector audit.
