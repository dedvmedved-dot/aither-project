# Aither — R8-CONTROL Harness Integrity Validation (Phase 6)

TASK: `AITHER-HERMES-R8-CONTROL-QWEN38-BENCHMARK-VALIDATION`
EXECUTOR: HERMES ONLY
MODE: FORCE_MAJEURE / MANUAL / HERMES
CONTROL MODEL: Qwen3.8-27B FP8 / vLLM (production, node n7)

## Objective

Prove that the harness used for the control run is byte-identical to the canonical
R7-C1 harness frozen at baseline, with ONLY transport-level differences (endpoint,
model identifier, authentication).

## Canonical freeze reference

`AITHER_R8_CONTROL_QWEN38_CANONICAL_FREEZE.json` (Phase 1).

## Method

`git diff --stat HEAD -- <canonical paths>` against the frozen canonical artifacts,
plus SHA256 re-verification against the freeze manifest.

## Result

`git diff --stat HEAD` returned EMPTY for all canonical benchmark artifacts:

- `aither-v2/tools/aither-agent-harness-lab` (evaluator + simulator + router + tool defs + scoring)
- `aither-v2/tools/aither-agent-harness-longcontext`
- `aither-v2/tools/aither-agent-tool-metrics`
- `docs/evidence/AITHER_QWEN38_VLLM_HERMES_R7_SCENARIOS.json`

SHA256 re-verification matched the freeze manifest exactly:

```
7225f7e971223127bfdbf47857d0151f313aa64dbec171b3e381a615cafec2bd  aither-v2/tools/aither-agent-harness-lab
696d09883b9a8a949df1fbc9d456ab3021861c08a47e3ec5713f88599692567f  aither-v2/tools/aither-agent-harness-longcontext
482157e2479bc96f7a18a5bfc9f0aa5e0af87d69be4baf2b69f41f87f36deda0  aither-v2/tools/aither-agent-tool-metrics
0d73e728568da726d94f0355293df8b4279d70b77bcf9fb64d9bee8628d38451  docs/evidence/AITHER_QWEN38_VLLM_HERMES_R7_SCENARIOS.json
```

## Permitted transport differences (only)

- `base` = `http://127.0.0.1:18000` (port-forward to `svc/vllm-qwen38-27b-fp8:8000`)
- `model` = `qwen3.8-27b` (production served-model-name)
- `key`  = production vLLM API key (not committed)

## Forbidden differences — none

Tool definitions, tool schemas, simulator semantics, evidence matching, scoring,
router rules, replan logic, pass thresholds, scenario content, required evidence,
root concepts, prohibited actions, final-schema semantics: UNCHANGED.

## Verdict

`R7C1_CONTROL_INTEGRITY = PASS`
