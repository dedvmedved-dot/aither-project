# Aither — R8 Candidate D-C1 Restore evidence

TASK: AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-D-C1-CORRECTIVE-QUALIFICATION-CLOSURE

## Teardown

- `kubectl delete -f llamacpp-gpt-oss-20b-candidate-d-lab.yaml` -> deployment + service deleted
- CANDIDATE_D_LAB_REMOVED=YES
- (weights preserved at /data/models/gpt-oss-20b-GGUF)

## Restore

- `kubectl -n aither-inference scale deploy vllm-qwen38-27b-fp8 --replicas=1` -> scaled
- New pod vllm-qwen38-27b-fp8-57b74959dd-4nxj9 on n7
- Ready=True, restartCount=0
- /health=200, /v1/models contains qwen3.8-27b
- basic chat PASS, tool-call smoke PASS (get_weather)

QWEN38_RESTORED=YES
QWEN38_HEALTH=PASS
QWEN38_CHAT=PASS
QWEN38_TOOL=PASS
N8_UNCHANGED=YES
ROUTING_UNCHANGED=YES
AGENT_UNCHANGED=YES
