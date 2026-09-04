# Aither — R8 Candidate B: n7 maintenance window evidence

TASK: `AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-B`
CANDIDATE: Qwen3-Coder-30B-A3B
DATE: 2026-09-02

## 1. Baseline gate
- branch = aither-v2
- HEAD = 3176ab36d7ba397c63098be78dc9293d7747b58f
- origin/aither-v2 = 3176ab36d7ba397c63098be78dc9293d7747b58f
- worktree = clean
- RESULT = PASS

## 2. Pre-maintenance Qwen3.8 snapshot
- Deployment: `aither-inference/vllm-qwen38-27b-fp8`, replicas=1, generation=15
- Pod: `vllm-qwen38-27b-fp8-57b74959dd-xzzh8`, Ready=True, restart=0, ip=10.244.1.123
- n8 Qwen3-32B: `vllm-qwen3-32b-awq-59bd8f7d75-zzj9g` Ready=True restart=0

## 3. Active traffic gate
- Qwen3.8 pod log (last 100 lines): 100/100 = `GET /health` (probes), zero inference traffic.
- ACTIVE_TRAFFIC_GATE = PASS (idle)

## 4. Scale down + GPU release
- `kubectl -n aither-inference scale deploy vllm-qwen38-27b-fp8 --replicas=0` → scaled
- Pod gone (No resources found)
- nvidia-smi n7: GPU0 23040 MiB (used 0, free 22502); GPU1 23040 MiB (used 0, free 22502)

ARCHITECT_TEMPORARY_N7_MAINTENANCE_AUTHORIZED=YES
QWEN38_TEMP_SCALE_DOWN=1_TO_0
GPU_RELEASE=PASS

## 5. Representation selection
- Preferred: FP8 (official `Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8`, sha dcaee4d4dfc5ee71ad501f01f530e5652438fde0), 31.20 GB
- Fallback: AWQ 4-bit (QuantTrio, 16.83 GB)

## 6. Memory feasibility (calculated)
- FP8 weights: 31.20 GB
- KV cache 64K (GQA 4 KV-heads, 48 layers): 2×48×4×128×2 × 65536 ≈ 6.29 GB (fp16)
- vLLM overhead (eager, no CUDA graph): ~2–3 GB
- Total ≈ 39.5–40.5 GB vs 43.95 GiB usable → ~3.5–4.5 GB headroom (90–92%)
- MEMORY_FEASIBILITY_64K = PASS (tight, to be confirmed at runtime)
