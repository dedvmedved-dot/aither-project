# Aither — R7-C1 v2 Measurement-Closure + Qwen3.8 Control Rerun: Final Report

TASK: `AITHER-HERMES-R8-R7C1-V2-MEASUREMENT-CLOSURE`
EXECUTOR: HERMES ONLY
MODE: FORCE_MAJEURE / MANUAL / HERMES
BASELINE_SHA: `ef4b5425ec9907d9daf2447b4fa258c56d4fb4b5`
PARENT: `87f2deaaeaa6a4e5915a97cf16ee7e26af677520`
COMMITS_CREATED: 1
WORKTREE: clean after commit

## 0. Scope

Close the live-run measurement defects (M1–M7) that made the first Qwen3.8 control
run (`ef4b5425`) not evaluable, then repeat the SAME Qwen3.8 control on the frozen
R7-C1 v2 benchmark with corrected measurement. No candidate models, no Codex, no
production changes.

## 1. Measurement closure — deterministic validation

MEASUREMENT_CLOSURE_PRE_FIX_FROZEN = YES
R3_R1_HISTORICAL_ARTIFACTS_UNCHANGED = YES
NEW_HARNESS_PATH = `aither-v2/tools/aither-agent-harness-r7c1-v2-r3-r2`
NEW_SCENARIO_PATH = `docs/evidence/AITHER_R7C1_V2_R3_R2_SCENARIOS.json`
CHANGE_CATALOG_COMPLETE = YES

| Gate | Count | Pass | Required |
|---|---|---|---|
| FINAL_EVALUATOR_TESTS | 172 | 100% | >=170 / 100% |
| METRIC_TESTS | 12 | 100% | >=10 / 100% |
| ERROR_RECOVERY_UNIT_TESTS | 12 | 100% | >=10 / 100% |
| SHELL_CONTRACT_TESTS | 93 | 100% | >=60 / 100% |
| LONG_CONTEXT_STATE_TESTS | 27 | 100% | 100% |
| RAW_LEDGER_STRUCTURE_TESTS | 7 | 100% | 100% |
| scripted positive control | 50 | 100% | 100% |
| operation dimension | 415 | 100% | 100% |
| preflight | 23 | 100% | 100% |
| portability | 6 | 100% | 100% |

ADVERTISED_BUT_UNSUPPORTED = 0
UNSAFE_ALLOWED = 0
DETERMINISTIC_VALIDATION_PASS = YES

## 2. Measurement fixes (M1–M7)

- M1 / M7: final synthesis for FULL/ROUTED/LONG-CONTEXT continues the FULL conversation
  (original task, prior turns, tool calls, tool results, discovered evidence).
  `LONG_CONTEXT_FINAL_USES_FULL_CONVERSATION_STATE = YES`,
  `FULL_ROUTED_FINAL_USES_FULL_CONVERSATION_STATE = YES`.
- M2: reconstructable raw ledger for all 13 long-context cases.
  `LONG_CONTEXT_RAW_CASES = 13`, `LONG_CONTEXT_RAW_COMPLETE = YES`, `RAW_LEDGER_RECONSTRUCTABLE = YES`.
- M3: `relevant_calls = RELEVANT_REVEAL + RELEVANT_NEGATIVE`.
  `RELEVANT_NEGATIVE_COUNTED_AS_RELEVANT = YES`.
- M4: full deterministic error-recovery contract (error observed, no blind retry,
  valid next step or safe stop, consistent final conclusion).
- M5: deterministic semantic final evaluator (typed concepts + general aliases +
  stopword-tolerant ordered token subsequence), no LLM judge, no model-specific exceptions.
- M6: shell_readonly advertised grammar narrowed to supported families + parser expanded
  (dmesg / grep / tail / head / systemctl --failed; pipeline/chain/redirection handling).

## 3. Qwen3.8 control rerun

QWEN38_CONTROL_RERUN_EXECUTED = YES

CONTROL_MODEL = qwen3.8-27b
CONTROL_RUNTIME = vLLM
CONTROL_RUNTIME_VERSION = 0.27.1
CONTROL_IMAGE_DIGEST = sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967
CONTROL_GPU_TOPOLOGY = 2x Quadro RTX 6000 24GB, no NVLink (node n7)

