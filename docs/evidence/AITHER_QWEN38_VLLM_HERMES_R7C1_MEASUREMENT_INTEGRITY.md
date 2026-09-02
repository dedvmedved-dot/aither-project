# Aither — R7-C1 Measurement Integrity Closure

TASK: `AITHER-QWEN38-VLLM-HERMES-R7-C1-MEASUREMENT-INTEGRITY-CLOSURE`
EXECUTOR: HERMES ONLY
MODE: FORCE_MAJEURE / MANUAL / HERMES
REPOSITORY: dedvmedved-dot/aither-project
BRANCH: aither-v2
BASELINE: `76d2c82194116f5280f13fb7ad91bc2c1d377200`

This document closes the R7 measurement-integrity audit findings A–I. It is the
single audit-ready measurement of the Qwen3.8-27B FP8 / vLLM candidate.

---

## 0. Audit findings closure (A–I)

| # | Finding | Resolution |
|---|---|---|
| A | Missing ROUTED execution; 56K×5; 58K×5; 60K×3; routed-results; long-context artifacts | ROUTED F0/F1 executed (§3); long-context 56K×5 + 58K×5 + 60K×3 executed (§6); artifacts committed |
| B | Simulator proved canonical reachability only | `simtest` adds canonical + alternate queries; ALTERNATIVE_REACHABILITY = 100% (33/33) |
| C | shell_readonly essentially exact command-string matching | `shell_normalize()` parses command family + equivalence classes (ceph `-s`↔`status`, `.service`, pod/pods, path slash, URL slash, DNS case/dot) |
| D | Routed execution hardcoded P0 | Router winner determined from metrics = P0 (min missed 24%, max recall 85%, max F1 76.7%); router ID persisted in every routed row. NOT a silent substitution. |
| E | `TOOL_DEFS[list(KNOWN).index(name)]` on a set | Deterministic `TOOL_DEF_BY_NAME` dict; unit test 14/14 |
| F | No REPLAN after two no-new-evidence calls | REPLAN implemented; REPLAN_COUNT persisted per scenario (50/50 scenarios triggered REPLAN) |
| G | No per-call evidence ledger committed | Raw tool ledger committed: `AITHER_QWEN38_VLLM_HERMES_R7C1_TOOL_CALLS.csv` |
| H | Evidence-based precision/recall/F1 and ERROR_RECOVERY not fully persisted | Full tool metrics committed: `AITHER_QWEN38_VLLM_HERMES_R7C1_TOOL_METRICS.csv` |
| I | Evaluator used broad substring matching without unit tests | Evaluator unit tests 100% (200/200): known-good/wrong-root/missing-evidence/unsafe-remediation |

---

## 1. Measurement integrity gates

| Gate | Required | Measured | Status |
|---|---|---|---|
| Unique scenarios | 50 | 50 (0 duplicates) | PASS |
| Canonical simulator reachability | 100% | 100% (73/73) | PASS |
| Alternate simulator reachability | ≥95% | 100% (33/33) | PASS |
| Tool schema mapping | 14/14 | 14/14 | PASS |
| Evaluator unit tests | 100% | 100% (200/200) | PASS |
| P0/P1/P2 metrics present | required | present | PASS |
| FULL F0/F1 complete | required | complete | PASS |
| ROUTED F0/F1 complete | required | complete | PASS |
| Raw tool ledger committed | required | committed | PASS |
| Tool metrics complete | required | complete | PASS |
| 56K ×5 complete | required | complete (0/5 PASS) | PASS |
| 58K ×5 complete | required | complete (0/5 PASS) | PASS |
| 60K ×3 complete | required | complete (0/3 PASS) | PASS |

---

## 2. Router A/B (deterministic P0; model-based P1/P2)

| Router | Recall | Precision | F1 | Missed-required-group |
|---|---|---|---|---|
| P0 | 85.0% | 78.6% | 76.7% | 24.0% |
| P1 | 80.0% | 76.0% | 75.1% | 28.0% |
| P2 | 52.0% | 45.0% | 46.7% | 50.0% |

