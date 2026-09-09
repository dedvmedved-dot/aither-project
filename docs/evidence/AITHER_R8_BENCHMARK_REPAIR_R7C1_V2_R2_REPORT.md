# Aither — R7-C1 v2-R2 Corrective Closure: Final Report

TASK: `AITHER-HERMES-R8-BENCHMARK-REPAIR-R7C1-V2-R2`
EXECUTOR: HERMES ONLY
MODE: FORCE_MAJEURE / MANUAL / HERMES
BASELINE: `b02e2046233f7b9ea8ebb65364705b10f6667309`

## 1. Objective

Close the two confirmed blockers from the v2-R1 audit (R2-1 scenario-specific relevance,
R2-2 operation-dimension matching) and prove the corrected v2-R2 instrument deterministically.
No model was run; no candidate was run.

## 2. Blocker closure

| Blocker | Fix |
|---|---|
| R2-1 scenario-specific relevance | explicit `relevance_rules` (typed ops + `ANY` wildcard) per scenario; domain-wide sets removed |
| R2-2 operation dimensions | `psql_query` canonical SQL match; `docker_exec_dns` container+host; `docker_build` tag+path; explicit evidence-side wildcards; executable audit |

## 3. Validation results (all mandatory gates PASS)

- Scenario-specific relevance: **50/50**
- Same-domain irrelevance tests: **200/200** (>=40)
- Relevant-negative tests: **118/118** (>=40)
- Executable operation-dimension tests: **82/82** (>=80)
- Significant fields silently ignored: **0**
- Wildcard tests: **6/6**
- Provenance assert tests: **10/10**; unrevealed valid-ID credit **0**; fabricated ID credit **0**
- Source semantic preservation (entity-level): **73/73**
- False evidence leaks: **0**
- Evaluator R2: **700/700**
- Preflight R2: **23/23**
- Long-context scripted: **13/13** (56K 5/5, 58K 5/5, 60K 3/3); adversarial fabricated-evidence case **FAILS AS EXPECTED**

Scripted positive: FULL **50/50**, ROUTED **50/50** — TASK_SUCCESS 100%, ROOT 100%,
EVIDENCE_DISCOVERY 100%, CREDITED 100%, TOOL_PRECISION 100%, RECALL 100%, F1 100%,
IRRELEVANT 0%, DUPLICATE 0%.

Scripted negatives: A (irrelevant) IRRELEVANT 100% / TASK_SUCCESS 0%; B (wrong context)
FALSE_POSITIVE_REVEALS 0; C (non-investigating) TASK_SUCCESS 0% / CREDITED 0%; D (valid-ID
fabrication) TASK_SUCCESS 0% / UNREVEALED 73; E (dimension collision) FALSE_POSITIVE_REVEALS 0;
F (same-domain noise) IRRELEVANT 100% / TASK_SUCCESS 0%.

## 4. No model qualification

QWEN38_FULL_MODEL_RUN_EXECUTED = NO; CANDIDATE_A/B/C/D/E_EXECUTED = NO.

## 5. Production immutability

No runtime mutation performed. QWEN38_PRODUCTION_UNCHANGED = YES; N8_UNCHANGED = YES;
ROUTING_UNCHANGED = YES; AGENT_UNCHANGED = YES (`.agent/CURRENT_TASK.*` not modified).

## 6. Proposed classification

All mandatory R2 gates pass.

`PROPOSED_R7C1_V2_R2_BENCHMARK_VALIDATED`

Hermes does NOT assign final acceptance; final classification belongs to ChatGPT after
independent GitHub Connector audit.

SECRETS_EXPOSED: NO. CODEX_USED: NO. AUTOMATED_RUNNER_USED: NO.
