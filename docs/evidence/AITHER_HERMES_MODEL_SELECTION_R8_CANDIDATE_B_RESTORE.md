# Aither — R8 Candidate B: Qwen3.8 restore evidence

TASK: `AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-B`
DATE: 2026-09-04

## Teardown

- `kubectl delete -f vllm-qwen3-coder-30b-a3b-r8-candidate-b-lab.yaml` → deployment + service deleted
- CANDIDATE_B_LAB_REMOVED=YES
- (model weights preserved at /data/models/Qwen3-Coder-30B-A3B-Instruct-FP8, not deleted per §29)

## Restore

- `kubectl -n aither-inference scale deploy vllm-qwen38-27b-fp8 --replicas=1` → scaled
- New pod `vllm-qwen38-27b-fp8-57b74959dd-5wkc8` on n7
- Ready=True, restartCount=0
- /health = HTTP 200
- /v1/models contains `qwen3.8-27b`
- basic chat = PASS
- tool-call smoke = PASS (get_weather)

## Post-restore

- QWEN38_RESTORED=YES
- POST_RESTORE_QWEN38_HEALTH=PASS
- POST_RESTORE_BASIC_CHAT=PASS
- POST_RESTORE_TOOL_SMOKE=PASS
- N8_QWEN32_CHANGED=NO
