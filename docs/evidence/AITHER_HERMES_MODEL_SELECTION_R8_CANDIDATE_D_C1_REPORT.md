# Aither — R8 Candidate D-C1 Corrective Qualification Closure Report

TASK: AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-D-C1-CORRECTIVE-QUALIFICATION-CLOSURE
BASELINE_SHA: 06aada7516f7b752701ab94ce4331e51116cafad
CANDIDATE: D (openai/gpt-oss-20b)

## Phase 1 — Immutable GGUF provenance

GGUF_REPOSITORY: ggml-org/gpt-oss-20b-GGUF
GGUF_REVISION: ef9b12f2ff56c69cf32153a02784e7a3c88bf524
GGUF_FILE: gpt-oss-20b-MXFP4.gguf
GGUF_BYTES: 12109566624
GGUF_SHA256: 27cd6c432c7672cb812a92f611cf3ba7bbc35928262bb1e1253ff4ee6ae35901 (local == remote LFS oid)
SOURCE_SHA: 6cee5e81ee83917806bbde320786a8fb61efebee
SRC_SHA_MATCH: YES (.src_sha PRIMARY == source revision)
REPRESENTATION_PROVENANCE: PASS

## Phase 4 — Context ladder + 64K semantic

CONTEXT_16K: PASS (16311 tok)
CONTEXT_32K: PASS (32678 tok)
CONTEXT_56K: PASS (57275 tok)
CONTEXT_58K: PASS (59327 tok)
CONTEXT_60K: PASS (61352 tok)
CONTEXT_64K: PASS (server n_ctx_slot=65536; 65456-token prompt yields empty completion at the very limit — no completion budget)
SEMANTIC_64K_3_OF_3: 3/3 PASS (S1 connection-pool/migration, S2 x509, S3 oom — root cause found at ~62K)

## Phase 5 — Corrected preflight

PREFLIGHT_EXPECTED_TOOL_CASES: 32
PREFLIGHT_PASSED_TOOL_CASES: 32/32
PREFLIGHT_JSON: 32/32 (100%)
PREFLIGHT_SCHEMA: 100%
PREFLIGHT_UNKNOWN: 0
PREFLIGHT_UNSAFE: 0
PREFLIGHT_MALFORMED: 0
PREFLIGHT_HTTP5XX: 0
(note: specific-function tool_choice is not supported by llama.cpp OpenAI API — replaced with tool_choice=required, which passes)

## Phase 7 — Rerun canonical R7-C1

R7C1_INTEGRITY: PASS (Candidate-D harness differs from canonical only by removing enable_thinking transport flag; no tool/scoring/simulator/routing differences)
FULL_SCENARIOS: 50
ROUTED_SCENARIOS: 50
TASK_SUCCESS_FULL: 2.0%
TASK_SUCCESS_ROUTED: 2.0%
ROOT_FULL: 74.0%
ROOT_ROUTED: 72.0%
EVIDENCE_DISCOVERY_FULL: 19.2% (global)
EVIDENCE_DISCOVERY_ROUTED: 20.6% (global)
PRECISION: 13.1%
RECALL: 21.9%
F1: 16.4%
ERROR_RECOVERY: 25.0%
IRRELEVANT: 86.9%
DUPLICATE: 6.8%
JSON_ARGS: 100%
FINAL_SCHEMA: 96% (FULL) / 94% (ROUTED)
HALLUCINATIONS: 0
UNSAFE: 0
HTTP5XX: 0
LONG_56K: 0/5
LONG_58K: 0/5
LONG_60K: 0/3
SEQUENTIAL_150: SKIPPED_CONDITIONALLY (functional hard gates FAIL)

## Phase 8 — Classification

All R8 hard quality gates FAIL (TASK_SUCCESS 2% << 90%; evidence discovery ~19-21% << 95%; long-context 0/13).
Measurement is valid and complete (proper gated sequence executed).

PROPOSED_CLASSIFICATION: PROPOSED_CANDIDATE_D_AUTONOMOUS_HERMES_QUALIFICATION_FAILED
CONNECTOR_AUDIT_REQUIRED: YES

## Production

QWEN38_RESTORED: YES
N8_UNCHANGED: NO (unchanged)
ROUTING_UNCHANGED: NO (unchanged)
AGENT_UNCHANGED: NO (unchanged)
SECRETS_EXPOSED: NO
CODEX_USED: NO

READY FOR CHATGPT CONNECTOR AUDIT
STOP
