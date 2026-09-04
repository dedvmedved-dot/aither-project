# Aither — R8 Candidate B Report

TASK: `AITHER-HERMES-AGENT-MODEL-SELECTION-R8`
CANDIDATE: B
MODEL: `Qwen/Qwen3-Coder-30B-A3B-Instruct`
MODEL REVISION: `b2cff646eb4bb1d68355c01b18ae02e7cf42d120`
ARCHITECTURE: Qwen3MoeForCausalLM (MoE)
TOTAL PARAMETERS: ~30B (128 experts)
ACTIVE PARAMETERS: ~3B (8 experts / token)
QUANTIZATION: FP8 (official `Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8`)
BACKEND: vLLM 0.27.1 (tp2)
IMAGE DIGEST: `sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967`

## Maintenance

- BASELINE: `3176ab36d7ba397c63098be78dc9293d7747b58f`
- ARCHITECT_TEMPORARY_N7_MAINTENANCE_AUTHORIZED: YES
- QWEN38_TEMP_SCALE_DOWN: 1_TO_0
- ACTIVE_TRAFFIC_GATE: PASS (idle)
- GPU_RELEASE: PASS
- MEMORY_FEASIBILITY_64K: PASS (FP8 31.2 GB + KV ~6.3 GB, ~20.5 GB/GPU used)

## Preflight

- PREFLIGHT: PASS (31 deterministic tool calls; JSON validity 31/31, unknown 0, unsafe 0, malformed 0, HTTP5xx 0)

## R7-C1 benchmark (native F0 only — non-thinking model)

| Metric | FULL | ROUTED |
|---|---|---|
| TASK_SUCCESS | 4.0% | 2.0% |
| ROOT_CAUSE_CORRECT | 70.0% | 68.0% |
| EVIDENCE_DISCOVERY (per-scenario avg) | 27.0% | 23.0% |
| FINAL_SCHEMA_VALID | 100.0% | 100.0% |

Tool metrics (global, task-defined):

| Metric | FULL | ROUTED |
|---|---|---|
| REQUIRED_EVIDENCE_DISCOVERY | 34.3% | 27.4% |
| TOOL_PRECISION | 9.6% | 10.5% |
| TOOL_RECALL | 34.3% | 27.4% |
| TOOL_F1 | 15.0% | 15.2% |
| IRRELEVANT_CALL_RATE | 90.4% | 89.5% |
| DUPLICATE_CALL_RATE | 4.1% | 5.5% |
| ERROR_RECOVERY_RATE | 6.7% | 7.3% |

JSON_TOOL_ARGS_VALID: 100%
HALLUCINATED_TOOL_RATE: 1 hallucinated tool (gate FAIL)
UNSAFE_ACTION_RATE: 0%
HTTP_5XX: 0
THINKING_AB: NOT_SUPPORTED (non-thinking model)

## Long context

- 56K: 0/5; 58K: 0/5; 60K: 0/3 (0/13, all root_correct=False)

## Comparison (three candidates)

| Metric | Qwen3.8 | Hermes-4.3-36B | Qwen3-Coder-30B-A3B |
|---|---|---|---|
| TASK_SUCCESS | 2% | **8%** | 4% |
| ROOT_CAUSE | 62% | **78%** | 70% |
| FULL EVIDENCE DISCOVERY (global) | 20.6% | 27.4% | **34.3%** |
| TOOL_PRECISION | 6.8% | 7.6% | **9.6%** |
| TOOL_F1 | 10% | 11.9% | **15.0%** |
| ERROR_RECOVERY | 20% | **26.5%** | 6.7% |
| DUPLICATE_RATE | 1.5% | 16.6% | **4.1%** |
| JSON_TOOL_ARGS | 100% | 98.2% | **100%** |
| 60K | 0/3 | 0/3 | 0/3 |

## Verdict

- QWEN38_BASELINE_BEATEN: YES (better root cause, evidence discovery, tool precision/F1)
- CANDIDATE_A_BEATEN: NO (mixed: Qwen3-Coder better on tool metrics + evidence discovery, but worse on TASK_SUCCESS 4% vs 8%, ROOT_CAUSE 70% vs 78%, and ERROR_RECOVERY 6.7% vs 26.5%; also 1 hallucinated tool)
- HERMES HARD GATE: FAIL (all functional gates far below; HALL=1 violates HALLUCINATED_TOOL_RATE=0%)
- CANDIDATE STATUS: **HERMES_R8_CANDIDATE_B_REJECTED**

Qwen3-Coder-30B-A3B shows the best raw tool-calling mechanics of the three (precision/F1/JSON/duplicate),
but its causal diagnosis and error recovery are too weak for the autonomous Hermes DevOps core, and it
hallucinated one tool. Not recommended. Final decision belongs to ChatGPT after independent GitHub
Connector audit.
