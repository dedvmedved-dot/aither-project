# Aither — R8 Candidate C-C2 Runtime Config

TASK: AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-C-C2-RUNTIME-FEASIBILITY-AND-PREFLIGHT
CANDIDATE: moonshotai/Kimi-Linear-48B-A3B-Instruct

## Backend identity (pinned)

- backend: vLLM
- version: 0.27.1
- image digest: sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967
- CUDA/driver: host n7 (to be captured at runtime)
- PyTorch/Triton: bundled in vLLM image (to be captured at runtime)

## Model / representation

- model: /model (hostPath /data/models/Kimi-Linear-48B-A3B-Instruct-AWQ-4bit)
- base revision: e1df551a447157d4658b573f9a695d57658590e9
- representation repo: cyankiwi/Kimi-Linear-48B-A3B-Instruct-AWQ-4bit (rev 5d029d1844aa64ec302e14466be7d0353c6e697f)
- quantization: compressed-tensors int4 (group_size 32, symmetric, weight-only)

## vLLM args (LAB manifest)

- --served-model-name kimi-linear-48b-a3b-candidate-c-c2
- --tensor-parallel-size 2
- --max-num-seqs 1
- --gpu-memory-utilization 0.90
- --max-model-len 16384 (start; staircase 16K->64K)
- --dtype half (FP16 override; int4 Marlin-class kernel uses FP16; Triton KDA is dtype-generic)
- --quantization compressed-tensors
- --trust-remote-code (required for configuration_kimi/modeling_kimi/tokenization_kimi)
- --enforce-eager (avoid CUDA graph OOM on sm75)
- --enable-auto-tool-choice (tool parser auto-detected; no Kimi-specific parser in vLLM 0.27.1)
- --generation-config vllm
- env: PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True, VLLM_ALLOW_LONG_MAX_MODEL_LEN=1

## Constraints

- Concurrency=1, speculative=OFF, MTP=OFF, CUDA Graph=OFF (enforce-eager), optimization tuning=OFF.
- No production route / Portal / BFF / Identity change.
