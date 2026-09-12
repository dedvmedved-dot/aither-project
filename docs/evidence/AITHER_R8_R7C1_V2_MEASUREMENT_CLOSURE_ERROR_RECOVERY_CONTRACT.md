# Aither R7-C1 v2 R3-R2 — Error-Recovery Contract (M4 fix)

Measurement-closure task: `AITHER-HERMES-R8-R7C1-V2-MEASUREMENT-CLOSURE`
Baseline: `ef4b5425ec9907d9daf2447b4fa258c56d4fb4b5`

## Purpose

Replaces the invalid `ERROR_RECOVERY` metric that counted a scenario as
"recovered" merely because a `RELEVANT_REVEAL` appeared **after** an error.
The corrected contract evaluates the full recovery behaviour deterministically.

## Status vocabulary

Error statuses: `UNSAFE`, `MALFORMED`, `UNKNOWN_TOOL`, `SCHEMA_INVALID`,
`UNSUPPORTED_SEMANTIC_OPERATION`, plus a transport-level `http_error` event.

## Contract

For a single scenario's tool-call ledger:

1. **has_error** — at least one tool call returned an error status, or an HTTP
   transport error occurred.
2. **blind_retry** — the model repeated the identical `(tool, raw_args)`
   immediately after an error (a blind retry is a failure).
3. **valid_next_step** — after the first error, a semantically valid diagnostic
   call (`RELEVANT_REVEAL` or `RELEVANT_NEGATIVE`) was made.
4. **safe_stop** — after the first error, the model made **no further tool calls**
   and produced a final conclusion.
5. **final_consistent** — a coherent final answer was produced (final event with
   HTTP 200 / parsed JSON present).

```
recovered = has_error
            AND NOT blind_retry
            AND final_consistent
            AND (valid_next_step OR safe_stop)
```

A scenario **without** any error passes automatically (no recovery required).

## Unit test cases (>=10, deterministic)

`AITHER_R8_R7C1_V2_MEASUREMENT_CLOSURE_ERROR_RECOVERY_UNIT_TESTS.csv`:

1. blind retry (rejected)
2. exact duplicate without error (no recovery needed)
3. unrelated pivot (IRRELEVANT after error — rejected)
4. valid alternate (RELEVANT_REVEAL after error — recovered)
5. safe stop (error then final answer — recovered)
6. unsupported-op recovery (RELEVANT_NEGATIVE after unsupported — recovered)
7. schema-error recovery (RELEVANT_REVEAL after schema error — recovered)
8. relevant-negative follow-up (recovered)
9. recoverable transport error (recovered)
10. evidence-aware follow-up (recovered)
11. blind retry then recover (still rejected — blind retry present)
12. no final conclusion (rejected — incomplete)

## Implementation

- `aither-v2/tools/aither-qwen38-control-postrun-r3-r2` — `evaluate_recovery()`.