LIVE_SMOKE = 8/8 PASS
FULL_SCENARIOS_EXECUTED = 50
ROUTED_SCENARIOS_EXECUTED = 50
LONG_CONTEXT_SCENARIOS_EXECUTED = 13
ERROR_RECOVERY_LIVE_CASES = 39 scenarios with error, 14 recovered (35.9%)

| Metric | FULL | ROUTED | Hard gate |
|---|---|---|---|
| TASK_SUCCESS | 22.0% | 14.0% | >=90% FAIL |
| ROOT_CAUSE | 48.0% | 58.0% | >=90% FAIL |
| EVIDENCE_DISCOVERY | 29.3% | 32.0% | >=95% FAIL |
| TOOL_PRECISION | 14.9% | 16.5% | >=90% FAIL |
| TOOL_RECALL | 32.9% | 37.0% | >=95% FAIL |
| TOOL_F1 | 20.5% | 22.9% | >=92% FAIL |
| IRRELEVANT_CALL_RATE | 68.1% | 72.2% | <=10% FAIL |
| DUPLICATE_CALL_RATE | 10.1% | 7.5% | <=5% FAIL |
| UNSUPPORTED_CALL_RATE | 15.3% | 10.4% | — |
| JSON_ARGUMENT_VALIDITY | 100% | 100% | =100% PASS |
| FINAL_SCHEMA_VALIDITY | 94.0% | 100.0% | =100% FAIL (FULL) |
| HALLUCINATED_EVIDENCE | 0 | 0 | =0 PASS |
| UNSAFE_ACTIONS | 0 | 0 | =0 PASS |
| HTTP_5XX | 0 | 0 | =0 PASS |

ERROR_RECOVERY = 35.9% (>=95% FAIL)

LONG_CONTEXT_56K = 0/5 PASS
LONG_CONTEXT_58K = 0/5 PASS
LONG_CONTEXT_60K = 0/3 PASS
LONG_CONTEXT_TOTAL = 0/13 PASS (10/13 root_correct=True — M5 fix; evidence discovery still below gate)

SEQUENTIAL_150_EXECUTED = NO (functional hard gates not met)
SEQUENTIAL_150_RESULT = NOT EXECUTED
SILENT_RETRIES = 4
FALSE_EVIDENCE_LEAKS = 0

FULL_RAW_COMPLETE = YES
ROUTED_RAW_COMPLETE = YES
LONG_CONTEXT_RAW_COMPLETE = YES
ERROR_RECOVERY_RAW_COMPLETE = YES

## 4. Immutability

QWEN38_PRODUCTION_UNCHANGED = YES
N8_UNCHANGED = YES
ROUTING_UNCHANGED = YES
AGENT_UNCHANGED = YES

CANDIDATE_A_EXECUTED = NO
CANDIDATE_B_EXECUTED = NO
CANDIDATE_C_EXECUTED = NO
CANDIDATE_D_EXECUTED = NO
CANDIDATE_E_EXECUTED = NO
CODEX_USED = NO
SECRETS_EXPOSED = NO

## 5. Result classification (proposed — Hermes is not acceptance authority)

PROPOSED_MEASUREMENT_CLASSIFICATION = PROPOSED_R7C1_V2_MEASUREMENT_CLOSURE_VALIDATED
PROPOSED_QWEN38_CLASSIFICATION = PROPOSED_QWEN38_CONTROL_FAILED_QUALITY
CONNECTOR_AUDIT_REQUIRED = YES

Measurement closure passed all deterministic gates (100%). The corrected rerun shows
Qwen3.8 produces schema-valid, non-hallucinating, non-unsafe calls, but its autonomous
multi-round investigation quality remains below every hard quality gate
(TASK_SUCCESS 14–22% vs >=90%; EVIDENCE_DISCOVERY 29–32% vs >=95%; ERROR_RECOVERY 35.9%
vs >=95%; LONG_CONTEXT 0/13). This is a valid, separable model-quality result now
measured by a corrected benchmark — no longer contaminated by measurement defects.

## 6. Final stage gate

Final Stage Gate is performed by ChatGPT after an independent GitHub Connector audit.
Hermes stops here.
