# Aither — R8 Candidate A: Qwen3.8 restore evidence

TASK: `AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-A-N7-MAINTENANCE`
DATE: 2026-09-02

## Teardown

- `kubectl delete -f llamacpp-hermes43-36b-r8-candidate-a-lab.yaml` → deployment + service deleted
- No Candidate A pod/GPU process remains
- CANDIDATE_A_LAB_REMOVED=YES
- (model weights preserved at /data/models/Hermes-4.3-36B-GGUF, not deleted per §28)

## Restore

- `kubectl -n aither-inference scale deploy vllm-qwen38-27b-fp8 --replicas=1` → scaled
- New pod `vllm-qwen38-27b-fp8-57b74959dd-xzzh8` on n7
- Ready=True, restartCount=0
- imageID = `docker.io/vllm/vllm-openai@sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967` (canonical)
- /health = HTTP 200
- /v1/models contains `qwen3.8-27b`, max_model_len=65536
- basic chat = PASS
- tool-call smoke = PASS (get_weather tool call returned correctly)
- nvidia-smi n7: GPU0/1 used 19067 MiB each (FP8 model restored)

## Post-restore verification

- QWEN38_RESTORED=YES
- POST_RESTORE_QWEN38_HEALTH=PASS
- POST_RESTORE_BASIC_CHAT=PASS
- POST_RESTORE_TOOL_SMOKE=PASS
- N8_QWEN32_CHANGED=NO (pod `vllm-qwen3-32b-awq-59bd8f7d75-zzj9g` Ready=True, restart=0, unchanged)