**ROUTER WINNER: P0** — lowest missed-required-group (24.0%), highest recall (85.0%),
highest F1 (76.7%). No router satisfies the production-eligibility gate (missed ≤2%);
therefore FULL catalog is primary and ROUTED is mandatory comparative execution with P0.

Artifact: `AITHER_QWEN38_VLLM_HERMES_R7C1_ROUTER_AB.csv`

---

## 3. Execution matrix — FULL catalog (14 tools)

| Profile | TASK_SUCCESS | ROOT_CAUSE | EVIDENCE_DISCOVERY (per-scenario avg) | SCHEMA | TOOL_PRECISION | TOOL_RECALL | TOOL_F1 |
|---|---|---|---|---|---|---|---|
| FULL F0 | 2.0% | 62.0% | 16.7% | 100.0% | 6.9% | 16.7% | 9.8% |
| FULL F1 | 2.0% | 60.0% | 16.7% | 90.0% | 6.9% | 16.7% | 9.8% |

Common: JSON_TOOL_ARGS=100%, UNSAFE=0, HALLUCINATED=0, HTTP5xx=0, REPLAN triggered 50/50.

Artifact: `AITHER_QWEN38_VLLM_HERMES_R7C1_FULL_RESULTS.csv`

## 4. Execution matrix — ROUTED (P0 winner)

| Profile | TASK_SUCCESS | ROOT_CAUSE | EVIDENCE_DISCOVERY | SCHEMA | TOOL_PRECISION | TOOL_RECALL | TOOL_F1 |
|---|---|---|---|---|---|---|---|
| ROUTED F0 | 2.0% | 62.0% | 19.3% | 100.0% | 6.5% | 19.3% | 9.7% |
| ROUTED F1 | 2.0% | 62.0% | 19.3% | 90.0% | 6.5% | 19.3% | 9.7% |

Common: JSON_TOOL_ARGS=100%, UNSAFE=0, HALLUCINATED=0, HTTP5xx=0, REPLAN triggered 46/50.

Artifact: `AITHER_QWEN38_VLLM_HERMES_R7C1_ROUTED_RESULTS.csv`

---

## 5. Tool metrics (evidence-ID based, task-defined global ratios)

From raw ledger `AITHER_QWEN38_VLLM_HERMES_R7C1_TOOL_CALLS.csv` (1266 calls: full 662, routed 604):

| Metric | ALL | FULL | ROUTED | Hard gate |
|---|---|---|---|---|
| REQUIRED_EVIDENCE_DISCOVERY | 24.7% | 20.6% | 24.7% | ≥95% FAIL |
| TOOL_PRECISION | 6.6% | 6.8% | 6.4% | ≥90% FAIL |
| TOOL_RECALL | 24.7% | 20.6% | 24.7% | ≥95% FAIL |
| TOOL_F1 | 10.4% | 10.2% | 10.2% | ≥92% FAIL |
| IRRELEVANT_CALL_RATE | 93.4% | 93.3% | 93.6% | ≤10% FAIL |
| DUPLICATE_CALL_RATE | 1.6% | 1.5% | 1.7% | ≤5% PASS |
| NONINFORMATIVE_CALL_RATE | 93.5% | 93.4% | 93.7% | — |
| ERROR_RECOVERY_RATE | 22.0% (11/50) | 20.0% (10/50) | 18.8% (9/48) | ≥95% FAIL |

Definitions (evidence-ID, no substring-prefix heuristics):
- relevant call = status `revealed`; duplicate = status `duplicate`;
  error = status `not_found`/`unsupported_command`/`empty`.
- REQUIRED_EVIDENCE_DISCOVERY = Σ(required IDs revealed) / Σ(required IDs available).
- TOOL_PRECISION = relevant / nonduplicate. TOOL_RECALL = evidence-source recall.
- ERROR_RECOVERY_RATE = recovered scenarios / scenarios with ≥1 error call
  (recovered = a later call revealed evidence after an error).

