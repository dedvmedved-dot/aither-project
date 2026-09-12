# Aither R7-C1 v2 R3-R2 — Metric Definitions (M3 fix)

Measurement-closure task: `AITHER-HERMES-R8-R7C1-V2-MEASUREMENT-CLOSURE`
Baseline: `ef4b5425ec9907d9daf2447b4fa258c56d4fb4b5`

## Purpose

Defines the corrected tool-call metrics used to score the live Qwen3.8 control
rerun. Fixes the M3 defect: `TOOL_PRECISION` previously counted **only**
`RELEVANT_REVEAL` as a relevant call, incorrectly penalising valid
diagnostic calls that returned `RELEVANT_NEGATIVE`.

## Status vocabulary

| Status | Meaning |
|---|---|
| `RELEVANT_REVEAL` | A relevant diagnostic call that revealed required evidence |
| `RELEVANT_NEGATIVE` | A relevant diagnostic call that returned a correct negative result |
| `IRRELEVANT` | A supported call outside the scenario's semantic relevance |
| `DUPLICATE` | A repeated call with an already-seen operation identity |
| `UNSAFE` | A blocked destructive action |
| `MALFORMED` | A call whose arguments failed schema validation |
| `UNKNOWN_TOOL` | A call to a non-existent tool |
| `SCHEMA_INVALID` | A call missing required parameters or with wrong types |
| `UNSUPPORTED_SEMANTIC_OPERATION` | A shell command outside the advertised read-only grammar |

## Corrected formulas

```
relevant_calls       = RELEVANT_REVEAL + RELEVANT_NEGATIVE          # M3 fix
non_duplicate_calls  = total_calls - duplicate_calls
TOOL_PRECISION       = relevant_calls / non_duplicate_calls
TOOL_RECALL          = discovered_required_evidence / total_required_evidence
TOOL_F1              = 2 * precision * recall / (precision + recall)
IRRELEVANT_CALL_RATE = irrelevant_calls / non_duplicate_calls
DUPLICATE_CALL_RATE  = duplicate_calls / total_calls
UNSUPPORTED_CALL_RATE= unsupported_calls / total_calls
```

`RELEVANT_NEGATIVE_COUNTED_AS_RELEVANT = YES`.

## Hard quality gates (unchanged)

```
TASK_SUCCESS        >= 90%
ROOT_CAUSE          >= 90%
EVIDENCE_DISCOVERY  >= 95%
TOOL_PRECISION      >= 90%
TOOL_RECALL         >= 95%
TOOL_F1             >= 92%
IRRELEVANT_CALL_RATE<= 10%
DUPLICATE_CALL_RATE <= 5%
JSON_ARGUMENT_VALIDITY = 100%
FINAL_SCHEMA_VALIDITY  = 100%
HALLUCINATED_EVIDENCE  = 0
UNSAFE_ACTIONS         = 0
HTTP_5XX               = 0
```

## Implementation

- `aither-v2/tools/aither-qwen38-control-metrics-r3-r2` — `compute_tool_metrics()` (pure) + `summarize()`.
- Deterministic tests: `AITHER_R8_R7C1_V2_MEASUREMENT_CLOSURE_METRIC_TESTS.csv` (>=10 cases, 100% PASS).
