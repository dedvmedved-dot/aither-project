# AITHER-PORTAL-MODEL-CATALOG-DOCSYNC-R1

## Authority and scope

GitHub repository `dedvmedved-dot/aither-project`, branch `aither-v2`, is the Source of Truth.

Executor: **Hermes only** through the existing host runner/H2/root-executor path. Codex execution is not authorized for Aither. Hermes must not commit or push; the host runner performs finalization.

This is the single corrective step for the already-proven live Portal model-catalog drift and the user-facing documentation article **«Работа с моделями»**. Do not expand into model benchmarking, performance tuning, observability, backend redesign, inference changes, or unrelated documentation cleanup.

## Proven starting facts

Discovery task `AITHER-LIVE-PORTAL-SOURCE-DISCOVERY-R2` proved that the user-facing Portal at `https://fb1.spb.ru:10443/` is served from Kubernetes ConfigMap `aither-portal-config` in namespace `aither-inference`, and that its canonical repository source is:

- `aither-v2/services/portal-frontend/index.html`
- `aither-v2/services/portal-frontend/app.js`
- `aither-v2/services/portal-frontend/styles.css`
- `aither-v2/services/portal-frontend/nginx.conf`

The current live chat selector is stale: it exposes `qwen2.5-32b-instruct` and `qwen3-32b`, while the accepted active backend catalog is exactly:

- `qwen3-32b`
- `qwen3.8-27b`

Both active models use API-key scope `model:qwen3:chat`.

Qwen2.5 is rollback-only and must not be presented as an active/selectable model.

The live Documentation card **«🤖 Работа с моделями»** points to `/docs/17_MODEL_USAGE_GUIDE.md`. Runtime discovery proved `aither-portal-docs` contains 18 Markdown keys, but `docs/user-package/` in GitHub currently contains only `00_INDEX.md` through `16_AI_AGENT_CONNECTION_PRIMER.md`; therefore the live article has no canonical GitHub source and this must be corrected.

## Objective

Make the live Portal, its canonical frontend source, and the user-facing article **«Работа с моделями»** consistent with the accepted active catalog, without changing model deployments, routing, Identity, Gateway behavior, database state, credentials, or any Secret.

The final state must support normal user selection of both `qwen3-32b` and `qwen3.8-27b` in the Portal and must allow creation of an API key with the correct `model:qwen3:chat` scope for these models.

## Allowed source changes — exact

Only these implementation/evidence paths may change:

1. `aither-v2/services/portal-frontend/index.html`
2. `aither-v2/services/portal-frontend/app.js`
3. `docs/user-package/00_INDEX.md`
4. `docs/user-package/17_MODEL_USAGE_GUIDE.md` — create this canonical source
5. `docs/evidence/AITHER_PORTAL_MODEL_CATALOG_DOCSYNC_R1.md`

Do not modify superseded frontend artifacts such as `portal/static/index.html`, `portal/dist/index.html`, `deploy/portal-frontend-combined.html`, `aither-v2/services/portal-frontend/k8s/portal-frontend.yaml`, or `aither-portal-frontend-config`.

## Runtime mutation allowlist — exact

Runtime writes are allowed only to synchronize the corrected canonical source into:

- ConfigMap `aither-portal-config`, namespace `aither-inference`;
- ConfigMap `aither-portal-docs`, namespace `aither-inference`;
- Deployment `aither-portal`, namespace `aither-inference`, **restart only if required** after waiting for ConfigMap projection to refresh.

No other Kubernetes object may be created, patched, restarted, scaled, deleted, or applied.

Do not touch either active vLLM deployment, Gateway/backend routing, Identity, API-key database contents, RAG backend behavior, reverse-proxy configuration, or the secondary non-user-facing `aither-portal-frontend` deployment/service.

## Security constraints

- Do not read, print, export, hash, decode, or otherwise access Kubernetes Secret values.
- Do not use user passwords, cookies, Authorization headers, API keys, or temporary credentials in this task.
- Do not create an API key in this task; authenticated E2E is the next acceptance step.
- Do not modify `/root/.hermes`.
- Do not change repository ownership or use `safe.directory=*`.
- Do not make Git commits or push from Hermes.

