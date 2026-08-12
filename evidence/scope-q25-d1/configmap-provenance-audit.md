# SCOPE-Q25-D1 ConfigMap Provenance Audit

## Scope

This is a repository-only audit at Git `HEAD` `68c6cbc4879a2559516faf9aa1f34dc0d91014cc`, on branch `aither-v2`. It examines tracked artifacts that plausibly define, generate, apply, or document configuration for the two current model IDs and their authorization scopes. No Kubernetes, runtime, secret, database, deployment, or network evidence was accessed.

The contract tested is:

- `qwen2.5-32b-instruct` -> `model:qwen2.5:chat`;
- `qwen3-32b` -> `model:qwen3:chat`;
- `model:32b:chat` may be accepted temporarily for compatibility, but must not be issued as the new Qwen2.5 default.

`UPSTREAM_14B_*` is evaluated by its consumers and configured value, not by its stale name.

## Evidence

### Current implementation and deployment artifacts

- `aither-v2/deploy/vllm-32b-instruct-awq.yaml` defines the Qwen2.5 workload and Service and sets vLLM `--served-model-name` to `qwen2.5-32b-instruct`. It was introduced by `407cbe73c75731a4dd01bffec94084921ad75df6`.
- `aither-v2/deploy/vllm-qwen3-32b-awq.yaml` defines the Qwen3 workload and Service and sets `--served-model-name` to `qwen3-32b`. It was introduced by `8ba71ac50fca9ae7fe66b6422e1b376f13fa73d9`.
- `aither-v2/services/portal-backend/app/main.py` consumes `UPSTREAM_14B_URL`, `UPSTREAM_14B_TOKEN`, `UPSTREAM_32B_URL`, and `UPSTREAM_32B_TOKEN`; allowlists both current model IDs; routes Qwen3 through the `UPSTREAM_14B_*` slot and Qwen2.5 through `UPSTREAM_32B_*`; and defines `CURRENT_MODELS` with canonical Qwen2.5 scope `model:qwen2.5:chat`, legacy compatibility scope `model:32b:chat`, and Qwen3 scope `model:qwen3:chat`. External API-key entitlement accepts the canonical scope or the declared legacy scope.
- `aither-v2/services/portal-backend/k8s/portal-backend.yaml` deploys the Portal Backend image. Its current `env` list does **not** define any `UPSTREAM_14B_*` or `UPSTREAM_32B_*` value, has no `envFrom`, and has no ConfigMap reference. Its last change was `118708fa5ecc8a2679a14608c2b3f82f69a02e84`, which corrected YAML nesting but did not add the upstream configuration.
- `aither-v2/services/identity/app/main.py` is the scope issuer and API-key validator. It currently gives new OAuth, local-registration, and bootstrap users canonical `model:qwen2.5:chat` and `model:qwen3:chat` scopes, and allows API keys with canonical Qwen2.5, Qwen3, or legacy Qwen2.5 scope.
- `aither-v2/services/portal-frontend/app.js` issues `model:qwen2.5:chat` and `model:qwen3:chat` from the current API-key UI and renders `model:32b:chat` only as a Qwen2.5 compatibility label.
- `aither-v2/services/portal-frontend/index.html` exposes the current model IDs in the source UI.
- `aither-v2/services/portal-frontend/k8s/portal-frontend.yaml` defines and mounts ConfigMap `aither-portal-frontend-config`, including an inline `index.html`. Git history shows only `d957070` and `f081791` for this path. Its inline page contains none of `qwen2.5-32b-instruct`, `qwen3-32b`, `model:qwen2.5:chat`, or `model:qwen3:chat`, and there is no generator or equality check linking it to the current files under `services/portal-frontend/`.
- `aither-v2/deploy/30-services.sh` applies the Identity, Portal Backend, and inline Portal Frontend ConfigMap manifests. It therefore supplies a repository deployment relationship for those manifests, but it does not apply the two current vLLM manifests and does not synthesize the missing Portal Backend upstream environment.

### Scope history

- `407cbe73c75731a4dd01bffec94084921ad75df6` introduced native Qwen2.5 chat and the Qwen2.5 vLLM manifest. At that point the scope was `model:32b:chat`.
- `8ba71ac50fca9ae7fe66b6422e1b376f13fa73d9` introduced Qwen3, its vLLM manifest, `model:qwen3:chat`, and Qwen3 routing through the configuration slot named `UPSTREAM_14B_*`.
- `31b97cac9f913c3bd6b46934c8b57baa3ba69a5c` introduced the permanent external API-key path in Identity and Portal Backend.
- `adf54f066600f1e0d2c56c37bbeca80aa8a84d1f` changed Portal Backend's Qwen2.5 canonical scope to `model:qwen2.5:chat` while retaining `model:32b:chat` as `legacy_scope`; it temporarily made new Identity users receive both scopes.
- `56d43ca77ed566f44c43b558770e1e2d5ffe38f7` removed `model:32b:chat` from new-user defaults and changed the current frontend issuer to request `model:qwen2.5:chat`. This is direct repository evidence that legacy scope is not the new issuer default.

### Documentation and preserved evidence

