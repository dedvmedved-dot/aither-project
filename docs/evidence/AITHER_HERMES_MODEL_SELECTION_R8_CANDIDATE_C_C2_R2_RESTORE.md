# Aither — R8 Candidate C-C2-R2 Restore evidence

TASK: AITHER-HERMES-AGENT-MODEL-SELECTION-R8-CANDIDATE-C-C2-R2-LOW-SMEM-KDA-KERNEL-COMPATIBILITY-CLOSURE

## Teardown

- microprobe pods removed (tmp-mp3 force-deleted)
- CANDIDATE_C_LAB_REMOVED=YES (no Candidate model deployed in this task; only synthetic-tensor microprobe pods)

## Restore

- `kubectl -n aither-inference scale deploy vllm-qwen38-27b-fp8 --replicas=1` -> scaled
- New pod vllm-qwen38-27b-fp8-57b74959dd-gpxbt on n7
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
