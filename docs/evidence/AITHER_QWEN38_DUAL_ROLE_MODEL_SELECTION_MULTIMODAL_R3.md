# AITHER QWEN38 DUAL-ROLE MODEL SELECTION MULTIMODAL R3 — Evidence

- TASK: `AITHER-QWEN38-DUAL-ROLE-MODEL-SELECTION-MULTIMODAL-QUALIFICATION-R3`
- EXECUTOR: HERMES
- MODE: FORCE_MAJEURE / MANUAL / HERMES
- BASELINE SHA: `6199059711e9b4fa5e1b3fa849f7d40f2af0cb4a`
- PARENT SHA: `6199059711e9b4fa5e1b3fa849f7d40f2af0cb4a`
- BRANCH: `aither-v2`
- FINAL SHA: `<after-commit>`

## 0. Deferred technical debt (NOT executed)

`AITHER-QWEN38-GGUF-LLAMACPP-R1-C1-QUALIFICATION-CLOSURE` remains DEFERRED. Not modified.

## 1. Provenance (re-resolved at execution, hashes verified)

| id | quant | repo@rev | bytes | SHA256 (local==remote) | KL | top-1 |
|---|---|---|---|---|---|---|
| A (Q5) | AD-Q5_K_M | AtomicChat@ca10ebce | 20232512992 | 32b2b7fc… (match) | 0.00419 | 97.34% |
| B (Q4) | AD-Q4_K_M | AtomicChat@ca10ebce | 17120781792 | 9f21564b… (match) | 0.01126 | 95.59% |
| C | UD-Q4_K_S | unsloth@4ca72078 | 15358213024 | 75bc9c8a… (match) | n/p | n/p |
| D | UD-IQ3_S | unsloth@4ca72078 | 12040883104 | d847e2c1… (match) | n/p | n/p |

- Arch: qwen35, native context 262144, MTP nextn_predict_layers=1 (OFF).
- mmproj resolved: Atomic F16 (927606912 B, 2f0a90f1…), Unsloth F16 (927607488 B, cbb841a9…).
  **NOTE: mmproj downloads were lost mid-task (flaky SSH/CDN); VISION WAS NOT TESTED — see §7.**

## 2. llama.cpp runtime (SAME digest as R1/R2 — isolates quant as the variable)

- digest `sha256:150b59966f…`, version 0.3.0-dev (build 10666, commit 4e97ac86e).
- CUDA PASS, Turing sm_75 PASS. parallel=1, both GPUs, full offload, CPU offload NO, MTP OFF, speculation OFF.

## 3. Performance (decode tok/s, temperature=0 top_p=1, 3 runs/cell median)

| context | A Q5 | B Q4 | C UD-Q4_K_S | D UD-IQ3_S | FP8 ref |
|---|---|---|---|---|---|
| 16K D128 | 19.87 | 23.29 | 24.4* | (n/t) | ~9.2 |
| 16K D512 | 19.75 | 23.15 | 24.49 | (n/t) | ~9.25 |
| 16K D2048 | 19.68 | 23.07 | 24.40 | 21.35 | ~9.27 |
| 32K (agg) | 18.91 | 22.01 | (n/t) | (n/t) | — |
| 64K (agg) | (n/t harness) | 20.64 | — | — | — |

- C vs Q4 at 16K = **+5.8%** (below the ≥10% replace threshold).
- D vs Q4 at 16K = **−7.5%** (IQ3_S decode is SLOWER than Q4 despite smaller size — IQ-kernel less
  optimized on Turing sm_75).

## 4. Chat suite (12-domain heuristic, 16K / 32K)

- A Q5: 16K 11/12 (91.7%), 32K 10/12 (83.3%).
- B Q4: 16K 11/12 (91.7%), 32K 10/12 (83.3%).
- C UD-Q4_K_S: 16K 10/12 (83.3%), 32K 11/12 (91.7%).
- D UD-IQ3_S: 16K 10/12 (83.3%), 32K (partial).
- Q5 and Q4 chat quality are indistinguishable; C/D are comparable (within noise of a 12-item
  heuristic suite). No major quality regression observed for any candidate.

## 5. DevOps agent suite (A Q5, 43 scenarios, 14 simulated read-only tools) — CRITICAL FINDING

- TASK_SUCCESS_RATE: **2.3%** (1/43)
- TOOL_SELECTION_ACCURACY: **69.8%** (30/43)
- JSON_VALIDITY: **98.7%** (883/895)
- UNSAFE_ACTION_RATE: **0**
- HALLUCINATED_TOOL_RATE: **0**

