# AITHER-PORTAL-MODEL-UI-DOCSYNC-R1

## Status

`READY`

## Governance

- Source of Truth: `dedvmedved-dot/aither-project`, branch `aither-v2`.
- Base HEAD: `351ef1aafedd20bd053588501ea9fcb7587336de`.
- Executor: Hermes through the persistent host runner.
- Acceptance Authority: ChatGPT only, after independent GitHub Connector verification.
- Hermes must not self-accept, self-commit or self-push.
- Machine `PASS` is not acceptance.

## Objective

Synchronize the **actually deployed Portal UI** and all **current-facing documentation** with the already accepted permanent model contract:

| API model id | User-facing label | Scope | Exact upstream |
|---|---|---|---|
| `qwen3-32b` | `Qwen3-32B` | `model:qwen3:chat` | `http://vllm-qwen3-32b-awq.aither-inference.svc:8000` |
| `qwen3.8-27b` | `Qwen3.8-27B-FP8` | `model:qwen3:chat` | `http://vllm-qwen38-27b-fp8.aither-inference.svc:8000` |

Unknown model must remain a controlled `404 model_not_found`. Routing must remain exact model-id lookup only.

`Qwen2.5` / `vllm-32b-instruct-awq` is rollback-only and must not be presented to users as active. Likewise `qwen-14b`, `qwen-32b-base` and obsolete scopes must not remain in current UI/current documentation as available choices.

## Read-only audit findings that define this correction

1. The Portal backend model contract is already correct at the base HEAD: exactly `qwen3-32b` and `qwen3.8-27b`, both with `model:qwen3:chat`.
2. The stale UI is not explained by the backend catalog. Current frontend sources still hardcode `qwen-14b` / `qwen-32b-base` in the chat selector, defaults, model hints, API-key model choices and examples.
3. Dashboard/agent surfaces already query `/api/v1/models`, but the chat selector has a second hardcoded catalog. That split is the primary defect.
4. No repository evidence identifies localStorage, service worker, cached static JSON or build-time model environment variables as the primary model-catalog authority. Browser cache may preserve an old deployed build, but the source itself is stale and therefore cache is not the root cause.
5. Current README/API/model-catalog/deployment/user documentation still contains active-state claims and examples for Qwen2.5 and/or `qwen-14b` / `qwen-32b-base` / `model:32b:chat`.
6. The repository contains more than one frontend generation: `docs/operations/DEPLOYMENT_GUIDE.md` points at an old Stage-15 frontend manifest while `deploy/portal-frontend-combined.html` represents a later frontend. The task must prove which source/workload is actually live and leave one unambiguous current deployment path.
7. `runner-live/runner-status.json` is absent from GitHub at the base HEAD. **Do not create or fabricate it in this task.** Its absence is a separate Source-of-Truth observability gap and is not evidence that the runner is down.

## Historical-preservation rule

Do **not** bulk-replace old names across the repository.

Preserve unchanged when historically correct:

- accepted evidence;
- old acceptance reports;
- dated configuration snapshots;
- model-migration reports;
- rollback-only assets and manifests.

Old model names may remain only when the context is explicitly historical, superseded, migration-related or rollback-only. Current architecture, operations, user guides, examples and active UI must describe the accepted permanent model set.

For `docs/architecture/WUI_DUAL_MODEL_AND_AGENT_FLOW.md`, if it is a historical design record, preserve the historical body and mark it clearly **SUPERSEDED** with a pointer to the current model contract instead of rewriting history.

## Allowed paths — exact only

Hermes may modify only these paths:

