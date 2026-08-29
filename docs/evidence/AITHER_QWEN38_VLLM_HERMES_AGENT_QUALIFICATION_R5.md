# AITHER QWEN38 VLLM HERMES AGENT QUALIFICATION R5 — Evidence

- TASK: `AITHER-QWEN38-VLLM-HERMES-AGENT-QUALIFICATION-R5`
- EXECUTOR: HERMES
- MODE: FORCE_MAJEURE / MANUAL / HERMES
- BASELINE SHA: `31f3c0baf17062e55aa21a20f264fb870cf04dc4`
- PARENT SHA: `31f3c0baf17062e55aa21a20f264fb870cf04dc4`
- BRANCH: `aither-v2`
- FINAL SHA: `<after-commit>`

## 1. Runtime provenance (production vLLM FP8, READ-ONLY)

- Deployment `vllm-qwen38-27b-fp8`, image `vllm/vllm-openai@sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967`
  (pod imageID == pinned digest — VERIFIED).
- Served model `qwen3.8-27b`, `--reasoning-parser qwen3`, `--tool-call-parser qwen3_xml`,
  `--enable-auto-tool-choice`, `--max-model-len 65536`, `--max-num-seqs 1`, `--enforce-eager`.
  Runtime matches canonical manifest `aither-v2/services/inference/k8s/vllm-qwen38-27b-fp8.yaml`.
- Production NOT modified in R5 (no restart/edit/scale). Pod Ready, restartCount 0 throughout.
- Secret `vllm-api-key` read at runtime only (value never logged/committed).

## 2. 16-call tool-call preflight (8 prompts × thinking default/off)

Tools: get_current_weather, calculator, get_time. Prompts: weather Moscow/London/Berlin,
123*456, 2^10, 987/3, time New York/Tokyo. AUTO tool choice.

- THINKING DEFAULT: **8/8 valid**, JSON 8/8, 503 completion tokens (avg ~63), 58.2 s (avg 7.3 s).
- THINKING OFF (`chat_template_kwargs {"enable_thinking": false}`): **8/8 valid**, JSON 8/8,
  229 tokens (avg ~29), 28.6 s (avg 3.6 s).
- **16/16 valid tool calls, JSON 16/16, HTTP 5xx = 0 → PREFLIGHT PASS.**
- TOKEN_REDUCTION = −54.5%, LATENCY_REDUCTION = −50.9%.

## 3. DevOps corpus (43 scenarios, 14 simulated read-only tools, enable_thinking=false)

- TASK_SUCCESS_RATE: **62.8%** (27/43) — below the >=90% hard gate.
- FINAL_NONEMPTY_RATE: **100.0%** — the R4 empty-final defect is FIXED by the stateless
  conclusion phase (fresh request, no prior tool_calls, no tools).
- TOOL_SELECTION_ACCURACY: **83.7%** — below the >=95% gate.
- JSON_VALIDITY: **100.0%**.
- HALLUCINATED_TOOL_RATE: **0%**. UNSAFE_ACTION_RATE: **0%**. MALFORMED_TOOL_CALL: **0**. HTTP 5xx: **0**.
- DUPLICATE_TOOL_CALLS: 354. NONINFORMATIVE (no-fixture) TOOL_CALLS: 819 — the model still
  over-explores read-only tools (many "no fixture data" probes) even with thinking off.

Harness correction applied (`aither-v2/tools/aither-agent-harness-lab`):
(A) one assistant turn + N tool results; (B) malformed args recorded and not replayed;
(C) stateless conclusion (system+task+ledger, no tools, no prior tool_calls, enable_thinking=false);
(D) no re-execute of identical tool+args; (E) MAX_TOOL_ROUNDS=12; (F) evidence ledger;
(G) FINAL_NONEMPTY mandatory.

## 4. 60K semantic (edge)

- Rep 1 (47,668 prompt tokens, begin/middle/end markers): **3/3 PASS** (297.7 s).
- Rep 2 timed out at the 300 s client timeout (FP8 60K prefill+decode ~300 s/rep); reps 2–3 not
  re-run within budget. FP8 60K semantic was already established PASS in W4A16-R3 (58,998 tokens).

## 5. Conclusion

The R5 harness fixes resolved the R3/R4 tool-calling defects on vLLM (FINAL_NONEMPTY 0%→100%,
JSON 98.7%→100%, malformed 0, unsafe 0, hallucinated 0, HTTP 5xx 0), and enable_thinking=false
halves tokens and latency. BUT the core DevOps diagnostic accuracy remains **62.8% task success
(<90%) and 83.7% tool-selection (<95%)**, with persistent over-exploration (819 non-informative
probes). The hard gates are NOT met.

**HERMES_DEVOPS_64K_RECOMMENDATION_CANDIDATE = NONE** on the current vLLM FP8 + non-thinking
harness. The remaining gap is model-level diagnostic reliability (correct root-cause selection
without over-exploring), not runtime stability.

## 6. Immutability / compliance

- Production Qwen3.8/Qwen3-32B/Portal/BFF/Identity/nginx/.agent/routing: NO changes.
- MTP OFF. AI_CODEX_USED NO. AUTOMATED_RUNNER_USED NO. SECRETS_EXPOSED NO.
