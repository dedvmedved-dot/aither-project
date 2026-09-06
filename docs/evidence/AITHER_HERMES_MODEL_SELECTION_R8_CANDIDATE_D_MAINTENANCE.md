# Aither — R8 Candidate D Maintenance evidence

TASK: AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-D-GPT-OSS-20B

## Pre-maintenance snapshot

- Deployment vllm-qwen38-27b-fp8: replicas=1
- Pod vllm-qwen38-27b-fp8-57b74959dd-gpxbt: Ready=True, restart=0, ip=10.244.1.149
- n8 Qwen3-32B: unchanged
- traffic: 50/50 = GET /health (idle)

ACTIVE_TRAFFIC_GATE = PASS

## Scale-down + GPU release

- `kubectl -n aither-inference scale deploy vllm-qwen38-27b-fp8 --replicas=0` -> scaled
- pod gone; nvidia-smi n7: GPU0/1 used 0, free 22502 MiB

QWEN38_TEMP_SCALE_DOWN = 1_TO_0
GPU_RELEASE = PASS

## LAB

- llama.cpp LAB Deployment/Service `llamacpp-gpt-oss-20b-candidate-d-lab` (n7, 2 GPUs)
- model gpt-oss-20b-MXFP4.gguf (12.11 GB) loaded, n_ctx 16384 then 65536
- 64K runtime PASS (~6.5 GB/GPU used, ~16 GB free/GPU)