## Required implementation

### 1. Preflight

Record sanitized evidence for:

- UTC timestamp;
- branch and start HEAD;
- clean worktree;
- baseline is ancestor of task-control HEAD;
- `baseline..HEAD` handoff contains only `.agent/CURRENT_TASK.json` and `.agent/CURRENT_TASK.md`;
- current live `aither-portal` Service/Deployment/Pod Ready state;
- current key names and SHA-256 fingerprints of `aither-portal-config` and `aither-portal-docs`, without Secret access.

### 2. Correct the live chat model selector

The chat model selector must no longer contain hardcoded stale model options.

Preferred implementation: populate the selector from the authenticated existing `/api/v1/models` response already used elsewhere in the Portal. The selector must represent the active catalog returned by the API and support the accepted IDs `qwen3-32b` and `qwen3.8-27b`.

Requirements:

- no selectable/default `qwen2.5-32b-instruct`;
- no `model:qwen2.5:chat` scope in active frontend code;
- no silent fallback to a retired/unknown model;
- if model-catalog retrieval fails, fail closed in the UI: disable sending or show a clear catalog-load error rather than inventing a model;
- when a saved browser chat contains a model no longer present in the active catalog, preserve chat history but migrate the active selection to a valid returned model without requiring the retired model ID to remain hardcoded;
- new chats must use a valid active model;
- changing sessions must restore the session model only if it is still in the returned active catalog.

Display labels must clearly distinguish:

- `qwen3-32b` → `Qwen3-32B`
- `qwen3.8-27b` → `Qwen3.8-27B`

Do not invent unverified context-window, quantization, placement, or performance claims. If the UI shows model detail, derive only from runtime/source facts that can be verified read-only; otherwise use a neutral description.

### 3. Correct all active model-related Portal behavior in canonical `app.js`

Remove the stale Qwen2.5 dependency from the active user journey, including at minimum:

- new-session/default model;
- old-single-chat migration fallback;
- chat send fallback;
- new-chat reset;
- dashboard model-description mapping;
- model-info panel;
- API-key creation modal;
- API-key scope generation;
- session usage/model labels.

The API-key creation UI must reflect that both accepted active Qwen3 models are covered by `model:qwen3:chat`. It must never emit `model:qwen2.5:chat`. Avoid duplicate identical scopes.

Do not change RAG routing. If a Qwen2.5 string is merely a fabricated client-side RAG response label rather than a runtime-returned model identity, replace it with a truthful neutral/API-derived label; do not claim RAG was migrated unless runtime evidence proves it.

### 4. Create and correct the canonical article «Работа с моделями»

Create:

`docs/user-package/17_MODEL_USAGE_GUIDE.md`

Use the current runtime `/docs/17_MODEL_USAGE_GUIDE.md` as a read-only structural/reference source if useful, but the GitHub file becomes canonical.

The article must be user-facing and must document only verified current behavior. At minimum include:

- title identifying it as **«Работа с моделями»**;
- current active model table with exactly `qwen3-32b` and `qwen3.8-27b`;
- exact API model IDs and display names;
- explanation of selecting a model in Portal chat;
- explanation that available models are obtained from the current model catalog/API rather than maintained as a separate static user list;
- API-key requirement and current scope `model:qwen3:chat`;
- a correct request example for each active model using the externally supported API path actually proven by current nginx/backend configuration;
- streaming/non-streaming behavior only where already supported and verified;
- concise model-choice guidance based on verified characteristics only;
- error behavior for unknown/unavailable model;
- no statement that Qwen2.5 is active or selectable;
- no old `qwen-14b`, `qwen-32b-base`, `qwen2.5-14b`, `qwen2.5-32b`, or `qwen2.5-32b-instruct` as current model examples.

If a context limit or deployment detail is stated, verify it read-only from the actual current runtime before writing it. Do not copy stale values from superseded documentation.

### 5. Update documentation index

Update `docs/user-package/00_INDEX.md` minimally:

- add document 17: `[MODEL USAGE GUIDE](17_MODEL_USAGE_GUIDE.md)` / «Работа с моделями»;
- replace the stale Web UI model summary with the active pair `qwen3-32b` and `qwen3.8-27b`;
- do not perform unrelated rewriting of the documentation package.