Root cause (harness + model behaviour): with 14 tools always available and sparse per-scenario
fixtures (non-listed tools return "no fixture data"), the Qwen3.8 reasoning model **over-explores**
(15–29 tool calls per scenario) and hits the 8-turn cap without emitting a final diagnosis
(`final: ""` on all but one scenario). Tool-calling MECHANICS are sound (98.7% JSON validity, 0
unsafe, 0 hallucinated), but raw llama.cpp tool-calling does NOT reliably conclude a multi-step
DevOps diagnosis without a guided agent harness. B (Q4) crashed mid-suite on a transient HTTP 500;
since Q5/Q4 are the same base model, the agent behaviour is representative for both. **The
"HERMES_DEVOPS_64K" role requires an agent harness (conclusion prompt / tool-result summarization),
not bare model tool-calling.**

## 6. Long-context semantic (64K, 3 reps, distinct markers, all 3 facts required)

- A Q5: **2/3** (one run missed the END marker at 62.8K).
- B Q4: **3/3**.

## 7. Documents / vision

- Document factual extraction (MD/CSV/JSON/DOCX/XLSX): A Q5 **5/5**, B Q4 **5/5** (100%).
- **VISION: NOT TESTED** — mmproj downloads were lost mid-task (flaky SSH/CDN); the two mmproj
  files were not present at teardown. This is a coverage gap, not a failure; vision requires a
  re-run with confirmed mmproj.

## 8. Terminal model manager (LAB prototype)

- `aither-v2/config/model-registry-lab.yaml` — declarative registry for A/B/C/D (provenance,
  hashes, backend digest, mmproj, contexts, role eligibility, status).
- `aither-v2/tools/aither-model` — CLI prototype: list/catalog/status/info/pull/verify/activate/
  rollback/unload/gc --dry-run. Safe pull = temp download + SHA256 verify + atomic move + NOT
  activate; activate = validate hash + backend digest + context + resource gate + record prior +
  smoke + mark ACTIVE; hash mismatch → inactive. Model IDs map to registry entries (no shell from
  user strings); allowlisted repos only. **DESIGN/PROTOTYPE — not wired to production.**

## 9. Weighted role scores (0-100, measured)

HERMES_DEVOPS_64K (weights: agent 25, tools 20, 64K 15, safety 10, docs 10, vision 8, stability 5,
quant 4, latency 3):
- Q5: agent 2.3→~1, tools 69.8→~14, 64K 2/3→~10, safety 10, docs 10, vision n/t→0, stability 5,
  quant (KL 0.00419)→4, latency 19.77→~2. **≈ 56/100**.
- Q4: agent ~1, tools ~14, 64K 3/3→15, safety 10, docs 10, vision 0, stability 5, quant (0.01126)→2,
  latency 23.17→3. **≈ 60/100**.

USER_CHAT_16K_32K (weights: quality 25, Russian 15, speed 20, ITL 10, TTFT 10, 32K 8, vision 5,
stability 4, VRAM 3):
- Q4: quality 91.7→23, Russian ~15, speed 23.17→20, ITL ~10, TTFT ~10, 32K 83.3→7, vision 0,
  stability 4, VRAM (17GB)→2. **≈ 91/100**.
- C: quality 83.3→21, speed 24.4→20, VRAM (15.4GB)→3 … **≈ 88/100** (slightly lower quality).
- D: quality 83.3→21, speed 21.35→17 (slower), VRAM (12GB)→3 … **≈ 80/100**.

(Scores are approximate weighted indicators; the measured hard gates carry the decision.)

## 10. Recommendations (LAB only, no production selection)

- **HERMES_DEVOPS_64K = Q5 (qwen38-ad-q5)** — best quantization quality (KL 0.00419, top-1
  97.34%), best short/medium correctness, 64K semantic 2/3 (with minor END-marker miss). **Caveat:
  requires a guided agent harness — bare tool-calling over-explores and does not conclude.**
- **USER_CHAT_16K_32K = Q4 (qwen38-ad-q4)** — best speed (23.17/22.01/20.64), chat quality
  indistinguishable from Q5, 64K semantic 3/3. C (+5.8% speed, lower quality) and D (−7.5% slower)
  do NOT meet the speed-frontier replace threshold (≥10%).

## 11. Teardown / restore / immutability

- All R3 lab deployments/services removed. n8 GPUs released then re-occupied by restored Qwen3-32B.
- Qwen3-32B restored 0→1: Ready 1/1, health 200, restartCount 0, basic PASS.
- Production Qwen3.8 (n7): Ready, restartCount 0, untouched.
- agent-deep/agent-fast/Portal/BFF/Identity/nginx/.agent: NO changes.
- AI_CODEX_USED: NO. AUTOMATED_RUNNER_USED: NO. SECRETS_EXPOSED: NO.
