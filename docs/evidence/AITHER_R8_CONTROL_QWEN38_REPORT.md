# Aither — R8-CONTROL: Benchmark & Harness Validation Against Production Qwen3.8

TASK: `AITHER-HERMES-R8-CONTROL-QWEN38-BENCHMARK-VALIDATION`
EXECUTOR: HERMES ONLY
MODE: FORCE_MAJEURE / MANUAL / HERMES
CONTROL MODEL: Qwen3.8-27B FP8 / vLLM (production, node n7)

---

## 0. Primary question — ANSWERED

> Does R7-C1 reliably distinguish a production-capable control model from failed
> autonomous-Hermes candidates, or does the benchmark/harness itself produce
> systemic false failures?

**The benchmark/harness itself produces systemic false failures.**

The production control model (Qwen3.8-27B) shows **perfect basic tool-calling**
(100% across all preflight gates) when measured with corrected infrastructure,
yet the unchanged R7-C1 harness scores it at 2% task success, 6.6% tool precision,
93% irrelevant-call rate, 0/13 long-context — *below every rejected candidate*.

The measurement stack, not the model, is the source of the failure.

---

## 1. Corrected preflight (Phase 3) — CONTROL PREFLIGHT = PASS

48 expected-tool cases, all hard gates at 100%:

| Gate | Result |
|---|---|
| EXPECTED_TOOL_CASES | 48 (>=40) PASS |
| EXPECTED_TOOL_CASE_PASS | 48/48 (100%) PASS |
| JSON_PARSE | 48/48 (100%) PASS |
| ARG_SCHEMA_VALID | 48/48 (100%) PASS |
| EXPECTED_TOOL_MATCH | 48/48 (100%) PASS |
| MALFORMED / HALLUCINATED / UNSAFE / HTTP5xx | 0 / 0 / 0 / 0 PASS |
| MULTI_TOOL | 3/3 (100%) PASS |
| MULTI_TURN | 4/4 (100%) PASS |
| ERROR_RECOVERY | 6/6 (100%) PASS |
| NEGATIVE_CONTROLS | 4/4 (100% no-tool) PASS |
| FORCED_SPECIFIC_TOOL_CHOICE | SUPPORTED |

The corrected preflight implements the R7 audit fixes: real JSON Schema validation
(`jsonschema`), exact expected-tool matching, true multi-tool (>=2 distinct actions),
true multi-turn (assistant -> tool result -> assistant), true injected-error recovery,
separated negative controls, and a raw request/response JSONL ledger (62 records).

This is a **material refutation** of the R7-C1 tool-calling measurement: R7-C1 reported
TOOL_PRECISION 6.8% / IRRELEVANT 93.3%; the corrected preflight measures 100%.

---

## 2. Full R7-C1 run (Phase 7) — UNCHANGED canonical harness

| Config | TASK_SUCCESS | ROOT | EVIDENCE_DISC (per-scenario) | SCHEMA | TOOL_PRECISION |
|---|---|---|---|---|---|
| FULL F0 | 2.0% | 62.0% | 16.7% | 100% | 6.9% |
| FULL F1 | 2.0% | 60.0% | 16.7% | 90% | 6.9% |
| ROUTED F0 | 2.0% | 62.0% | 19.3% | 100% | 6.5% |
| ROUTED F1 | 2.0% | 62.0% | 19.3% | 90% | 6.5% |

Common: JSON_TOOL_ARGS=100%, HALL=0, UNSAFE=0, HTTP5xx=0, DUP=5.

Tool metrics (evidence-ID, ALL policy): TOOL_PRECISION 6.58%, TOOL_RECALL 24.66%,
TOOL_F1 10.39%, IRRELEVANT 93.42%, DUPLICATE 1.58%, ERROR_RECOVERY 22.0%.

**These reproduce R7-C1 exactly** (2% / 62% / 6.6% / 24.7% / 10.4% / 93.4% / 22%).

---

## 3. Root cause of the false failure — the simulator

The raw tool ledger shows the smoking gun: **1266 tool calls, of which 1164 (92%)
return `error` (not_found / unsupported_command / empty) from the simulator**.

The model issues valid tool calls (JSON_TOOL_ARGS=100%, HALL=0 — every argument is
well-formed JSON against a known tool), but the canonical harness's `simulate()` uses
exact-string `arg_key`/`ev_key` matching to map a tool call to scenario evidence. That
matching fails for ~92% of valid calls, so valid calls are classified "irrelevant" and
"no evidence revealed".

Consequence: TOOL_PRECISION ~6.6% and IRRELEVANT ~93% are **simulator-match artifacts**,
not model behavior. This defect affects every candidate identically (see §4), which is
why the benchmark cannot rank models — it measures the simulator's matching success,
not the model's tool competence.

---

## 4. Differentiation (Phase 10) — control vs candidates A/B/D

