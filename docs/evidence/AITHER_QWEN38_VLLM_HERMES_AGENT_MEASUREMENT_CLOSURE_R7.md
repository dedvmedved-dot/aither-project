# AITHER QWEN38 VLLM HERMES AGENT MEASUREMENT CLOSURE R7 — Evidence

- TASK: `AITHER-QWEN38-VLLM-HERMES-AGENT-MEASUREMENT-CLOSURE-R7`
- EXECUTOR: HERMES
- MODE: FORCE_MAJEURE / MANUAL / HERMES
- BASELINE SHA: `d2aefedb061a10f9a316feab90442df45ddb471b`
- PARENT SHA: `d2aefedb061a10f9a316feab90442df45ddb471b`
- BRANCH: `aither-v2`
- FINAL SHA: `<after-commit>`

## 1. Measurement framework (corrected vs R6)

- **Evidence-ID world simulator**: each scenario has structured evidence facts with IDs; tools query
  them semantically (pod/pods equivalence, hashed-pod normalization, service names, command
  variants); missing objects return realistic not_found/empty/unsupported, never "no data".
- **Simulator contract test**: SIMULATOR_REQUIRED_EVIDENCE_REACHABILITY = **100% (73/73)**.
- **50 UNIQUE scenarios** (LINUX 5 / NETWORK 5 / K8s 8 / CONTAINER 4 / STORAGE 6 / KVM 3 / GIT+CI 5 /
  CODE 6 / SECURITY 4 / CROSS 4); DUPLICATE_SCENARIO_COUNT = **0**.
- **Router independent of answer key**: P0 derives groups from prompt text only; P1/P2 are Qwen
  planners returning JSON {"groups":[...]} with no tool access and no answer key.
- **Machine-readable final**: JSON schema `{root_cause_summary, evidence_ids, causal_explanation,
  remediation_steps, risks, missing_data, confidence}`; schema validation mandatory.
- **Evidence-ID scoring**: root cause via concept rubric (accepted + rejected confounders), evidence
  coverage via exact evidence IDs, causal = root + causal-evidence-id, remediation via action class.

## 2. Runtime (production vLLM FP8, READ-ONLY)

image `vllm/vllm-openai@sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967`
(pod imageID == digest). Served `qwen3.8-27b`, qwen3/qwen3_xml, auto-tools, 65536. Not modified.
Pod Ready, restartCount 0 throughout. Secret read at runtime only.

## 3. Router A/B (50 scenarios each)

- P0 (rule-based): GROUP_RECALL 85.0% / GROUP_PRECISION 78.6% / GROUP_F1 76.7% / MISSED 24.0%.
- P1 (thinking=false): GROUP_RECALL 86.0% / PRECISION 69.3% / F1 73.8% / MISSED 20.0%.
- P2 (thinking=true): GROUP_RECALL 72.0% / PRECISION 56.0% / F1 60.6% / MISSED 32.0%.

**No router meets the safety gate (MISSED_REQUIRED_GROUP_RATE <=2%).** Per task §9, **FULL catalog
becomes the primary tool policy** (all 14 tools).

## 4. Execution — FULL catalog (all 14 tools), F0 vs F1

50 scenarios each:

| profile | TASK_SUCCESS | ROOT_CAUSE | EVIDENCE_DISCOVERY | SCHEMA | JSON_TOOL_ARGS |
|---|---|---|---|---|---|
| FULL F0 (thinking off) | 4.0% | 72.0% | 21.0% | 100.0% | 100.0% |
| FULL F1 (thinking on) | 2.0% | 62.0% | 21.0% | 76.0% | 100.0% |

UNSAFE 0, HALLUCINATED 0, DUPLICATE 7, HTTP 5xx 0 (both).

**F0 > F1**: thinking ON in the final synthesis lowers root-cause (62 vs 72) and breaks the JSON
schema (76 vs 100). The "final synthesis = thinking ON" hypothesis is REJECTED.

## 5. Hard-gate assessment (best valid profile = FULL F0)

- TASK_SUCCESS 4.0% (gate >=90%) — FAIL.
- ROOT_CAUSE_CORRECT 72.0% (>=90%) — FAIL.
- REQUIRED_EVIDENCE_DISCOVERY 21.0% (>=95%) — FAIL.
- TOOL_PRECISION/RECALL/F1 — FAIL (evidence discovery too low; model over-explores the 14-tool
  catalog with many not_found/empty probes).
- FINAL_SCHEMA_VALID 100% — PASS. JSON_TOOL_ARGS_VALID 100% — PASS.
- HALLUCINATED 0 / UNSAFE 0 / HTTP 5xx 0 — PASS.

## 6. Completeness note

56K/58K long-horizon, 60K edge semantic, and 150-sequential stability were NOT run within R7
budget. The short-suite (50 scenarios × FULL F0/F1) hard gates already fail by a wide margin
(4% vs 90% task success, 21% vs 95% evidence discovery); these completeness items would not change
the conclusion but are recorded as gaps.

## 7. Decision

Measurement integrity **PASS** (simulator reachability 100%, 50 unique scenarios, routers P0/P1/P2
run, FULL F0/F1 run, evidence-ID scoring, JSON schema). Hard gates **FAIL** (task success 4%,
root cause 72%, evidence discovery 21% — all far below 90/95%).

**CANDIDATE STATUS = NONE_MODEL_LIMIT_CONFIRMED** — with correctly measured orchestration, the
Qwen3.8-27B FP8 + vLLM agent does not reach Hermes DevOps accuracy requirements. The primary
deficit is evidence discovery (21%): with the full 14-tool catalog the model over-explores and
does not reliably reach the required evidence, so the complete causal diagnosis fails even though
the root-cause guess is right ~72% of the time.

## 8. Immutability

Production Qwen3.8/Qwen3-32B/Portal/BFF/Identity/nginx/routing/.agent: NO changes. MTP OFF.
AI_CODEX_USED NO. AUTOMATED_RUNNER_USED NO. SECRETS_EXPOSED NO.
