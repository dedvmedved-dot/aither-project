# AITHER QWEN38 VLLM HERMES AGENT ORCHESTRATION R6 — Evidence

- TASK: `AITHER-QWEN38-VLLM-HERMES-AGENT-ORCHESTRATION-QUALIFICATION-R6`
- EXECUTOR: HERMES
- MODE: FORCE_MAJEURE / MANUAL / HERMES
- BASELINE SHA: `4d88db5db2e070bf35e7594e1e1ad508dc5d5c33`
- PARENT SHA: `4d88db5db2e070bf35e7594e1e1ad508dc5d5c33`
- BRANCH: `aither-v2`
- FINAL SHA: `<after-commit>`

## 1. Runtime (production vLLM FP8, READ-ONLY)

- image `vllm/vllm-openai@sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967`
  (pod imageID == pinned digest). Served `qwen3.8-27b`, reasoning parser `qwen3`, tool parser
  `qwen3_xml`, `--enable-auto-tool-choice`, 65536 context. Production NOT modified.
- Secret read at runtime only (value never logged). Pod Ready, restartCount 0 throughout.

## 2. Methodology (corrected vs R5)

- Semantic tool simulator: normalized fact lookup (tool, args) -> canonical key -> fact; equivalent
  queries (pod hash suffixes, service names) resolve to the same fact; missing objects return
  realistic "no data" (not generic "no fixture data").
- 50 UNIQUE scenarios (LINUX 5 / NETWORK 5 / K8s 8 / CONTAINER 4 / STORAGE 6 / KVM 3 / GIT+CI 5 /
  CODE 6 / SECURITY 4 / CROSS 4). No duplicated case counted as unique.
- Structured causal answer key per scenario: ROOT_CAUSE (+synonyms), CAUSAL_LINK, REQUIRED_EVIDENCE,
  PROHIBITED_CONCLUSIONS, SAFE_REMEDIATION, RELEVANT_TOOL_GROUPS.
- Causal scoring (no keyword-all): ROOT_CAUSE_CORRECT / CAUSAL_LINK_CORRECT / EVIDENCE_COVERAGE /
  REMEDIATION_SAFE / PROHIBITED_HIT. Scenario PASS = root+causal+evidence>=0.8+remediation and no
  prohibited hit.
- Tool scoring: PRECISION (relevant non-dup / total non-dup), RECALL (evidence sources accessed /
  expected), F1.
- Tool groups (FILES/LINUX/KUBERNETES/GIT/NETWORK) + P0 rule-based router (MODE B "routed" exposes
  only the scenario's relevant groups; MODE A "full" exposes all 14).
- Loop control: no re-execute of identical tool+args; after 3 consecutive non-informative -> stop
  tool phase. MAX_TOOL_ROUNDS=12.
- Final synthesis: STATELESS fresh request, no tools, no prior tool_calls, structured format,
  thinking OFF (F0) vs ON (F1). Tool phase always enable_thinking=false.

## 3. Results — MODE B routed, final synthesis F1 (thinking ON)

50 scenarios:
- TASK_SUCCESS: **18.0%** (full causal gate).
- ROOT_CAUSE_CORRECT: **78.0%**.
- FINAL_NONEMPTY: **100.0%**.
- JSON_VALIDITY: **100.0%**. UNSAFE 0. HALLUCINATED 0. DUPLICATE 2. NONINFORMATIVE 193. IRRELEVANT 0.
- TOOL_PRECISION 100.0% / TOOL_RECALL 23.0% / TOOL_F1 26.1%.

## 4. Final synthesis A/B (F0 thinking OFF vs F1 thinking ON, routed, identical ledger)

- F0 (off): TASK_SUCCESS **20.0%**, ROOT_CAUSE_CORRECT **76.0%**.
- F1 (on): TASK_SUCCESS **18.0%**, ROOT_CAUSE_CORRECT **78.0%**.
- FINAL_NONEMPTY 100% both; TOOL_PRECISION/RECALL/F1 identical (100/23/26).

F0 vs F1 differ only within noise. The "final synthesis = thinking ON" hypothesis yields no material
gain over OFF for diagnostic completeness.

Interpretation: the semantic simulator + routing + stateless synthesis fixed the earlier defects
(FINAL_NONEMPTY 0->100%, duplicate 50->2, root-cause 34->78%). The model names the correct root
cause in ~76-78% of cases, but the FULL causal diagnosis (root + causal link + >=0.8 evidence
coverage + safe remediation) is only ~18-20% — the model frequently cites partial evidence and a
weak causal link, falling below the >=90% hard gate.

## 5. Conclusion

Orchestration (semantic simulator + routing + loop control + stateless thinking-ON synthesis)
substantially improves Qwen3.8-FP8 agent behaviour, but measured diagnostic completeness remains
below the hard gates (root cause 78%, full task success 18% — both < 90%).

**HERMES_DEVOPS_64K_RECOMMENDATION_CANDIDATE = NONE** on vLLM FP8 orchestrated.

## 6. Immutability

Production Qwen3.8/Qwen3-32B/Portal/BFF/Identity/nginx/routing/.agent: NO changes. MTP OFF.
AI_CODEX_USED NO. AUTOMATED_RUNNER_USED NO. SECRETS_EXPOSED NO.
