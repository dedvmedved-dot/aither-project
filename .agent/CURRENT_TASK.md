# AITHER-PORTAL-MODEL-UI-DOCSYNC-R1

## Status

`ACTIVE`

## Machine contract

This task is intentionally published in the exact schema accepted by the installed `.agent/host_task_runner.py`.

- Source of Truth: `dedvmedved-dot/aither-project`, branch `aither-v2`
- Baseline for this corrected publication: `3690ebea23713e93c45bc510ea157be47f04a6fb`
- Executor: `hermes` through persistent host runner and H2 bridge
- Acceptance Authority: ChatGPT only after independent GitHub Connector verification
- Hermes must not self-commit, self-push, modify `CURRENT_TASK.*`, or self-accept
- `.agent/EXECUTION_RESULT.json` is runner-managed; Hermes must place detailed test/runtime evidence in the two evidence files below
- Machine `PASS` is not acceptance

## Objective

Synchronize the actually deployed Portal UI and all current-facing documentation with the already accepted permanent model contract:

| API model id | User-facing label | Scope | Exact upstream |
|---|---|---|---|
| `qwen3-32b` | `Qwen3-32B` | `model:qwen3:chat` | `http://vllm-qwen3-32b-awq.aither-inference.svc:8000` |
| `qwen3.8-27b` | `Qwen3.8-27B-FP8` | `model:qwen3:chat` | `http://vllm-qwen38-27b-fp8.aither-inference.svc:8000` |

Unknown model must remain `404 model_not_found`; routing remains exact model-id lookup only. Qwen2.5 / `vllm-32b-instruct-awq` is rollback-only and must not be shown as active. `qwen-14b`, `qwen-32b-base`, and obsolete model scopes must not remain in current UI/current documentation as available choices.

## Established defect

Read-only audit proved:

1. Portal backend catalog is already correct: exactly `qwen3-32b` and `qwen3.8-27b`, both with `model:qwen3:chat`.
2. Active/current frontend sources still contain a second hardcoded chat catalog using `qwen-14b` and `qwen-32b-base` plus stale defaults, hints, key choices and examples.
3. Dashboard/agent surfaces already call `/api/v1/models`; chat selector does not.
4. No repository evidence makes localStorage, service worker, cached static JSON or build-time model env the primary catalog authority. Stale source itself reproduces the drift.
5. Current README/API/model/deployment/user docs contain stale current-state claims.
6. Multiple frontend generations exist; live runtime must determine the actual deployment source before it is edited or declared canonical.

## Exact allowed paths

Hermes may modify only paths authorized by `CURRENT_TASK.json`. In particular the implementation/evidence scope is limited to:

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
- `docs/user-package/00_INDEX.md` through `docs/user-package/16_AI_AGENT_CONNECTION_PRIMER.md` as individually enumerated in `CURRENT_TASK.json`
- `docs/evidence/AITHER_PORTAL_MODEL_UI_DOCSYNC_R1.md`
- `docs/evidence/AITHER_PORTAL_MODEL_UI_DOCSYNC_R1_RUNTIME.md`

`.agent/EXECUTION_RESULT.json` is owned and written by the host runner. Do not edit it directly.

Do not modify `.agent/CURRENT_TASK.json`, `.agent/CURRENT_TASK.md`, `/root/.hermes`, unrelated files, or accepted historical evidence.

## Historical preservation

Do not bulk-replace old model names repository-wide. Preserve historically correct accepted evidence, dated snapshots, migration reports and rollback-only assets. Old model names may remain only when explicitly historical, superseded, migration-related or rollback-only.

For `docs/architecture/WUI_DUAL_MODEL_AND_AGENT_FLOW.md`, if it is a historical design record, preserve the historical body and mark it clearly `SUPERSEDED` with a pointer to the permanent current model contract rather than rewriting history.

## Required execution sequence

### 1. Prove the live frontend source before editing

Capture secret-free runtime facts:

- live workload/service/deployment name and namespace;
- image/config source;
- mounted ConfigMap/static file identity if applicable;
- deterministic content fingerprint/hash or equivalent;
- mapping from the served frontend to the repository artifact.

Do not infer from filenames.

### 2. Read-only verify backend contract

Do not redesign or edit accepted backend routing. Prove:

- authenticated `/api/v1/models` returns exactly `qwen3-32b` and `qwen3.8-27b`;
- both use `model:qwen3:chat`;
- invalid model produces `404 model_not_found`;
- no substring/unknown-model fallback exists.

### 3. Make `/api/v1/models` authoritative for chat UI

The chat selector must be populated from authenticated `/api/v1/models`, not from a second hardcoded active catalog.

Required behavior:

