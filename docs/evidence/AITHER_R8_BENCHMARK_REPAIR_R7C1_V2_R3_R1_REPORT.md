# Aither — R7-C1 v2-R3-R1 Final Micro-Correction: Report

TASK: `AITHER-HERMES-R8-BENCHMARK-REPAIR-R7C1-V2-R3-R1`
EXECUTOR: HERMES ONLY
MODE: FORCE_MAJEURE / MANUAL / HERMES
BASELINE: `473e31317c5b36b500b8f7bf1af6e8798ebd7f83`

## 1. Objective

Close the single confirmed blocker `CON-03 EVIDENCE-SIDE HOST WILDCARD FALSE-POSITIVE` and
re-verify the full deterministic regression. No model was run; no candidate was run.

## 2. Fix

- `EVIDENCE_CORRECTIONS = {("CON-03","E1"): {"host":"db.internal"}}` — canonical evidence text
  `server can't find db.internal: NXDOMAIN` makes the target hostname explicit (no regex guess).
- Relevance rule: `docker_exec_dns(container="app", host="db.internal")` (no host wildcard).
- Reverse mapping: `docker exec app nslookup db.internal`.
- Portability: script-relative harness resolution (no hard-coded absolute root path).

## 3. Validation results (all gates PASS)

- Converter: executable YES, reproducible YES (SHA256 `5d9d7245…`), output SHA match YES
- ABSOLUTE_ROOT_HARNESS_DEPENDENCY = NO
- CON-03: canonical container `app`, host `db.internal`; source `canonical evidence text`;
  migration `APPLIED`; evidence/relevance host wildcard `NO`; reverse mapping `docker exec app nslookup db.internal`
- CON-03 tests: **6/6**; false evidence reveals **0** (exact positive, wrong host, wrong
  container, host omitted, direct DNS, unrelated DNS)
- Source semantic asserts: **73/73** (CON-03 E1 via `canonical-result-host-enrichment`)
- Wildcard inventory: 5 list-all values; unjustified **0**; adversarial **8/8**
- Cross-tool equivalence: **34/34**
- Relevance rule audit: **50/50**
- Operation-dimension executable: **82/82**; significant fields silently ignored **0**
- Provenance assert: **10/10**; unrevealed credit **0**; fabricated credit **0**
- Evaluator: **700/700**; false evidence leaks **0**
- Scripted positive: FULL **50/50**, ROUTED **50/50** (TASK_SUCCESS 100%, CREDITED 100%);
  CON-03 scripted command `docker exec app nslookup db.internal`, E1 revealed YES
- Negative A-G: all expected (A/F/G irrelevant 100%, B/E false-reveals 0, C/D task-success 0%)
- Long-context: **13/13** (56K 5/5, 58K 5/5, 60K 3/3); adversarial FAILS AS EXPECTED
- Preflight: **23/23**

## 4. No model qualification

QWEN38_FULL_MODEL_RUN_EXECUTED = NO; CANDIDATE_A/B/C/D/E_EXECUTED = NO.

## 5. Production immutability

No runtime mutation. QWEN38_PRODUCTION_UNCHANGED = YES; N8_UNCHANGED = YES;
ROUTING_UNCHANGED = YES; AGENT_UNCHANGED = YES.

## 6. Proposed classification

All mandatory R3-R1 gates pass.

`PROPOSED_R7C1_V2_R3_R1_BENCHMARK_VALIDATED`

Hermes does NOT assign final acceptance. The next real task (Qwen3.8 control run on frozen
R7-C1 v2) is NOT started here.

SECRETS_EXPOSED: NO. CODEX_USED: NO. AUTOMATED_RUNNER_USED: NO.
