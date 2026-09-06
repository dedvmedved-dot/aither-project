# Aither — R8 Candidate D Restore evidence

TASK: AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-D-GPT-OSS-20B

## Teardown

- `kubectl delete -f llamacpp-gpt-oss-20b-candidate-d-lab.yaml` -> deployment + service deleted
- CANDIDATE_D_LAB_REMOVED=YES
- (weights preserved at /data/models/gpt-oss-20b-GGUF, not deleted)

## Restore

- `kubectl -n aither-inference scale deploy vllm-qwen38-27b-fp8 --replicas=1` -> scaled
- New pod vllm-qwen38-27b-fp8-57b74959dd-6lrfs on n7
- Ready=True, restartCount=0
- /health = 200
- /v1/models contains qwen3.8-27b
- basic chat = PASS
- tool-call smoke = PASS (get_weather)

## Post-restore

- QWEN38_RESTORED=YES
- POST_RESTORE_QWEN38_HEALTH=PASS
- POST_RESTORE_BASIC_CHAT=PASS
- POST_RESTORE_TOOL_SMOKE=PASS
- N8_QWEN32_CHANGED=NO
