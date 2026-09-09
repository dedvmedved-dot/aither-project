# Aither — R7-C1 v2-R3-R1 Portability Closure: Final Report

TASK: `AITHER-HERMES-R8-BENCHMARK-REPAIR-R7C1-V2-R3-R1-PORTABILITY-CLOSURE`
EXECUTOR: HERMES ONLY
MODE: FORCE_MAJEURE / MANUAL / HERMES
BASELINE: `f5e8324391edab33326e607f155e5af4d1ee0a68`

## 1. Objective

Close the packaging/reproducibility blocker `ABSOLUTE_ROOT_HARNESS_DEPENDENCY`. Five R3-R1
runner scripts still loaded the harness via hard-coded `/root/aither-project-r7-canonical/...`.
No benchmark semantics were changed.

## 2. Fix

- Replaced hard-coded absolute harness path in 5 runners (tests, opdim, scripted, evaltests,
  longcontext) with script-relative resolution (`_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))`).
- Added a deterministic portability checker and an audit/CWD-independence runner.

## 3. Validation results (all gates PASS)

- Portability audit: **10/10** (all R3-R1 executables audited; script-relative; no CWD dependency)
- Forbidden absolute runtime path matches: **0** (`ABSOLUTE_ROOT_HARNESS_DEPENDENCY = NO`)
- CWD independence: **8/8** (all runners executed from `/tmp`, exit 0, artifacts created)
- Converter: executable YES, reproducible YES (SHA256 `5d9d7245…`), output SHA match YES
- Semantic immutability: scenario/matcher/evaluator/relevance/CON-03 semantics all **UNCHANGED**
  (diff classification `PORTABILITY_ONLY`)

Deterministic regression (unchanged results):
- CON-03 **6/6**, false evidence reveals **0**
- Source semantic asserts **73/73**
- Unjustified wildcards **0**; wildcard adversarial **8/8**
- Cross-tool equivalence **34/34**; relevance rule audit **50/50**
- Operation dimension **82/82**; significant fields silently ignored **0**
- Provenance **10/10**; unrevealed credit **0**; fabricated credit **0**
- Evaluator **700/700**; false evidence leaks **0**
- Scripted positive FULL **50/50**, ROUTED **50/50**; CON-03 command `docker exec app nslookup db.internal`
- Long-context **13/13** (56K 5/5, 58K 5/5, 60K 3/3); preflight **23/23**

## 4. No model qualification

QWEN38_FULL_MODEL_RUN_EXECUTED = NO; CANDIDATE_A/B/C/D/E_EXECUTED = NO.

## 5. Production immutability

No runtime mutation. QWEN38_PRODUCTION_UNCHANGED = YES; N8_UNCHANGED = YES;
ROUTING_UNCHANGED = YES; AGENT_UNCHANGED = YES.

## 6. Proposed classification

All portability and deterministic regression gates pass.

`PROPOSED_R7C1_V2_R3_R1_PORTABILITY_VALIDATED`

Hermes does NOT assign final acceptance. The next authorized stage (Qwen3.8 control run on
frozen R7-C1 v2) is NOT started here.

SECRETS_EXPOSED: NO. CODEX_USED: NO. AUTOMATED_RUNNER_USED: NO.