| Metric | Control Qwen3.8 | A | B | D |
|---|---|---|---|---|
| TASK_SUCCESS (FULL) | 2.0% | 8.0% | 4.0% | 2.0% |
| ROOT (FULL) | 62.0% | 78.0% | 70.0% | 70.0% |
| TOOL_PRECISION | 6.58% | 7.95% | 9.98% | 12.17% |
| TOOL_F1 | 10.39% | 12.7% | 15.59% | 15.99% |
| IRRELEVANT | 93.42% | 92.05% | 90.02% | 87.83% |
| ERROR_RECOVERY | 22.0% | 30.61% | 20.0% | 25.0% |
| LONG 56K/58K/60K | 0/5, 0/5, 0/3 | 0/5, 0/5, 0/3 | 0/5, 0/5, 0/3 | 0/5, 0/5, 0/3 |

The production control model — which the corrected preflight proves calls tools with
100% accuracy — scores **equal to or worse than** the rejected candidates on every
functional gate. A benchmark that ranks the production control below rejected
candidates is not a valid model-selection instrument.

---

## 5. Long-context (Phase 8) — 0/13 PASS

5×56K, 5×58K, 3×60K: all 13 cases `root_correct=False` (0/13 PASS). All begin/mid/end
markers embedded and found (assembly check passed); all tool-call JSON valid; hall=0;
unsafe=0; token counts within target. Reproduces R7-C1 (0/13) exactly.

Note: even LC-56K-02 with evidence_cov=1.0 (all three facts discovered) produced
`root_correct=False` — the final-synthesis/scoring path, not evidence retrieval, is
what fails.

---

## 6. Hard gates (Phase 9) — FAIL (same shape as R7-C1)

TASK_SUCCESS 2% (<90% FAIL) · ROOT 62% (<90% FAIL) · EVIDENCE_DISCOVERY 24.66%
(<95% FAIL) · TOOL_PRECISION 6.58% (<90% FAIL) · TOOL_RECALL 24.66% (<95% FAIL) ·
TOOL_F1 10.39% (<92% FAIL) · ERROR_RECOVERY 22% (<95% FAIL) · IRRELEVANT 93.42%
(>10% FAIL) · DUPLICATE 1.58% (<=5% PASS) · JSON_ARGS 100% (PASS) · FINAL_SCHEMA
F0 100% / F1 90% (PASS/FAIL) · HALL 0 (PASS) · UNSAFE 0 (PASS) · HTTP5xx 0 (PASS) ·
56K 0/5, 58K 0/5, 60K 0/3 (FAIL).

SEQUENTIAL_150 = SKIPPED_CONDITIONALLY (functional hard gates fail).

---

## 7. Architect decision proposal (Phase 11)

**CASE C — CONTROL SHOWS THE SAME SYSTEMIC FAILURE SHAPE AS REJECTED CANDIDATES.**

`PROPOSED_R8_BENCHMARK_INVALID_FOR_MODEL_SELECTION`

Do NOT start Candidate E. Do NOT redesign the benchmark in this task.

The control does not pass the functional hard gates; the failure is measurement-side
(proven by the 100% preflight and the 92% simulator-miss in the ledger), not model-side.
Final classification belongs to ChatGPT after the GitHub Connector audit.

---

## 8. Production immutability (Phase 12) — unchanged

QWEN38_PRODUCTION_UNCHANGED=YES (replicas 1, image digest unchanged, restart 0) ·
N8_UNCHANGED=YES · ROUTING_UNCHANGED=YES · AGENT_UNCHANGED=YES (.agent hashes
unchanged) · health 200 · /v1/models qwen3.8-27b · chat "4" · tool smoke read_file ·
GPU 2× Quadro RTX 6000 19309/23040 MiB (unchanged).

---

## Evidence artifacts (all under docs/evidence/)

`AITHER_R8_CONTROL_QWEN38_CANONICAL_FREEZE.json`, `..._PREFLIGHT.csv`,
`..._PREFLIGHT_RAW.jsonl`, `..._PREFLIGHT_SUMMARY.md`, `..._RUNTIME_PRE.txt`,
`..._RUNTIME_POST.txt`, `..._FULL_F0.csv`, `..._FULL_F1.csv`, `..._ROUTED_F0.csv`,
`..._ROUTED_F1.csv`, `..._TOOL_CALLS.csv`, `..._TOOL_METRICS.csv`,
`..._LONG_CONTEXT.csv`, `..._CANDIDATE_COMPARISON.csv`, `..._INTEGRITY.md`,
`..._REPORT.md` (this file). Measurement helpers: `aither-v2/tools/aither-r8-control-preflight`,
`aither-v2/tools/aither-r8-control-benchmark-run.sh`, `aither-v2/tools/aither-r8-control-longcontext-run.sh`.

Note: the canonical harness writes the tool ledger as CSV (not .jsonl), consistent with
R7-C1 (`AITHER_QWEN38_VLLM_HERMES_R7C1_TOOL_CALLS.csv`); `..._TOOL_CALLS.csv` is that
canonical-format ledger.

SECRETS_EXPOSED: NO. No secrets committed; the vLLM API key is used only at runtime
(`/tmp/aither_qwen38_api_key.txt`, not under the repo).

CODEX_USED: NO. AUTOMATED_RUNNER_USED: NO.
