# Aither — R8 Candidate A: n7 maintenance window evidence

TASK: `AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-A-N7-MAINTENANCE`
CANDIDATE: NousResearch/Hermes-4.3-36B
DATE: 2026-09-02

## 1. Baseline gate
- branch = aither-v2
- HEAD = 440b9836c4d745b5f801fd3f0e9391dfda9c8bdf
- origin/aither-v2 = 440b9836c4d745b5f801fd3f0e9391dfda9c8bdf
- worktree = provenance report only (R8 scope)
- RESULT = PASS

## 2. Pre-maintenance Qwen3.8 snapshot

- Deployment: `aither-inference/vllm-qwen38-27b-fp8`
- replicas = 1
- generation = 13
- image = `vllm/vllm-openai@sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967`
- Pod = `vllm-qwen38-27b-fp8-57b74959dd-65lzb`
- Ready = True
- restartCount = 0
- node = `bootsmam-k8s-clnt01-n7-gpu`
- podIP = 10.244.1.119
- imageID = `docker.io/vllm/vllm-openai@sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967` (canonical)
- /health = HTTP 200
- /v1/models = 401 Unauthorized (API-key gate, expected)
- Service = `vllm-qwen38-27b-fp8` ClusterIP 10.97.9.59:8000
- Endpoints = 10.244.1.119:8000
- nvidia-smi n7: GPU0 23040 MiB (used 19309, free 3193); GPU1 23040 MiB (used 19309, free 3193)
- model identity = qwen3.8-27b (FP8, TP=2)

## 3. Active traffic gate

- Qwen3.8 pod log (last 200 lines): 200/200 requests are `GET /health` (readiness/liveness probes).
- Zero inference requests (`/v1/chat/completions`, `/v1/models`, `/v1/completions`) observed.
- Model is idle (reference model post NONE_MODEL_LIMIT_CONFIRMED).

ACTIVE_TRAFFIC_GATE = PASS (no critical active production traffic).

## 5. Scale down + GPU release

- `kubectl -n aither-inference scale deploy vllm-qwen38-27b-fp8 --replicas=0` → scaled
- Pod `vllm-qwen38-27b-fp8-57b74959dd-65lzb` → Terminating → gone
- nvidia-smi n7 after release:
  - GPU0: 23040 MiB, used 0, free 22502
  - GPU1: 23040 MiB, used 0, free 22502
  - no GPU processes
- host RAM: 754 GB total, 402 GB free
- /data disk: 83 GB free

ARCHITECT_TEMPORARY_N7_MAINTENANCE_AUTHORIZED=YES
QWEN38_TEMP_SCALE_DOWN=1_TO_0
GPU_RELEASE=PASS

## 6. Memory feasibility (free n7)

- Hardware: 2× Quadro RTX 6000, 22502 MiB free each (~44 GB total usable)
- Candidate Q4_K_M GGUF weights: 21.76 GB
- KV cache (GQA 8 KV-heads, head_dim 128, 64 layers):
  - per token = 2 × 64 × 8 × 128 × 2 B = 256 KB
  - 64K (65536 tokens): fp16 ≈ 16 GB; Q8_0 ≈ 8 GB; Q4_0 ≈ 4 GB
- Totals:
  - Q4_K_M + Q8_0 KV 64K ≈ 30 GB → comfortable (~14 GB headroom)
  - Q4_K_M + fp16 KV 64K ≈ 38 GB → tight (~6 GB headroom)
- 16K/32K/56K/58K/60K all ≤ 64K footprint → feasible

MEMORY_FEASIBILITY_64K=PASS

## 4. n8 / Qwen3-32B (unchanged reference)

- Pod = `vllm-qwen3-32b-awq-59bd8f7d75-zzj9g`, Ready=True, restartCount=0
- nvidia-smi n8: GPU0/1 used ~20563 MiB each (production AWQ)
- N8_QWEN32_CHANGED = NO (to be re-verified post-maintenance)
