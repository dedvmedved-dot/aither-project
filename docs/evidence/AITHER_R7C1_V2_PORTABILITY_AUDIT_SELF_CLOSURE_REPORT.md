# Aither — R7-C1 v2 Portability Audit Self-Closure: Final Report

TASK: `AITHER-HERMES-R7C1-V2-PORTABILITY-AUDIT-SELF-CLOSURE`
EXECUTOR: HERMES ONLY
MODE: FORCE_MAJEURE / MANUAL / HERMES
BASELINE: `290ecee374b21926bc2188522cc5afe66d263235`

## 1. Objective

Close the two packaging/self-audit defects in the portability tooling:
1. `portability-audit` had a host-specific default `REPO = os.environ.get("REPO", "/root/aither-project-r7-canonical")`.
2. `portability-audit`/`portability-check` excluded whole files containing "portability"
   from their own scan, hiding the tooling from the audit.

No benchmark semantics were changed.

## 2. Fix

- `portability-check`: AST-based forbidden runtime dependency detection; distinguishes
  allowed search-signature/docstring/data literals from runtime deps (REPO=, SourceFileLoader,
  open, Path, subprocess.run). No whole-file exclusions — it scans itself and the audit too.
- `portability-audit`: script-relative repo resolution (`..`/`..` from the tool), no host-specific
  default, no env-var requirement, no whole-file exclusions. Added `--no-cwd` flag to break
  self-recursion in the CWD test.

## 3. Validation results (all gates PASS)

- Portability audit repo resolution: **SCRIPT_RELATIVE**; host-specific default **NONE**;
  whole-file exclusions **NONE**
- Runtime tool audit: **13/13** (harness, converter, con03, tests, opdim, scripted, evaltests,
  longcontext, preflight, audit, checker, portability-check, scenario-converter)
- Checker self-test: **6/6** (REPO=/root→DETECTED, SourceFileLoader→DETECTED, open→DETECTED,
  subprocess.run→DETECTED, signature-list→ALLOWED, script-relative→ALLOWED)
- Portability tooling CWD test: **2/2** (audit + checker run from `/tmp`, exit 0)
- Forbidden runtime dependencies: **0**
- Semantic immutability: scenario/harness/matcher/evaluator/relevance/CON-03 all **UNCHANGED**
  (scenario JSON and harness byte-identical to baseline)

Deterministic regression (unchanged results):
- CON-03 **6/6**, false reveals **0**
- Source semantic asserts **73/73**
- Unjustified wildcards **0**; wildcard adversarial **8/8**
- Cross-tool equivalence **34/34**; relevance rule audit **50/50**
- Operation dimension **82/82**; significant fields silently ignored **0**
- Provenance **10/10**; unrevealed credit **0**; fabricated credit **0**
- Evaluator **700/700**; false evidence leaks **0**
- Scripted positive FULL **50/50**, ROUTED **50/50**; CON-03 command `docker exec app nslookup db.internal`
- Long-context **13/13**; preflight **23/23**

## 4. No model qualification

QWEN38_FULL_MODEL_RUN_EXECUTED = NO; CANDIDATE_A/B/C/D/E_EXECUTED = NO.

## 5. Production immutability

No runtime mutation. QWEN38_PRODUCTION_UNCHANGED = YES; N8_UNCHANGED = YES;
ROUTING_UNCHANGED = YES; AGENT_UNCHANGED = YES.

## 6. Proposed classification

All portability self-audit and regression gates pass.

`PROPOSED_R7C1_V2_PORTABILITY_AUDIT_SELF_CLOSURE_VALIDATED`

Hermes does NOT assign final acceptance. The next authorized stage (Qwen3.8 control run on
frozen R7-C1 v2) is NOT started here.

SECRETS_EXPOSED: NO. CODEX_USED: NO. AUTOMATED_RUNNER_USED: NO.
