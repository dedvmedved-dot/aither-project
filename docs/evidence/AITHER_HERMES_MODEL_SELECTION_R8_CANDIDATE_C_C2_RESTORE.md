# Aither — R8 Candidate C-C2 Restore evidence

TASK: AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-C-C2-RUNTIME-FEASIBILITY-AND-PREFLIGHT

## Teardown

- `kubectl delete -f vllm-kimi-linear-48b-a3b-candidate-c-c2-lab.yaml` -> deployment + service deleted
- CANDIDATE_C_LAB_REMOVED=YES
- (downloaded weights preserved at /data/models/Kimi-Linear-48B-A3B-Instruct-AWQ-4bit, not deleted)

## Restore

- `kubectl -n aither-inference scale deploy vllm-qwen38-27b-fp8 --replicas=1` -> scaled
- New pod vllm-qwen38-27b-fp8-57b74959dd-5gcn7 on n7
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
