# Aither — R8-BENCHMARK-REPAIR R7-C1 v2: Final Report

TASK: `AITHER-HERMES-R8-BENCHMARK-REPAIR-R7C1-V2`
EXECUTOR: HERMES ONLY
MODE: FORCE_MAJEURE / MANUAL / HERMES
BASELINE: `60453bbcc1a978a93c8e3f2bfad75b745a8493f1`

---

## 1. Objective

Repair the R7-C1 benchmark measurement instrument (declared INVALID FOR MODEL SELECTION
by R8-CONTROL) and validate the repaired v2 instrument deterministically. No model was
qualified; no candidate was run.

---

## 2. v1 frozen (Phase 1)

`R7C1_V1_FROZEN = YES`. v1 artifacts (scenarios, harness-lab, long-context, tool-metrics,
final-ab) hashed with Git blob SHA + SHA256 + bytes + lines in
`AITHER_R8_BENCHMARK_REPAIR_R7C1_V1_FREEZE.json`.

## 3. Defect catalog (Phase 2)

Documented D1–D8 (exact-string false negative; k8s namespace false positive; object/path
identity; shell semantic-equivalence; error-classification contamination; relevance≠reveal;
preflight exact-tool; negative-control) in MD + JSON. During repair two additional
evaluator defects were found and fixed:

- **D9** remediation/prohibited word collision — `remediation_class "scale up"` (add
  capacity) falsely matched prohibited `"scale"` (`kubectl scale`). Fixed with a
  phrase-aware prohibited matcher.
- **D10** causal text never validated — `causal_ok` checked only evidence IDs, so a
  fabricated causal explanation passed. Fixed by additionally requiring the causal
  explanation to reference root concepts.

## 4. v2 semantic operation model (Phase 3)

Replaced hidden `tool + exact-string key` matching with typed semantic operations:
files (`read_file`/`list_directory`/`grep_search`), systemd (`service_status`/`journal_read`),
Kubernetes (`kube_get`/`kube_describe`/`kube_logs` with explicit namespace),
git (`git_status`/`git_diff`/`git_show`), network (`http_get`/`dns_lookup`), and a limited
deterministic shell parser for benchmark-supported read-only operations
(`disk_usage_filesystem`, `disk_usage_directory`, `ceph_status`, `drbd_status`,
`certificate_expiry`, `dns_query`, `process_list`, etc.). Unknown-but-safe commands return
`UNSUPPORTED_SEMANTIC_OPERATION` (distinct from `IRRELEVANT`).

## 5. v2 scenario contract (Phase 4)

`docs/evidence/AITHER_R7C1_V2_SCENARIOS.json` — 50 scenarios, 73 evidence items, each with
an explicit typed operation. Scenario intent/root cause/difficulty unchanged.

## 6. Result/relevance model (Phase 5) + realistic negatives (Phase 6)

Nine statuses: `RELEVANT_REVEAL`, `RELEVANT_NEGATIVE`, `IRRELEVANT`, `DUPLICATE`, `UNSAFE`,
`MALFORMED`, `UNKNOWN_TOOL`, `SCHEMA_INVALID`, `UNSUPPORTED_SEMANTIC_OPERATION`.
Invariant: `relevant != revealed`. Valid non-revealing diagnostics return deterministic
realistic negatives; wrong context never leaks evidence.

## 7. Validation results (all mandatory gates)

| Gate | Result | Status |
|---|---|---|
| Unit/regression tests | 112/112 (>=100) | PASS |
| Canonical operation reachability | 73/73 | PASS |
| Semantic-equivalence tests | 9/9 | PASS |
| Wrong-context rejection | 14/14 | PASS |
| False evidence leaks | 0 | PASS |
| Supported-negative classification | 5/5 | PASS |
| Irrelevant classification | 4/4 | PASS |
| Safety/malformed/schema/unknown/unsupported | 7/7 | PASS |
| Evaluator self-tests | 600/600 | PASS |
| Preflight v2 logic tests | 18/18 | PASS |
| Scripted positive FULL | 50/50 (TASK_SUCCESS 100%) | PASS |
| Scripted positive ROUTED | 50/50 (TASK_SUCCESS 100%) | PASS |
| Scripted long-context | 13/13 | PASS |

Scripted positive: TASK_SUCCESS 100%, ROOT 100%, EVIDENCE_DISCOVERY 100%,
TOOL_PRECISION 100%, TOOL_RECALL 100%, TOOL_F1 100%, IRRELEVANT 0%, DUPLICATE 0%,
JSON_ARGS 100%, HALLUCINATIONS 0, UNSAFE 0.

Scripted negatives separate clearly: Negative A (irrelevant) IRRELEVANT 66.7% /
TASK_SUCCESS 0%; Negative B (wrong context) FALSE_POSITIVE_REVEAL_RATE 0; Negative C
(non-investigating) TASK_SUCCESS 0% / EVIDENCE 0%.

## 8. No model qualification (Phase 19)

QWEN38_FULL_MODEL_RUN_EXECUTED = NO; CANDIDATE_A/B/C/D/E_EXECUTED = NO. No LLM was run.
All validation used deterministic scripted policies through the exact v2 simulator/evaluator.

## 9. Production immutability (Phase 21)

No production mutation performed (no kubectl mutation, no routing/n8/model change).
QWEN38_PRODUCTION_UNCHANGED = YES; N8_UNCHANGED = YES; ROUTING_UNCHANGED = YES;
AGENT_UNCHANGED = YES (`.agent/CURRENT_TASK.*` not modified).

## 10. Proposed classification

All mandatory benchmark gates pass.

`PROPOSED_R7C1_V2_BENCHMARK_VALIDATED`

Hermes does NOT assign final acceptance; final classification belongs to ChatGPT after
independent GitHub Connector audit.

SECRETS_EXPOSED: NO. CODEX_USED: NO. AUTOMATED_RUNNER_USED: NO.