### 6. Synchronize the live Portal ConfigMap

Before mutation, record the `aither-portal-config` key set and SHA-256 values.

Update `aither-portal-config` from the canonical repository files exactly:

- `index.html`
- `app.js`
- existing unchanged `styles.css`
- existing unchanged `nginx.conf`

After update, prove all four ConfigMap keys are byte-identical to the canonical repository files.

Do not update `aither-portal-frontend-config`.

### 7. Synchronize the live documentation ConfigMap

Before mutation, record the complete non-secret key set of `aither-portal-docs` and fingerprints.

Synchronize `00_INDEX.md` and `17_MODEL_USAGE_GUIDE.md` from GitHub canonical source while preserving all other documentation keys byte-identical. The post-change ConfigMap must not lose any existing documentation key.

Prove the live `/docs/17_MODEL_USAGE_GUIDE.md` bytes equal the new GitHub source and returns HTTP 200 through the user-facing Portal.

### 8. Make projection live

First wait for normal ConfigMap volume propagation and verify live hashes.

Only if the user-facing Portal still serves old bytes after a reasonable bounded wait, restart **only** Deployment `aither-portal` and wait for it to become Ready. Record whether a restart was needed.

The Portal must remain healthy after the sync.

### 9. Runtime verification — unauthenticated/static only

Without credentials, verify from `https://fb1.spb.ru:10443/` and the NodePort where useful:

- HTTP 200 for entry page and static assets;
- live entry/app.js fingerprints equal repository + `aither-portal-config`;
- live code contains support for `qwen3-32b` and `qwen3.8-27b`;
- live active frontend has no selectable/default Qwen2.5 path and no `model:qwen2.5:chat` scope;
- `/docs/17_MODEL_USAGE_GUIDE.md` returns HTTP 200 and its bytes equal repository + `aither-portal-docs`;
- the article documents the exact active pair and `model:qwen3:chat`.

Do not perform login/chat/API-key authenticated testing here. That belongs to the final E2E task.

## Required evidence

Write exactly:

`docs/evidence/AITHER_PORTAL_MODEL_CATALOG_DOCSYNC_R1.md`

Include:

1. task ID, baseline, task-control/start HEAD and UTC timestamps;
2. exact source files changed;
3. before/after model-selector behavior;
4. before/after active model IDs and API-key scope behavior;
5. proof that `17_MODEL_USAGE_GUIDE.md` was absent in GitHub before and is canonical after;
6. pre/post ConfigMap key sets and SHA-256 fingerprints;
7. live HTTP/fingerprint verification for index, app.js, and article;
8. `aither-portal` Ready state after sync;
9. whether deployment restart was required;
10. sanitized commands used;
11. explicit `BACKEND_MODEL_DEPLOYMENTS_CHANGED: NO`;
12. explicit `GATEWAY_ROUTING_CHANGED: NO`;
13. explicit `SECRETS_EXPOSED: NO`;
14. explicit list `RUNTIME_MUTATIONS:` containing only the allowed objects actually changed;
15. final `RESULT: PASS` or `RESULT: BLOCKED/FAIL` with exact reason.

## PASS criteria

PASS only if all are true:

- canonical live frontend source has been corrected;
- live Portal bytes match corrected canonical source;
- active chat UI supports `qwen3-32b` and `qwen3.8-27b`;
- Qwen2.5 is not selectable/default and no active frontend path creates `model:qwen2.5:chat`;
- API-key UI generates the correct `model:qwen3:chat` scope without duplicates;
- `docs/user-package/17_MODEL_USAGE_GUIDE.md` exists in GitHub worktree and is the canonical source for the live article;
- live `/docs/17_MODEL_USAGE_GUIDE.md` is byte-identical to that source;
- `00_INDEX.md` references document 17 and shows the active pair;
- no backend model deployment, Gateway routing, Identity, database, Secret, reverse proxy, or secondary frontend was changed;
- Portal is healthy/Ready after runtime sync;
- no Secret or credential was exposed.

STOP after evidence is complete. Do not run the final authenticated E2E; ChatGPT will independently audit this task first.