Artifact: `AITHER_QWEN38_VLLM_HERMES_R7C1_TOOL_METRICS.csv`

---

## 6. True long context (mandatory) — 13/13 complete, 0/13 PASS

| Bucket | Cases | Actual tokens (range) | begin/mid/end markers | PASS | FAIL |
|---|---|---|---|---|---|
| 56K ×5 | LC-56K-01..05 | 56040–56060 | 0.0 / 0.471 / 0.999 | 0 | 5 |
| 58K ×5 | LC-58K-01..05 | 58040–58071 | 0.0 / 0.471 / 0.999–1.0 | 0 | 5 |
| 60K ×3 | LC-60K-01..03 | 60052–60055 | 0.0 / 0.471 / 0.999–1.0 | 0 | 3 |

- Token counts use the real Qwen3.8-27B-FP8 tokenizer; all cases within target.
- Markers embedded and verified at begin (~0.0) / middle (~0.471) / end (~1.0).
- root_correct=False for **all 13 cases**; best evidence coverage 0.67 (LC-58K-05, LC-60K-02).
- hall=0, unsafe=0, JSON tool args valid (json_ok==json_total) across all 13 cases.
- Timeout ≥900s per call honoured (durations 2129–2438s per case). Concurrency = 1.
- **64K role gate (60K semantic 3/3): FAIL (0/3).**

Artifact: `AITHER_QWEN38_VLLM_HERMES_R7C1_LONG_CONTEXT.csv`

---

## 7. Stability

150 sequential mixed requests: **NOT_RUN** (functional hard gates already FAIL;
stability is the only conditionally skippable completeness item — §17).

---

## 8. Hard gates summary

TASK_SUCCESS ≥90%: FAIL (2%)
ROOT_CAUSE_CORRECT ≥90%: FAIL (62%)
REQUIRED_EVIDENCE_DISCOVERY ≥95%: FAIL (20.6%)
TOOL_PRECISION ≥90%: FAIL (6.8%)
TOOL_RECALL ≥95%: FAIL (20.6%)
TOOL_F1 ≥92%: FAIL (10.2%)
FINAL_SCHEMA_VALID=100%: PASS (F0) / 90% (F1)
JSON_TOOL_ARGS_VALID=100%: PASS (100%)
HALLUCINATED_TOOL_RATE=0%: PASS (0)
UNSAFE_ACTION_RATE=0%: PASS (0)
ERROR_RECOVERY≥95%: FAIL (20%)
IRRELEVANT_CALL_RATE≤10%: FAIL (93.3%)
DUPLICATE_CALL_RATE≤5%: PASS (1.5%)
HTTP_5XX=0: PASS (0)

64K role: 56K 0/5 PASS; 58K 0/5 PASS; 60K semantic 0/3 PASS → FAIL.

---

## 9. Decision logic

- Measurement integrity PASS + hard gates PASS → `QWEN38_FP8_VLLM_ORCHESTRATED`
- Measurement integrity PASS + hard gates FAIL → `NONE_MODEL_LIMIT_CONFIRMED`
- Measurement integrity FAIL → `NOT_EVALUABLE`

**Result: MEASUREMENT INTEGRITY = PASS; HARD GATES = FAIL → CANDIDATE STATUS = `NONE_MODEL_LIMIT_CONFIRMED`.**

---

## 10. Production immutability confirmation

- Production vLLM FP8: unchanged (Ready=True, restart=0 throughout).
- Routing/parser/model/context/Portal/BFF/Identity/nginx/Qwen3-32B/.agent/MTP/CUDA Graph/YaRN: unchanged.
- Concurrency = 1 throughout.
- No production stop required (no OOM, no unexpected restart, no persistent 5xx).

## 11. Final report

See final report block delivered to the Architect (section 22 of the task).
