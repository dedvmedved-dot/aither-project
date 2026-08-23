# AITHER-URGENT-QWEN38-PERMANENT-CUTOVER-R2

## Цель
Постоянно заменить активную Qwen2.5 на n7 моделью `Qwen/Qwen3.8-27B-FP8`, сохранив Qwen3-32B на n8 без изменений и переведя Portal/External API на точную маршрутизацию двух активных моделей.

## Критические требования к поведению Hermes
- Работать только в перечисленных `allowed_paths` и разрешённом runtime scope.
- Не читать и не выводить значения Secret/API keys. `secret_access=false`.
- Не трогать БД, Identity schema, user accounts, billing или scope assignments.
- Не менять n8 Qwen3-32B, кроме read-only health verification.
- Не включать MTP/DSpark/EAGLE/speculative decoding, FP8 KV, long-context tuning, CUDA graphs или другие оптимизации.
- Не удалять model files Qwen2.5 и не удалять её source manifest: она должна остаться rollback asset.
- Не создавать новый auth scope. Обе активные Qwen3-family модели используют существующий `model:qwen3:chat`.
- Не использовать substring routing вида `if "qwen3" in model`; только exact map.
- Unknown model обязан возвращать контролируемый 4xx `model_not_found`, без fallback.
- Если permanent Qwen3.8 не становится healthy или routing validation не проходит — восстановить Qwen2.5 на n7 и завершить BLOCKED с evidence. Не оставлять n7 без рабочей модели.
- Не превышать один итоговый implementation commit.

## Подтверждённый baseline
- n7: `vllm-32b-instruct-awq` Qwen2.5, 1/1 healthy, 2× Quadro RTX 6000 sm_75.
- n8: `vllm-qwen3-32b-awq`, 1/1 healthy.
- Qwen3.8 snapshot на n7: `/data/models/Qwen3.8-27B-FP8`, 66/66 shards, revision already verified.
- vLLM image tested and cached on n7: `vllm/vllm-openai@sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967` (v0.27.1).
- Compatibility test already proved Qwen3.8 FP8 on Turing sm_75 via Marlin weight-only fallback, TP=2, `max-model-len=16384`, `/health=200`, chat completion HTTP 200, no fatal OOM/kernel error.

## Фаза 1 — Preflight и rollback capture
1. Verify clean worktree and baseline SHA ancestry.
2. Capture runtime state for:
   - n7 Qwen2.5 deployment/pod/health;
   - n8 Qwen3 deployment/pod/health;
   - no temporary qwen38 compat objects;
   - n7 model path completeness 66/66;
   - vLLM 0.27.1 image digest present/cached.
3. Capture current Qwen2.5 manifest and live deployment state for rollback. Do not read Secret values.

## Фаза 2 — Permanent Qwen3.8 source manifest
Create `aither-v2/deploy/vllm-qwen38-27b-fp8.yaml` with permanent Deployment + ClusterIP Service.

Required baseline:
- namespace: `aither-inference`
- Deployment/Service name: `vllm-qwen38-27b-fp8`
- pin to n7 using existing primary nodeSelector or exact n7 binding consistent with current production conventions
- runtimeClassName: nvidia
- image exactly `vllm/vllm-openai@sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967`
- model hostPath: `/data/models/Qwen3.8-27B-FP8`, read-only
- served model: `qwen3.8-27b`
- tensor parallel: 2
- gpu-memory-utilization: 0.90
- max-model-len: 16384
- max-num-seqs: 1 for first permanent baseline
- dtype: half
- enforce-eager
- reasoning parser: qwen3
- no speculative decoding
- no forced `--quantization fp8`; use checkpoint metadata/autodetection exactly as successful compatibility run
- resources must comply with namespace LimitRange: CPU limit <= 8; GPU=2; memory within max 64Gi
- liveness/readiness/startup probes `/health`
- if upstream vLLM API auth is currently required by architecture, reuse existing Secret reference by name only; never resolve value.

## Фаза 3 — Portal catalog and exact routing
Update `aither-v2/services/portal-backend/app/main.py` so active catalog is exactly:
- `qwen3-32b` → scope `model:qwen3:chat`
- `qwen3.8-27b` → scope `model:qwen3:chat`

Remove Qwen2.5 from active `CURRENT_MODELS` and user-facing allowlists/contracts.

Replace all model routing logic in active chat/external API paths with one exact mapping. Required logical mapping:
- `qwen3-32b` → `http://vllm-qwen3-32b-awq.aither-inference.svc:8000`
- `qwen3.8-27b` → `http://vllm-qwen38-27b-fp8.aither-inference.svc:8000`

Implementation may use explicit constants/env vars, but must be exact-key routing and preserve server-side upstream authentication without exposing secrets.

Unknown model:
- external OpenAI-compatible API: 404 `model_not_found` or equivalent controlled 4xx;
- authenticated Portal chat: controlled 400/404;
- never route unknown model to either backend.