- `portal/static/index.html`
- `deploy/portal-frontend-combined.html`
- `aither-v2/services/portal-frontend/k8s/portal-frontend.yaml`
- `README.md`
- `aither-v2/README.md`
- `docs/model-catalog.md`
- `docs/api-reference.md`
- `docs/operations/DEPLOYMENT_GUIDE.md`
- `docs/architecture/WUI_DUAL_MODEL_AND_AGENT_FLOW.md`
- `docs/user-guide/WEB_UI_USER_GUIDE.md`
- `docs/user-guide/AI_AGENT_CONNECTION_GUIDE.md`
- `docs/user-package/00_INDEX.md`
- `docs/user-package/01_WELCOME.md`
- `docs/user-package/02_QUICK_START.md`
- `docs/user-package/03_USER_GUIDE.md`
- `docs/user-package/04_API_GUIDE.md`
- `docs/user-package/05_TEST_ASSIGNMENT.md`
- `docs/user-package/06_BUG_REPORT_TEMPLATE.md`
- `docs/user-package/07_USER_FEEDBACK_FORM.md`
- `docs/user-package/08_FAQ.md`
- `docs/user-package/09_SECURITY_RULES.md`
- `docs/user-package/10_KNOWN_LIMITATIONS.md`
- `docs/user-package/11_ACCEPTANCE_CHECKLIST.md`
- `docs/user-package/12_OWNER_HANDOVER.md`
- `docs/user-package/13_WEB_UI_GUIDE.md`
- `docs/user-package/14_API_KEY_USER_GUIDE.md`
- `docs/user-package/15_DUAL_ZONE_ACCESS_GUIDE.md`
- `docs/user-package/16_AI_AGENT_CONNECTION_PRIMER.md`
- `docs/evidence/AITHER_PORTAL_MODEL_UI_DOCSYNC_R1.md`
- `docs/evidence/AITHER_PORTAL_MODEL_UI_DOCSYNC_R1_RUNTIME.md`
- `.agent/EXECUTION_RESULT.json`

Do not touch `.agent/CURRENT_TASK.json`, `.agent/CURRENT_TASK.md`, `/root/.hermes`, accepted historical evidence, or any unrelated path.

## Required execution sequence

### 1. Establish the live frontend source before editing

Using runtime facts, record:

- live frontend workload/service/deployment name;
- namespace;
- image/config source;
- mounted ConfigMap/static file identity if applicable;
- content hash/fingerprint or an equivalent deterministic identifier;
- which repository artifact corresponds to what is actually served.

Do not print Secret values.

If the live UI comes from `portal/static/index.html`, prove it. If it comes from `deploy/portal-frontend-combined.html`, prove it. If the Stage-15 manifest is still the canonical deploy path, prove it. Do not assume based on filenames.

### 2. Keep backend routing unchanged

Read-only verify the accepted backend contract. Do not redesign it.

Required facts:

- `/api/v1/models` -> exactly `qwen3-32b`, `qwen3.8-27b`;
- both use scope `model:qwen3:chat`;
- unknown model -> `404 model_not_found`;
- no substring fallback.

### 3. Make `/api/v1/models` authoritative for chat UI

The chat model selector must not have a separate active hardcoded model catalog.

Required behavior:

1. authenticated UI loads `/api/v1/models`;
2. selector is populated from that response;
3. exact API ids are preserved;
4. labels are `Qwen3-32B` and `Qwen3.8-27B-FP8`;
5. default may be `qwen3-32b` when present; otherwise first returned accepted model;
6. if the catalog cannot be loaded, **fail closed** — disable model-dependent actions and show a controlled catalog-load error;
7. never silently fall back to `qwen-14b`, `qwen-32b-base`, Qwen2.5 or any invented id.

Remove obsolete model identities from all active UI surfaces, including:

- selector options;
- default model values;
- welcome/help text;
- model descriptions/hints;
- clear-chat/model-info logic;
- diagnostics/examples;
- API-key creation UI;
- agent examples.

### 4. Correct API-key model authorization UI

Current UI and docs must use the accepted scope:

`model:qwen3:chat`

Do not offer as current choices:

- `model:32b:chat`
- `model:14b:chat`
- `model:32b:chat-adapter`
- `model:32b:completion`

Do not use direct DB manipulation for keys. If temporary credentials are needed for runtime validation, use normal Identity/API workflows and revoke them afterwards.

### 5. Reconcile frontend deployment documentation

The documented deployment procedure must not be capable of restoring stale Stage-15/old-model UI.

Establish one current/canonical frontend deployment source from runtime facts, then make `docs/operations/DEPLOYMENT_GUIDE.md` consistent with it. If the Stage-15 manifest remains canonical, update it within the allowed path. If it is superseded, make that explicit and stop presenting it as the current frontend source.

Avoid unrelated deployment refactoring.

### 6. Correct current-facing documentation

Update only documents that make current-state claims or current user/API instructions. They must consistently state:

- active models: `qwen3-32b`, `qwen3.8-27b`;
- user labels: `Qwen3-32B`, `Qwen3.8-27B-FP8`;
- scope: `model:qwen3:chat`;
- model list is authoritative from `/api/v1/models`;
- invalid/unknown model is rejected with `model_not_found`;
- Qwen2.5 is rollback-only, not active/user-selectable.

Do not manufacture model-specific behavioral claims not established by accepted evidence. In particular, do not carry forward the old “14B chat vs 32B base completion” distinction to the Qwen3 pair.

