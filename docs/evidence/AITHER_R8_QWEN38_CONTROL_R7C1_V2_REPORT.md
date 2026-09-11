# Aither — Qwen3.8 Control Run on Frozen R7-C1 v2: Final Report

TASK: `AITHER-HERMES-R8-QWEN38-CONTROL-RUN-FROZEN-R7C1-V2`
EXECUTOR: HERMES ONLY
MODE: FORCE_MAJEURE / MANUAL / HERMES
BASELINE: `87f2deaaeaa6a4e5915a97cf16ee7e26af677520`

## 1. Objective

First real model control run against the production Qwen3.8-27B FP8 backend using the
validated (frozen) R7-C1 v2 benchmark. Prove the live benchmark path is sane before any
candidate retest. This task is NOT candidate model selection.

## 2. Live path sanity — PASS

- Benchmark freeze: `BENCHMARK_FILES_UNCHANGED = YES`, `PORTABILITY_CHECK = PASS`,
  `DETERMINISTIC_PREFLIGHT = PASS`, worktree clean.
- Runtime identity captured (qwen3.8-27b, vLLM 0.27.1, 2× Quadro RTX 6000,
  image sha256:0a51ea…, TP=2, max-model-len 65536, qwen3_xml tool parser).
- Live smoke: **8/8 PASS** (single-tool, multi-tool, irrelevant-tool avoidance,
  error-recovery path, final-JSON schema, evidence provenance, ROUTED, FULL).

The live path is demonstrably sane: API, tool-call parsing, simulator, final-JSON parsing,
evaluator and provenance all function correctly. Schema validity 100%, unsafe 0,
hallucinated evidence 0, HTTP 5xx 0.

## 3. Control results (model quality)

| Metric | FULL | ROUTED | Hard gate |
|---|---|---|---|
| TASK_SUCCESS | 4.0% | 4.0% | >=90% FAIL |
| ROOT_CAUSE | 48.0% | 46.0% | >=90% FAIL |
| EVIDENCE_DISCOVERY | 27.0% | 22.0% | >=95% FAIL |
| TOOL_PRECISION | 9.8% | 8.8% | >=90% FAIL |
| TOOL_RECALL | 35.6% | 27.4% | >=95% FAIL |
| TOOL_F1 | 15.4% | 13.4% | >=92% FAIL |
| IRRELEVANT_CALL_RATE | 61.1% | 72.6% | <=10% FAIL |
| DUPLICATE_CALL_RATE | 12.3% | 9.6% | <=5% FAIL |
| JSON_ARGUMENT_VALIDITY | 100% | 100% | =100% PASS |
| FINAL_SCHEMA_VALIDITY | 100% | 100% | =100% PASS |
| HALLUCINATED_EVIDENCE | 0 | 0 | =0 PASS |
| UNSAFE_ACTIONS | 0 | 0 | =0 PASS |
| HTTP_5XX | 0 | 0 | =0 PASS |

Error recovery: **15.6%** (>=95% FAIL). Long-context: **0/13 PASS**
(56K 0/5, 58K 0/5, 60K 0/3; all root_correct=False).

SEQUENTIAL_150_EXECUTED = NO (functional hard gates not met).

## 4. Interpretation

The corrected benchmark now measures a real, separable model limitation: Qwen3.8 calls
tools with perfect schema validity (100%), never hallucinates evidence, and never acts
unsafely — but its autonomous multi-round investigation is weak (4% task success, 48%
root, 27% evidence discovery, 15.6% error recovery, 0/13 long-context). This is
consistent with the earlier R8-CONTROL finding, now measured by the repaired benchmark
rather than by measurement artifacts.

## 5. Production immutability

QWEN38_PRODUCTION_UNCHANGED = YES (image/replicas/restarts/node identical) ·
N8_UNCHANGED = YES · ROUTING_UNCHANGED = YES · AGENT_UNCHANGED = YES.
No runtime mutation performed.

## 6. Proposed classification

`PROPOSED_QWEN38_CONTROL_FAILED_QUALITY`

The live path is demonstrably sane (smoke 8/8, schema 100%, no plumbing errors), evidence
is complete (raw ledgers + summaries for all 113 scenarios), and one or more model-quality
hard gates fail. This is a model-quality failure, not a benchmark-invalidating result.

Hermes does NOT assign final acceptance. Candidate runs remain prohibited.

SECRETS_EXPOSED: NO. CODEX_USED: NO. AUTOMATED_RUNNER_USED: NO.