Update `portal-backend.yaml` only as needed to declare explicit upstream URLs/Secret refs and deploy the updated backend image/config using the project's existing build/deploy mechanism. Do not embed credentials.

## Фаза 4 — Canonical image digest/source tracking
Update `aither-v2/canonical-image-digests.txt` with:
- permanent Qwen3.8 vLLM image digest `sha256:0a51ea5b...` and model/runtime label;
- any newly built portal-backend image digest if a new image is built.
Do not invent digest: record only runtime/registry-observed digest.

## Фаза 5 — Cutover runtime order
Fail-closed order:
1. Ensure Qwen3.8 source and Portal source changes are prepared before disrupting n7.
2. Scale Qwen2.5 on n7 from 1→0.
3. Apply permanent Qwen3.8 manifest.
4. Wait for Qwen3.8 1/1 Ready. Startup can take several minutes; avoid unnecessary context escalation/restarts.
5. Verify in-pod `/health` HTTP 200.
6. Verify `/v1/models` with an already-supported non-secret mechanism; if upstream API requires secret and task cannot access it, use startup logs to prove served-model-name and do not read secret.
7. Perform a short direct chat completion using only an allowed non-secret path. If direct auth cannot be obtained without secret access, document AUTH_REQUIRED and validate through Portal/external unauthenticated behavior in next phases.
8. Confirm n8 Qwen3 remains 1/1 and `/health=200`.

If steps 3-7 fail materially:
- delete/scale down permanent Qwen3.8 runtime as appropriate;
- scale Qwen2.5 back to 1;
- verify Qwen2.5 1/1 `/health=200`;
- leave source evidence explaining BLOCKED; do not leave n7 degraded.

## Фаза 6 — Portal/backend deployment
Build and deploy the updated portal-backend using the project's accepted source/runtime process. Pin/record the resulting immutable digest if available. Verify rollout 1/1 and `/health` + `/ready` successful.

Do not change frontend unless strictly required; frontend is not in allowed paths.

## Фаза 7 — Acceptance checks
Without creating/reading API keys or DB data:

### Runtime
- n7 Qwen3.8 permanent Deployment 1/1 Ready, restarts=0 ideally.
- n7 `/health=200`.
- n8 Qwen3 1/1 Ready and `/health=200`.
- Qwen2.5 deployment source retained but runtime `replicas=0` or otherwise inactive.
- no temporary `*-compat` objects.

### Catalog/routing source proof
- `CURRENT_MODELS` contains exactly `qwen3-32b`, `qwen3.8-27b`.
- both require `model:qwen3:chat`.
- exact routing table points each model to its own Service.
- no active substring routing capable of confusing qwen3.8 with qwen3-32b.
- no active qwen2.5 catalog entry.

### External API unauthenticated gates
Against Test Zone external routes:
- GET models without auth: auth failure (401/403), NOT 404/5xx.
- POST chat for qwen3-32b without auth: auth failure, NOT routing 404/5xx.
- POST chat for qwen3.8-27b without auth: auth failure, NOT routing 404/5xx.
- invalid model without valid auth may be auth-first; source proof must still establish controlled model_not_found after auth.

### No authenticated E2E in this task
Do NOT create temporary API keys and do NOT access Identity secrets. A separate narrow authenticated E2E gate will follow permanent cutover.

## Фаза 8 — Evidence
Create only `docs/evidence/QWEN38_PERMANENT_CUTOVER_R2.md` as evidence.
Must include:
- baseline/final commit SHAs;
- exact changed source files;
- before/after active model catalog;
- permanent Qwen3.8 manifest key parameters and image digest;
- n7/n8 pod/deployment state;
- health checks;
- startup evidence of FP8 Marlin fallback/no fatal errors;
- exact routing proof;
- Portal backend rollout proof;
- unauth external API results;
- Qwen2.5 inactive but rollback files retained;
- rollback outcome if any failure occurred;
- `SECRETS_EXPOSED: NO|YES`.

## PASS criteria
PASS only if all are true:
1. n7 permanently serves `qwen3.8-27b` 1/1 healthy.
2. n8 continues serving `qwen3-32b` 1/1 healthy.
3. Qwen2.5 is not active and remains available only as rollback asset.
4. active catalog is exactly the two Qwen3 models and both use existing `model:qwen3:chat` scope.
5. exact model→upstream routing is implemented; no substring ambiguity/fallback.
6. Portal backend is healthy after source/runtime deployment.
7. external unauthenticated routes fail for auth rather than routing/service errors.
8. no temporary compatibility objects remain.
9. only allowed paths changed, max one implementation commit.
10. `SECRETS_EXPOSED: NO`.

## STOP conditions
Stop BLOCKED and restore Qwen2.5 if Qwen3.8 cannot become healthy or if a safe rollback cannot be guaranteed. For auth-only validation blocked by unavailable credentials, do not bypass security; document and defer authenticated E2E to the next gate.
