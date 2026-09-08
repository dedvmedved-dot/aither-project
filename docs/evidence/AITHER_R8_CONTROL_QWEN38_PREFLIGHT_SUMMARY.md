# Aither — R8-CONTROL Preflight Summary (Phase 3)

TASK: `AITHER-HERMES-R8-CONTROL-QWEN38-BENCHMARK-VALIDATION`
CONTROL MODEL: Qwen3.8-27B FP8 / vLLM (production, node n7, vLLM 0.27.1)
ENDPOINT: `http://127.0.0.1:18000` (port-forward to `svc/vllm-qwen38-27b-fp8:8000`)
MEASUREMENT: corrected preflight `aither-v2/tools/aither-r8-control-preflight`

## Corrected measurement infrastructure (Phase 2 fixes applied)

| Defect (R7 audit) | Fix |
|---|---|
| `schema_valid = True` constant | REAL JSON Schema validation (`jsonschema`) against canonical tool schemas |
| ">=1 tool, all known" counted as match | EXACT expected-tool matching (expected tool name must be called) |
| multi-tool PASS on one call | >=2 distinct required ACTIONS, each with a valid tool + valid schema |
| single prompt called "multi-turn" | true assistant -> tool result -> assistant continuation (4 cases) |
| error recovery not exercised | true injected failures + recovery check (6 cases) |
| negative controls not separated | 4 separated no-tool controls (excluded from expected-tool count) |
| no raw ledger | full raw request/response JSONL (62 records) |

## Results (48 expected-tool cases)

| Metric | Result | Gate | Status |
|---|---|---|---|
| EXPECTED_TOOL_CASES | 48 | >=40 | PASS |
| EXPECTED_TOOL_CASE_PASS | 48/48 (100%) | =100% | PASS |
| JSON_PARSE | 48/48 (100%) | =100% | PASS |
| ARG_SCHEMA_VALID | 48/48 (100%) | =100% | PASS |
| EXPECTED_TOOL_MATCH | 48/48 (100%) | =100% | PASS |
| MALFORMED | 0 | =0 | PASS |
| HALLUCINATED_TOOL | 0 | =0 | PASS |
| UNSAFE | 0 | =0 | PASS |
| HTTP_5XX | 0 | =0 | PASS |
| MULTI_TOOL | 3/3 (100%) | =100% | PASS |
| MULTI_TURN | 4/4 (100%) | =100% | PASS |
| ERROR_RECOVERY | 6/6 (100%) | >=95% | PASS |
| NEGATIVE_CONTROLS | 4/4 (100% no-tool) | =100% | PASS |
| FORCED_SPECIFIC_TOOL_CHOICE | SUPPORTED | — | info |

## Coverage detail

- 14 tools, direct phrasing: 14/14 exact match
- 14 tools, alternative wording: 14/14 exact match
- tool_choice=required: 2/2 (known tool, valid args)
- forced specific tool choice: SUPPORTED (backend honours forced `read_file`)
- multi-tool (>=2 required actions): 3/3 (MULTI_02 correctly scored via `shell_readonly ls` for "list /var/log")
- multi-turn (assistant -> tool result -> assistant): 4/4 protocol-valid, coherent continuation
- error recovery (not_found / unsupported_command / connection_refused / empty / malformed): 6/6 recovered, 0 blind repeats
- structured arguments (explicit namespace): 4/4 valid schema
- negative controls (basic chat / arithmetic / irrelevant-resistance / no-tool): 4/4 no spurious tool call

## Verdict

`CONTROL_PREFLIGHT = PASS` — all preflight hard gates met at 100%.

This is a material refutation of the R7-C1 measurement: R7-C1 reported TOOL_PRECISION 6.8%
and IRRELEVANT_CALL_RATE 93.3% for this same model; the corrected preflight measures
100% exact-tool match, 100% schema validity, 0 hallucination, 0 irrelevant-call cases.

Artifacts:
- `AITHER_R8_CONTROL_QWEN38_PREFLIGHT.csv`
- `AITHER_R8_CONTROL_QWEN38_PREFLIGHT_RAW.jsonl`