- exact API IDs preserved;
- labels `Qwen3-32B` and `Qwen3.8-27B-FP8`;
- deterministic default `qwen3-32b` when present, otherwise first accepted returned model;
- failed catalog load fails closed, disables model-dependent actions and shows a controlled error;
- no fallback to Qwen2.5, `qwen-14b`, `qwen-32b-base` or invented IDs.

Remove old identities from active selector options, defaults, welcome/help text, model hints/descriptions, diagnostics/examples, API-key choices and agent examples.

### 4. Correct current API-key authorization UI/docs

Use only current model authorization scope `model:qwen3:chat`.

Do not present as current choices:

- `model:32b:chat`
- `model:14b:chat`
- `model:32b:chat-adapter`
- `model:32b:completion`

No direct database auth/key manipulation. If temporary credentials are needed, use normal Identity/API flows and remove/revoke them after validation. Secret access is not authorized for this task; do not read or print Kubernetes Secret values.

### 5. Reconcile frontend deployment source

Use runtime facts to establish one current/canonical frontend deployment source. Update the permitted manifest/docs only as needed so following the current deployment guide cannot restore stale old-model UI. Avoid unrelated deployment refactoring.

### 6. Correct current-facing docs

Current documentation must consistently state:

- active API IDs: `qwen3-32b`, `qwen3.8-27b`;
- labels: `Qwen3-32B`, `Qwen3.8-27B-FP8`;
- scope: `model:qwen3:chat`;
- authoritative model list: `/api/v1/models`;
- unknown model: `404 model_not_found`;
- Qwen2.5 is rollback-only, not user-selectable.

Do not invent behavioral distinctions between the Qwen3 models that are not supported by accepted evidence.

## Required tests

- **T01** Static/current-vs-historical scan: no stale current model claim in allowed current UI/docs.
- **T02** Authenticated `/api/v1/models`: HTTP 200, exactly `qwen3-32b` + `qwen3.8-27b`, old models absent.
- **T03** UI source: chat selector demonstrably populated from `/api/v1/models`.
- **T04** Rendered UI/DOM: exactly the two accepted labels/IDs.
- **T05** Fresh/private or cache-bypassed session confirms corrected selector; record cache invalidation if actually needed.
- **T06** Catalog-load failure fails closed; no old/unknown fallback.
- **T07** API-key UI uses `model:qwen3:chat`; obsolete scopes absent as active choices.
- **T08** Authenticated non-stream `qwen3-32b` succeeds.
- **T09** Authenticated non-stream `qwen3.8-27b` succeeds.
- **T10** Streaming both succeeds if this deployed Portal generation exposes streaming.
- **T11** Invalid model returns `404 model_not_found`, no fallback.
- **T12** Deployment reproducibility: current documented deploy path cannot reintroduce stale UI.
- **T13** README/model/API/deployment/current user docs agree on model set and scope.
- **T14** Sample accepted historical evidence remains unmodified.
- **T15** Temporary session/key cleanup complete; no credentials retained.

## Required evidence

Create exactly:

1. `docs/evidence/AITHER_PORTAL_MODEL_UI_DOCSYNC_R1.md`
2. `docs/evidence/AITHER_PORTAL_MODEL_UI_DOCSYNC_R1_RUNTIME.md`

Together they must contain:

- baseline/start HEAD and resulting worktree state before runner finalization;
- exact implementation paths changed;
- before/after model-source mapping;
- live frontend workload/source identity and fingerprint;
- old-identifier scan classified current vs historical;
- authenticated `/api/v1/models` result without credentials;
- rendered selector/DOM proof from fresh session or equivalent served-page verification;
- API-key scope UI proof;
- invalid-model `404 model_not_found` proof;
- deployment reproducibility result;
- cleanup/revocation/logout evidence;
- explicit `SECRETS EXPOSED: NO`, or fail if that statement cannot truthfully be made;
- T01-T15 result table with PASS/FAIL/BLOCKED and evidence references.

The host runner will generate `.agent/EXECUTION_RESULT.json` using its fixed whitelist schema. Do not attempt to replace that schema from Hermes.

## Security / execution prohibitions

- No secret disclosure.
- No Kubernetes Secret-value reads/prints.
- No direct DB auth/key manipulation.
- No `/root/.hermes` modification.
- No second Telegram Gateway.
- No generic sudo for Codex.
- No `safe.directory=*`.
- No repository ownership change to root.
- No substring routing or unknown-model fallback.
- No rewrite of accepted historical evidence.
- No unrelated roadmap/refactoring work.
- No Hermes self-commit/self-push/self-acceptance.

## Acceptance gate

A runner/Hermes `PASS` is only an execution claim. ChatGPT must independently verify GitHub changes and runtime evidence before issuing any of `PASSED`, `CONNECTOR VERIFIED`, `RUNTIME ACCEPTED`, or `ACCEPTED`.
