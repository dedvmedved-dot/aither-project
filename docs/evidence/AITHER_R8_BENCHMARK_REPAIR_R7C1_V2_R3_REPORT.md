# Aither — R7-C1 v2-R3 Final Correction: Final Report

TASK: `AITHER-HERMES-R8-BENCHMARK-REPAIR-R7C1-V2-R3`
EXECUTOR: HERMES ONLY
MODE: FORCE_MAJEURE / MANUAL / HERMES
BASELINE: `e1b5082bf4db2d2dae8fcd36ed4bae554f145e04`

## 1. Objective

Close the four final blockers (R3-1 reproducible converter, R3-2 namespace extraction,
R3-3 true source semantic assertions, R3-4 remove unjustified ANY) and prove the corrected
v2-R3 instrument deterministically. No model was run; no candidate was run.

## 2. Blocker closure

| Blocker | Fix |
|---|---|
| R3-1 reproducible converter | self-contained R3 converter, imports only R3 harness, deterministic, byte-identical (SHA256 d4fe03ca…), fails closed |
| R3-2 namespace extraction | explicit migration map (K8S-01→prod, X-04→default); no regex; X-04 evidence+relevance ns = default |
| R3-3 source semantic asserts | independent v1-key → typed-operation parse + real equality assertion (73/73) |
| R3-4 remove unjustified ANY | specific targets (dns hostname, disk filesystem, cert path); remaining `*`/`null` are list-all queries; UNJUSTIFIED_WILDCARDS = 0 |
| R3 cross-tool equivalence | read_file≡cat, http_get≡curl unified in matcher |

## 3. Validation results (all mandatory gates PASS)

- Converter: executable YES, reproducible YES, output SHA match YES
- Namespace audit: **16/16**; X-04 evidence ns = default, relevance ns = default
- Source semantic asserts: **73/73** (real value comparison)
- Wildcard inventory: 6 list-all values, **0 unjustified**
- Wildcard adversarial tests: **8/8**
- Cross-tool equivalence: **34/34** (>=30)
- Relevance rule audit: **50/50**
- Executable operation-dimension: **82/82** (>=80); significant fields silently ignored **0**
- Provenance assert: **10/10**; unrevealed credit **0**; fabricated credit **0**
- Evaluator R3: **700/700**; false evidence leaks **0**
- Scripted positive: FULL **50/50**, ROUTED **50/50** (TASK_SUCCESS 100%, CREDITED 100%,
  PRECISION/RECALL/F1 100%, IRRELEVANT 0%)
- Negative A-G: all expected (A irrelevant 100%, B false-reveals 0, C/D task-success 0%,
  E false-reveals 0, F/G irrelevant 100%)
- Long-context: **13/13** (56K 5/5, 58K 5/5, 60K 3/3); adversarial FAILS AS EXPECTED
- Preflight R3: **23/23**

## 4. No model qualification

QWEN38_FULL_MODEL_RUN_EXECUTED = NO; CANDIDATE_A/B/C/D/E_EXECUTED = NO.

## 5. Production immutability

No runtime mutation performed. QWEN38_PRODUCTION_UNCHANGED = YES; N8_UNCHANGED = YES;
ROUTING_UNCHANGED = YES; AGENT_UNCHANGED = YES.

## 6. Proposed classification

All mandatory R3 gates pass.

`PROPOSED_R7C1_V2_R3_BENCHMARK_VALIDATED`

Hermes does NOT assign final acceptance; final classification belongs to ChatGPT after
independent GitHub Connector audit. The next real task (Qwen3.8 control run on frozen
R7-C1 v2) is NOT started here.

SECRETS_EXPOSED: NO. CODEX_USED: NO. AUTOMATED_RUNNER_USED: NO.