- `aither-v2/docs/current-state/CHANGE_HISTORY_2026-08-06_07.md`, `CURRENT_STATE_2026-08-07.md`, and `REPOSITORY_STATE_MATRIX.md` document commits `407cbe7` and `8ba71ac` and explicitly distinguish Git facts from reported runtime facts. They predate the canonical Qwen2.5 scope cutover and still describe `model:32b:chat` as current in places.
- `aither-v2/docs/models/MODEL_CATALOG.md` identifies both current model manifests but still lists `model:32b:chat` as Qwen2.5's primary scope. That statement is stale relative to `adf54f0` and `56d43ca`; it is not evidence of a new issuer default at `HEAD`.
- `configs/snapshot-2026-07-27/configuration/configmaps-index.json` inventories older runtime ConfigMap names and keys only. It contains neither current Qwen model configuration nor ConfigMap values, and predates the August model/scope changes.
- Historical inline ConfigMaps and gateway evidence under `aither-v2/manifests/mvp-roadmap/`, `aither-v2/docs/mvp-roadmap/`, and `aither-v2/03-vllm-14b-deploy/` describe the superseded 14B/32B-adapter architecture. They do not generate or deploy the current Qwen2.5/Qwen3 Portal Backend configuration.

## Provenance Chain

The repository proves these source-level chains:

1. `407cbe7` -> `deploy/vllm-32b-instruct-awq.yaml` -> vLLM serves `qwen2.5-32b-instruct` at Service `vllm-32b-instruct-awq`.
2. `8ba71ac` -> `deploy/vllm-qwen3-32b-awq.yaml` -> vLLM serves `qwen3-32b` at Service `vllm-qwen3-32b-awq`.
3. `31b97ca` -> external API-key implementation -> `adf54f0` canonical/legacy Qwen2.5 split -> `56d43ca` canonical-only new issuers.
4. `services/identity/app/main.py` and `services/portal-frontend/app.js` issue canonical scopes -> `services/portal-backend/app/main.py` checks those scopes and retains explicit legacy consumption for Qwen2.5.
5. `deploy/30-services.sh` -> `services/portal-backend/k8s/portal-backend.yaml` and `services/portal-frontend/k8s/portal-frontend.yaml` -> Kubernetes Deployment/ConfigMap objects if that script is used.

The repository does **not** close the chain from Portal Backend routing to deployed upstream configuration. The application uses defaults if the variables are absent: Qwen2.5 defaults to `http://vllm-32b-instruct-awq.aither-inference.svc:8000`, while the stale `UPSTREAM_14B_URL` name defaults to the old `vllm-14b-instruct` Service rather than the tracked Qwen3 Service `vllm-qwen3-32b-awq`. Repository documents claim the runtime slot was repointed, but no tracked ConfigMap, Deployment env entry, overlay, generator, or deployment command proves that value.

The repository also does not close the chain from the current frontend source to the ConfigMap actually applied by `deploy/30-services.sh`. The applied inline ConfigMap predates and is not generated from the current frontend files.

## Findings

1. **Canonical authorization source is supported at `HEAD`.** New scope issuers use `model:qwen2.5:chat` for `qwen2.5-32b-instruct` and `model:qwen3:chat` for `qwen3-32b`.
2. **Legacy scope is transition-only in active external API code.** `model:32b:chat` remains in Identity's accepted API-key scope set and Portal Backend's `legacy_scope`, but commit `56d43ca` removes it from the default user issuers. No active new-key UI path found in the current frontend emits it.
3. **The stale variable name is not itself treated as routing evidence.** Code intentionally selects the `UPSTREAM_14B_*` slot for Qwen3. The problem is not its name; the provenance gap is that the repository supplies neither a Qwen3 value for that slot nor a tracked deploy-time override. With only tracked defaults, the slot points to the old 14B Service.
4. **Current model manifests are repository-proven but not tied into the main deployment script.** Both Services exist as tracked desired-state artifacts, but `deploy/30-services.sh` does not apply them.
5. **The tracked frontend ConfigMap is not aligned with current frontend source.** It is a plausible deployment artifact because the main script applies it, but it contains an older inline application and has no reproducible generation relationship to the current UI files.
6. **Documentation is mixed-age.** Recent code/history establishes the canonical Qwen2.5 scope, while the model catalog and August 7 state documents retain legacy-primary descriptions. Those documents cannot override the later implementation history.
7. **No runtime conclusion is made.** Statements in repository documents about repointed environment values, deployed ConfigMaps, migrated databases, or working model endpoints remain reported runtime claims, not repository proof.

## Unresolved

- The tracked ConfigMap, overlay, Helm/Kustomize values, environment file, or manifest patch that sets `UPSTREAM_14B_URL` to `http://vllm-qwen3-32b-awq.aither-inference.svc:8000` is missing.
- The equivalent authoritative deploy-time values for both upstream tokens and any non-default upstream URLs are absent; secret values are neither required nor sought, but the names of Secret/ConfigMap references and their wiring are needed for provenance.
- No tracked deployment path connects `deploy/vllm-32b-instruct-awq.yaml` and `deploy/vllm-qwen3-32b-awq.yaml` to `deploy/30-services.sh` or another current orchestrator.
- No tracked generator or verification evidence connects current `services/portal-frontend/index.html` and `app.js` to the inline `aither-portal-frontend-config` applied by the main script.
- Repository history cannot prove which manifest or ConfigMap, if any, is currently installed. Runtime state would require separately authorized Kubernetes/Connector evidence.
- The repository does not establish whether existing persisted users/keys were migrated from `model:32b:chat`; only new-issuer behavior and compatibility consumption are proven.

## Result

INCONCLUSIVE

The repository supports the intended canonical model/scope contract in current source and proves that `model:32b:chat` is no longer a new issuer default. However, ConfigMap/deployment provenance is not sufficiently demonstrated: the Qwen3 upstream override is absent, current model manifests are not connected to the main deploy script, and the applied frontend ConfigMap is not linked to current source. Repository evidence therefore cannot prove or disprove the effective deployed configuration.
