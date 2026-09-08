# Aither — R7-C1 v2-R1 Corrective Closure: Final Report

TASK: `AITHER-HERMES-R8-BENCHMARK-REPAIR-R7C1-V2-R1`
EXECUTOR: HERMES ONLY
MODE: FORCE_MAJEURE / MANUAL / HERMES
BASELINE: `bd534bc6994c2616b3fc549f6f4597153df4078b`

## 1. Objective

Close the six confirmed benchmark-invalidating defects found by the GitHub Connector
audit of v2 (`bd534bc`), and prove the corrected v2-R1 instrument deterministically.
No model was qualified; no candidate was run.

## 2. Blocker closure

| Blocker | Fix | Tests |
|---|---|---|
| R1-1 evidence provenance | credited = claimed ∩ valid ∩ revealed + 6 metrics | 9 + 700 evaluator cases |
| R1-2 service normalization | exact `.service` suffix (no rstrip charset) | 9/9 |
| R1-3 namespace semantics | prompt-derived namespace + normative map (K8S-01→prod) | 11/11 |
| R1-4 alternative diagnostics | `SocketListeners(port)` + `dns_query` families | in unit tests |
| R1-5 semantic relevance | `relevant_operation_types` (domain ∪ evidence), not tool-presence | 20/20 |
| R1-6 operation dimensions | full matcher audit; read_file≡cat unified on path | 39-row audit |

## 3. Validation results (all mandatory gates PASS)

- Total deterministic tests: **163/163** (>=160 required)
- Evidence provenance tests: 9/9; unrevealed valid-ID credit **0**; fabricated credit **0**
- Service normalization: **9/9**
- K8s semantic preservation: **11/11** (K8S-01 namespace = prod)
- Source semantic preservation: **50/50**
- Operation dimension audit: 39 operation types audited, no silently-ignored significant field
- Cross-tool relevance: **20/20**
- Evaluator R1 tests: **700/700**
- Preflight R1: **23/23** (exact-tool enforcement incl. `systemctl_status` vs `shell_readonly`)
- Scripted positive FULL: **50/50** (TASK_SUCCESS 100%, ROOT 100%, EVIDENCE 100%,
  CREDITED 100%, PRECISION 100%, RECALL 100%, F1 100%, IRRELEVANT 0%, DUPLICATE 0%)
- Scripted positive ROUTED: **50/50** (TASK_SUCCESS 100%)
- Negative A (irrelevant): IRRELEVANT 100%, TASK_SUCCESS 0%
- Negative B (wrong context): FALSE_POSITIVE_REVEALS 0
- Negative C (non-investigating): TASK_SUCCESS 0%, CREDITED 0%
- Negative D (valid-ID fabrication): TASK_SUCCESS 0%, UNREVEALED_CLAIMED 73
- Negative E (collision): FALSE_POSITIVE_REVEALS 0
- Long-context scripted: **13/13** (56K 5/5, 58K 5/5, 60K 3/3)
- Long-context fabricated-evidence adversarial: **FAILS AS EXPECTED** (claims IDs, reveals nothing → 0 credit)
- False evidence leaks: **0**

## 4. No model qualification

QWEN38_FULL_MODEL_RUN_EXECUTED = NO; CANDIDATE_A/B/C/D/E_EXECUTED = NO. All validation
used deterministic scripted policies through the v2-R1 simulator/evaluator.

## 5. Production immutability

No runtime mutation performed. QWEN38_PRODUCTION_UNCHANGED = YES; N8_UNCHANGED = YES;
ROUTING_UNCHANGED = YES; AGENT_UNCHANGED = YES (`.agent/CURRENT_TASK.*` not modified).

## 6. Proposed classification

All mandatory R1 gates pass.

`PROPOSED_R7C1_V2_R1_BENCHMARK_VALIDATED`

Hermes does NOT assign final acceptance; final classification belongs to ChatGPT after
independent GitHub Connector audit.

SECRETS_EXPOSED: NO. CODEX_USED: NO. AUTOMATED_RUNNER_USED: NO.
