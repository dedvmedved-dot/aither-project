# AITHER URGENT — Qwen3.8 Failed Cutover Recovery Audit R1

## Цель
После BLOCKED задачи `AITHER-URGENT-QWEN38-PERMANENT-CUTOVER-R1` и сообщения runner `restore also failed` установить фактическое runtime-состояние Aither без каких-либо изменений.

## Жёсткие ограничения
- ТОЛЬКО READ-ONLY runtime audit.
- Не менять Deployments/Services/ConfigMaps/Secrets/DB/files on host/runtime.
- Не scale/restart/delete/apply/patch/rollout.
- Не читать Secret values.
- Не создавать credentials/API keys/sessions.
- Не продолжать D2/D3/E1/F1/F2.
- Не выполнять Git writes; host runner commit/push.
- Не менять `.agent/*` и `/root/.hermes`.
- Не использовать sudo/chown/chmod.
- Evidence только `docs/evidence/QWEN38_RECOVERY_AUDIT_R1.md`.

## Обязательные проверки
1. Зафиксировать n7/n8 и GPU inventory: model/count/used+free VRAM/processes — без kill/reset.
2. Namespace `aither-inference`: deployments, pods, services, replicas, Ready, images relevant to:
   - qwen2.5 / 32b-instruct-awq;
   - qwen3-32b;
   - любые qwen3.8/qwen38 объекты.
3. Проверить, существуют ли partial Qwen3.8 Deployment/Service/Pod и их status/reason/restarts/image/args/volumes/node placement.
4. Проверить текущий replica/state Qwen2.5 deployment и его service/endpoints.
5. Проверить Qwen3-32B unchanged/Ready на n8.
6. Read-only проверить `/health` и `/v1/models` напрямую на существующих model services, если доступны без auth.
7. Read-only проверить Test Zone `/health` и `/api/v1/models`; authenticated inference НЕ выполнять.
8. Проверить hostPath n7 read-only:
   - наличие `/data/models/Qwen3.8-27B-FP8`;
   - размер/общий статус файлов;
   - НЕ читать токены/credential files.
9. Проверить наличие/статус image `vllm/vllm-openai:v0.27.1` или mirrored equivalent и immutable digest, если можно read-only.
10. Собрать безопасные relevant events/log summaries только для определения причины failure; не выводить env dumps, tokens, Authorization headers, secret refs values.
11. Установить наиболее вероятную причину исходного `command exited with status 1` и отдельно причину `restore also failed`, если доказуемо.
12. Классифицировать фактическое состояние ровно одним вариантом:
   - SAFE_BASELINE: Qwen2.5 restored, Qwen3 healthy, no active Qwen3.8;
   - PARTIAL_CUTOVER_SAFE: Qwen3.8 partial exists, but Qwen2.5 and Qwen3 service remain healthy;
   - DEGRADED_N7: Qwen2.5 unavailable/degraded and Qwen3.8 not accepted;
   - CUTOVER_RUNTIME_ONLY: Qwen3.8 actually running while source integration not committed;
   - OTHER: exact description.
13. Сформировать минимальный corrective plan без его выполнения.

## Evidence
`docs/evidence/QWEN38_RECOVERY_AUDIT_R1.md` должен включать:
- task/result;
- UTC timestamps;
- n7/n8 GPU state;
- deployment/service/pod inventory;
- Qwen2.5 state;
- Qwen3-32B state;
- Qwen3.8 residual state;
- model files/image state;
- safe endpoint status codes;
- failure/restore-failure findings;
- runtime classification;
- exact next corrective actions;
- `SECRETS_EXPOSED: NO`.

## PASS
PASS если audit достоверно устанавливает текущее состояние и даёт достаточно evidence для безопасного corrective. PASS здесь НЕ означает успешный Qwen3.8 cutover.

При невозможности определить критичное состояние: BLOCKED с точной причиной. STOP после evidence.
