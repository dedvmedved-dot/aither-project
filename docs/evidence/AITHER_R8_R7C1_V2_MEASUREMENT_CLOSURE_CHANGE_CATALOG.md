# Aither R7-C1 v2 R3-R2 — Measurement-Closure Change Catalog

Measurement-closure task: `AITHER-HERMES-R8-R7C1-V2-MEASUREMENT-CLOSURE`
Baseline: `ef4b5425ec9907d9daf2447b4fa258c56d4fb4b5`

## Summary

All changes are **measurement-only** — they fix how the frozen R7-C1 v2 benchmark
is *measured* (evaluation, metrics, shell contract, live orchestration, evidence
completeness). No scenario task intent, evidence truth, root truth, safety truth,
or threshold was changed. Production (Qwen3.8 weights / quantization / vLLM
runtime / launch args / GPU topology / routing / n7-n8 / Portal-BFF-Identity)
was not modified.

## Change list

### M1 — Long-context finalization uses full conversation state
- **Category:** live orchestration (measurement-only)
- **Fix:** the long-context final synthesis is now a continuation of the same
  conversation (original 56-60K context, original task, prior assistant turns,
  tool calls, tool result texts, discovered evidence) instead of a detached
  two-message call over evidence IDs only.
- **File:** `aither-v2/tools/aither-qwen38-control-live-longcontext-r3-r2`
- `LONG_CONTEXT_FINAL_USES_FULL_CONVERSATION_STATE = YES`

### M2 — Long-context raw evidence completeness
- **Category:** evidence completeness
- **Fix:** the 13 long-context cases now write a reconstructable raw ledger
  (JSONL) with exact messages, tools exposed, raw responses, tool calls, raw
  args, simulator status, tool result texts, final response, parsed JSON,
  evaluator output, timing, HTTP status, token usage, retry identity.
- **File:** `aither-v2/tools/aither-qwen38-control-live-longcontext-r3-r2`
- `LONG_CONTEXT_RAW_CASES = 13`, `LONG_CONTEXT_RAW_COMPLETE = YES`

### M3 — TOOL_PRECISION formula (RELEVANT_NEGATIVE counted as relevant)
- **Category:** metric correction
- **Fix:** `relevant_calls = RELEVANT_REVEAL + RELEVANT_NEGATIVE`.
  Separately computed: semantic tool precision, evidence recall, irrelevant
  rate, duplicate rate, unsupported rate.
- **File:** `aither-v2/tools/aither-qwen38-control-metrics-r3-r2`
- `RELEVANT_NEGATIVE_COUNTED_AS_RELEVANT = YES`

### M4 — ERROR_RECOVERY metric (full contract)
- **Category:** metric correction
- **Fix:** recovery is now a deterministic contract over returned error/status,
  no blind retry, semantically valid next step or safe stop, and a consistent
  final conclusion — not "a RELEVANT_REVEAL appeared later".
- **File:** `aither-v2/tools/aither-qwen38-control-postrun-r3-r2`

### M5 — Final-answer semantic evaluator (typed concepts + general aliases)
- **Category:** semantic evaluation
- **Fix:** replaces the narrow exact-substring matcher with a deterministic
  semantic evaluator: typed concept keys (`root_semantics`,
  `remediation_semantics`), a general alias map, and a stopword-tolerant ordered
  token-subsequence matcher. No LLM judge, no model-specific exceptions.
- **Files:**
  - `aither-v2/tools/aither-agent-harness-r7c1-v2-r3-r2` (evaluator + `CONCEPT_ALIASES`)
  - `aither-v2/tools/aither-r7c1-v2-r3-r2-scenario-converter`
  - `docs/evidence/AITHER_R7C1_V2_R3_R2_SCENARIOS.json` (semantic annotations)

### M6 — shell_readonly contract (advertised grammar == parser coverage)
- **Category:** shell contract
- **Fix:** the advertised grammar was narrowed to the actually-supported
  read-only diagnostic families, and the parser was expanded to cover common
  safe diagnostics (`dmesg`, `grep`, `tail`, `head`, `systemctl --failed`) plus
  deterministic pipeline/chain/redirection handling.
- **File:** `aither-v2/tools/aither-agent-harness-r7c1-v2-r3-r2`
- `ADVERTISED_BUT_UNSUPPORTED = 0`, `UNSAFE_ALLOWED = 0`

### M7 — FULL/ROUTED finalization uses full conversation state
- **Category:** live orchestration (measurement-only)
- **Fix:** the FULL/ROUTED final synthesis is a continuation of the same
  conversation (system + task + prior turns + tool results + evidence), not a
  detached call.
- **File:** `aither-v2/tools/aither-qwen38-control-live-runner-r3-r2`
- `FULL_ROUTED_FINAL_USES_FULL_CONVERSATION_STATE = YES`

## Truth-change audit

| Dimension | Changed? |
|---|---|
| scenario task intent | NO |
| evidence truth | NO |
| root truth | NO |
| safety truth | NO |
| thresholds | **NO** |
| production (weights/quant/runtime/launch/GPU/routing/n7-n8/Portal/BFF/Identity) | NO |
| Candidate A/B/C/D/E executed | NO |
| Codex used | NO |

## Versioning

Historical R3-R1 artifacts are unchanged. New measurement-closure versioned
artifacts:
- `aither-v2/tools/aither-agent-harness-r7c1-v2-r3-r2`
- `docs/evidence/AITHER_R7C1_V2_R3_R2_SCENARIOS.json`
- `aither-v2/tools/aither-r7c1-v2-r3-r2-scenario-converter`
- `aither-v2/tools/aither-qwen38-control-live-runner-r3-r2`
- `aither-v2/tools/aither-qwen38-control-live-longcontext-r3-r2`
- `aither-v2/tools/aither-qwen38-control-live-smoke-r3-r2`
- `aither-v2/tools/aither-qwen38-control-metrics-r3-r2`
- `aither-v2/tools/aither-qwen38-control-postrun-r3-r2`
- `aither-v2/tools/aither-r7c1-v2-measurement-closure-tests`
- `aither-v2/tools/aither-r7c1-v2-measurement-closure-final-evaluator`
