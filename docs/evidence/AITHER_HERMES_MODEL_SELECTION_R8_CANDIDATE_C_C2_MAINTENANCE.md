# Aither — R8 Candidate C-C2 Maintenance evidence

TASK: AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-C-C2-RUNTIME-FEASIBILITY-AND-PREFLIGHT

## Pre-maintenance snapshot

- Deployment vllm-qwen38-27b-fp8: replicas=1, generation=17
- Pod vllm-qwen38-27b-fp8-57b74959dd-5wkc8: Ready=True, restart=0, ip=10.244.1.125
- imageID: canonical (vllm/vllm-openai@sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967)
- n8 Qwen3-32B: Ready=True restart=0 (unchanged)
- traffic: 100/100 = GET /health (idle)

ACTIVE_TRAFFIC_GATE = PASS

## Scale-down + GPU release

- `kubectl -n aither-inference scale deploy vllm-qwen38-27b-fp8 --replicas=0` -> scaled
- pod gone (No resources found)
- nvidia-smi n7: GPU0/1 23040 MiB (used 0, free 22502)

ARCHITECT_TEMPORARY_N7_MAINTENANCE_AUTHORIZED=YES
QWEN38_TEMP_SCALE_DOWN=1_TO_0
GPU_RELEASE=PASS

## Outcome

Candidate C-C2 LAB deployed and failed at startup (tokenizer/transformers version incompatibility),
then torn down. See STARTUP.md and REPORT.md.