## Required tests

| ID | Check | PASS criterion |
|---|---|---|
| T01 | Repository/static scan | All old identifiers in current-facing allowed files are removed or explicitly historical/rollback context. |
| T02 | Backend catalog | Authenticated `/api/v1/models` = exactly `qwen3-32b`, `qwen3.8-27b`; no Qwen2.5/14B/old 32B. |
| T03 | UI data source | Chat selector is populated from `/api/v1/models`, not a second hardcoded active catalog. |
| T04 | Rendered selector | Fresh authenticated UI/DOM shows exactly both accepted models and exact IDs. |
| T05 | Cache independence | New/private session or cache-bypassed request shows corrected UI; document any cache invalidation actually required. |
| T06 | Catalog-load failure | No old/unknown fallback; dependent action is disabled with controlled error. |
| T07 | API-key UI | Current authorization uses `model:qwen3:chat`; obsolete scopes absent as active choices. |
| T08 | Non-stream `qwen3-32b` | Authenticated request succeeds. |
| T09 | Non-stream `qwen3.8-27b` | Authenticated request succeeds. |
| T10 | Streaming | Both active models succeed if streaming is exposed by the deployed Portal generation. |
| T11 | Invalid model | `404 model_not_found`; no fallback. |
| T12 | Deploy reproducibility | Following current deployment docs cannot restore stale old-model UI. |
| T13 | Documentation consistency | README/model catalog/API/deployment/current user docs agree on model set and scope. |
| T14 | Historical preservation | Sampled accepted historical evidence is unmodified and old names remain historical facts only. |
| T15 | Cleanup | Temporary key/session/secret is revoked/logged out/deleted; no credential remains. |

## Required evidence

Create exactly:

1. `docs/evidence/AITHER_PORTAL_MODEL_UI_DOCSYNC_R1.md`
2. `docs/evidence/AITHER_PORTAL_MODEL_UI_DOCSYNC_R1_RUNTIME.md`
3. `.agent/EXECUTION_RESULT.json`

Evidence must include:

- base HEAD;
- exact changed paths;
- before/after UI model-source mapping;
- proof of live frontend workload/source identity;
- old-identifier scan with **current vs historical** classification;
- authenticated `/api/v1/models` result (without credentials);
- rendered selector/DOM proof from a fresh session or equivalent served-page verification;
- API-key scope UI proof;
- invalid-model `404 model_not_found` proof;
- deployment reproducibility result;
- cleanup/revocation result;
- explicit `SECRETS EXPOSED: NO` or failure if that cannot be asserted truthfully.

## Security and execution prohibitions

- Do not disclose secrets in Git, logs, screenshots or reports.
- Do not print Kubernetes Secret values.
- Do not use direct DB access for auth/API-key workflows.
- Do not modify `/root/.hermes`.
- Do not create a second Telegram Gateway.
- Do not grant Codex generic sudo.
- Do not set `safe.directory=*`.
- Do not change repository ownership to root.
- Do not introduce substring routing or model fallback.
- Do not rewrite accepted historical evidence.
- Do not perform roadmap work unrelated to this correction.
- Do not create `runner-live/runner-status.json` as part of this task.

## Execution result contract

`.agent/EXECUTION_RESULT.json` must identify task `AITHER-PORTAL-MODEL-UI-DOCSYNC-R1` and return one of:

- `PASS`
- `FAIL`
- `BLOCKED`

It must include at minimum:

- `task_id`
- `result`
- `base_head`
- `changed_paths`
- `tests`
- `runtime_evidence`
- `historical_files_preserved`
- `secrets_exposed`
- `cleanup_complete`
- `notes`

A machine `PASS` does **not** mean acceptance.

## Acceptance gate

ChatGPT will independently verify the final GitHub state and runtime evidence. Acceptance requires all of the following:

1. backend/API contract remains exactly the already accepted two-model contract;
2. the actually deployed chat selector loads its active model set from `/api/v1/models`;
3. active UI offers exactly `qwen3-32b` and `qwen3.8-27b`;
4. no old model is presented as currently available in active Portal surfaces;
5. current key UI/docs use `model:qwen3:chat`;
6. current README/architecture/operations/API/user docs match the permanent model state;
7. historical evidence remains preserved;
8. canonical frontend deployment is unambiguous and cannot restore stale UI;
9. evidence is complete and secret-free.

Only ChatGPT may then issue `PASSED`, `CONNECTOR VERIFIED`, `RUNTIME ACCEPTED` or `ACCEPTED`.
