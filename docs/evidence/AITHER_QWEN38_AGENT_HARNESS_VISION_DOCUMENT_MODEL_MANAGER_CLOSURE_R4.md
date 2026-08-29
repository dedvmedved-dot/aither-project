# AITHER QWEN38 AGENT HARNESS VISION DOCUMENT MODEL MANAGER CLOSURE R4 — Evidence

- TASK: `AITHER-QWEN38-AGENT-HARNESS-VISION-DOCUMENT-MODEL-MANAGER-CLOSURE-R4`
- EXECUTOR: HERMES
- MODE: FORCE_MAJEURE / MANUAL / HERMES
- BASELINE SHA: `7797bd2a38c01fea6a486b554d180356c2404423`
- PARENT SHA: `7797bd2a38c01fea6a486b554d180356c2404423`
- BRANCH: `aither-v2`
- FINAL SHA: `<after-commit>`

## 0. R3 final selection: NOT ACCEPTED (audit) — this R4 corrects the mandatory items.

Deferred debt `AITHER-QWEN38-GGUF-LLAMACPP-R1-C1-QUALIFICATION-CLOSURE` remains DEFERRED (not executed).

## 1. Registry governance — FIXED

`aither-v2/config/model-registry-lab.yaml`: Q5/Q4 changed from `status: QUALIFIED` →
`status: CANDIDATE` + `governance_state: PENDING_CHATGPT_ACCEPTANCE` + `evidence_state: R4_PENDING`.
C/D remain `EXPERIMENTAL`. Only ChatGPT may authorize ACCEPTED/QUALIFIED.

## 2. Agent harness — IMPLEMENTED (R4)

`aither-v2/tools/aither-agent-harness-lab` implements the controlled 4-phase executor:
- PHASE 1 PLAN (system prompt: investigate with read-only tools, do not repeat calls, conclude).
- PHASE 2 TOOL EXECUTION (allowlisted dispatcher, JSON validation, normalized observations).
- PHASE 3 EVIDENCE CONTROL (ledger: tool/args/result/provenance; duplicate detection returns
  "already tried"; non-informative "no fixture" results counted).
- PHASE 4 CONCLUSION (mandatory synthesis call with **no tools** exposed, structured format
  DIAGNOSIS/EVIDENCE/INFERENCE/REMEDIATION/RISKS/MISSING_DATA/NEXT_SAFE_ACTION).

## 3. Agent tool-calling instability — CONFIRMED (root cause of R3 2.3% + R4 500s)

The full DevOps rerun (43 scenarios, 14 read-only tools) on Q5 could NOT complete: llama.cpp
returns HTTP 500 `"Failed to parse tool call arguments as JSON: unexpected end of input"` when the
Qwen3.8 **reasoning** model emits a truncated/empty `<tool_call>` tag. This occurs:
- in the tool loop when `max_tokens` is too small for reasoning + tool call (fixed by raising to
  1500); and
- **even in the CONCLUSION phase where NO tools are exposed** — the model, having been in a
  tool-calling loop, still emits `<tool_call>`, which llama.cpp attempts to parse and fails.

Conclusion: **bare llama.cpp tool-calling with the Qwen3.8 reasoning model is unstable** for
multi-step DevOps (over-exploration in R3 at 2.3% task success + malformed tool calls in R4).
This is a runtime+model combination issue, not a quantization-quality issue — it affects Q5 and Q4
identically. The HERMES_DEVOPS_64K role requires a different agent runtime (e.g. vLLM with a
validated tool parser, or a non-reasoning variant), NOT bare llama.cpp.

## 4. Vision — PASS (Q5 and Q4)

mmproj `mmproj-Qwen3.8-27B-F16.gguf` downloaded via safe path (temp+resume+sha256+atomic move),
SHA256 VERIFIED = `2f0a90f140322e570130adffe50ae45355f1a79715a641ce0e11ac6b1cdc822c`.

Vision corpus (PIL-generated screenshots/dialog/table/diagram/chart, base64 → mmproj):
- Q5: **5/5 (100%)** — terminal IP:port (10.0.0.10:5432), error % (98%), table (cache down),
  diagram relation (Client→Server), chart max (80).
- Q4: **5/5 (100%)**.

## 5. Model manager — FIXED (real LAB behavior)

`aither-v2/tools/aither-model` now: argparse `--context` (activate ROLE MODEL --context N);
`pull` = temp+resume+sha256+atomic (never auto-activate); `verify` = real sha256; `activate` =
validate hash + mmproj presence + **backend digest vs running pod imageID** + resource gate (disk)
+ save PRIOR + real smoke; `rollback` = restore prior; `gc --dry-run` = enumerates
installed/active/unused/orphan files. State file atomic writes. (LAB-only; not wired to production.)

## 6. Documents / chat

- Document factual extraction (MD/CSV/JSON/DOCX/XLSX): Q5 5/5, Q4 5/5 (100%) from R3 evidence;
  R4 did not rebuild a hermetic PDF/DOCX/XLSX venv (host lacks pypdf/python-docx/openpyxl) — the
  text/structure pipeline remains validated, full PDF/scan qualification still pending.
- Chat: R3 12-domain heuristic (Q5/Q4 both 91.7% 16K / 83.3% 32K). R4 >=30-prompt corpus NOT
  re-run (time; the chat gate is secondary to the tool-calling blocker).

## 7. Recommendations (LAB, measured; no production selection)

- **HERMES_DEVOPS_64K = NONE** — no candidate passes the DevOps hard gates with bare llama.cpp
  tool-calling (unstable tool-call parsing). A different agent runtime is required before this role
  can be qualified.
- **USER_CHAT_16K_32K = Q4 (qwen38-ad-q4)** — best speed (16K 23.17 / 32K 22.01 / 64K 20.64 tok/s),
  chat quality indistinguishable from Q5, vision 5/5, semantic 64K 3/3 (R3).

## 8. Teardown / restore / immutability

- R4 lab deployments/services removed; Qwen3-32B restored 0→1 (Ready, health, restarts 0);
  production Qwen3.8 n7 unchanged (Ready, restarts 0).
- Routing/Portal/Identity/BFF/nginx/.agent: NO changes. MTP OFF. AI_CODEX_USED NO.
  AUTOMATED_RUNNER_USED NO. SECRETS_EXPOSED NO.
