# SCOPE-Q25-D1 ConfigMap Provenance Remediation Plan

This is an implementation plan derived from `configmap-provenance-audit.md`. It does not change application code, manifests, configuration, workflows, or runtime state. Every repository change below requires a later task whose `allowed_paths` explicitly includes the named path; every cluster or browser action requires separate runtime authorization.

The target contract is:

- `qwen2.5-32b-instruct` -> `model:qwen2.5:chat`;
- `qwen3-32b` -> `model:qwen3:chat`;
- `model:32b:chat` remains accepted only as temporary Qwen2.5 compatibility and is not issued by a new-user or new-key default;
- the existing `UPSTREAM_14B_*` names may remain stale names, but their Qwen3 values and consumers must have traceable provenance.

## Confirmed Gaps

1. `aither-v2/services/portal-backend/k8s/portal-backend.yaml` supplies none of `UPSTREAM_14B_URL`, `UPSTREAM_14B_TOKEN`, `UPSTREAM_32B_URL`, or `UPSTREAM_32B_TOKEN`. With tracked defaults, Qwen3 is routed through `UPSTREAM_14B_URL` to the superseded `vllm-14b-instruct` Service rather than `vllm-qwen3-32b-awq`.
2. The repository has no authoritative non-secret configuration object for the two upstream URLs and no named Secret-key wiring for the two upstream tokens. Secret values are not required in Git, but their object/key references are required for provenance.
3. `aither-v2/deploy/30-services.sh` does not apply `aither-v2/deploy/vllm-32b-instruct-awq.yaml` or `aither-v2/deploy/vllm-qwen3-32b-awq.yaml`; it still applies the superseded 14B deployment path and checks the superseded deployment name.
4. `aither-v2/services/portal-frontend/k8s/portal-frontend.yaml`, which `30-services.sh` applies, embeds an old frontend. It is neither generated from nor checked against `services/portal-frontend/index.html` and `app.js`.
5. Repository history and source prove the canonical scope issuance rules, but do not prove the live Deployment environment, installed ConfigMaps/Secrets, live served frontend, model Service endpoints, or persisted legacy-scope population.

## Required Repository Changes

Implement the following as one separately authorized repository change set. Do not rename `UPSTREAM_14B_*` merely because the name is stale.

1. Add a non-secret ConfigMap in `aither-v2/services/portal-backend/k8s/portal-backend.yaml` named `aither-portal-backend-upstreams`, in namespace `aither-inference`, with exactly these routing values:

   - `UPSTREAM_14B_URL: http://vllm-qwen3-32b-awq.aither-inference.svc:8000`
   - `UPSTREAM_32B_URL: http://vllm-32b-instruct-awq.aither-inference.svc:8000`

   Wire both Deployment environment variables to the corresponding `configMapKeyRef`; do not duplicate the URLs as literal Deployment values.

2. Wire tokens in the same Deployment through `secretKeyRef`, using the existing cluster Secret contract `vllm-api-key` and key `VLLM_API_KEY` for both `UPSTREAM_14B_TOKEN` and `UPSTREAM_32B_TOKEN`. Do not add token values to a ConfigMap, manifest, generator input, test fixture, log, or evidence file. Before implementation, the authorized runtime owner must confirm that this Secret/key is the intended shared credential; if it is not, the later repository task must name the approved Secret and keys without recording their values.

3. Update `aither-v2/deploy/30-services.sh` so its inference phase applies, in dependency order, both `deploy/vllm-32b-instruct-awq.yaml` and `deploy/vllm-qwen3-32b-awq.yaml` before Portal Backend. Replace the superseded `vllm-14b-instruct` readiness target with `vllm-32b-instruct-awq` and `vllm-qwen3-32b-awq`. Preserve failure accounting so either apply failure makes the script exit nonzero. Do not delete historical manifests in this remediation.

4. Make `aither-v2/services/portal-frontend/index.html` and `app.js` the only editable frontend content sources. Add `aither-v2/services/portal-frontend/scripts/render-configmap.py` to deterministically render both files into `aither-v2/services/portal-frontend/k8s/portal-frontend.yaml`, while preserving the Deployment, Service, nginx configuration, metadata, mount paths, and resource settings already in that manifest. The renderer must support `--check`, which renders in memory and exits nonzero with a diff when the committed manifest is stale. Regenerate the manifest and add the check to the repository's existing validation workflow or, if no suitable workflow exists, to a checked-in validation script invoked by CI. Do not maintain a second hand-edited inline copy.

5. Correct the stale current-state documentation in `aither-v2/docs/models/MODEL_CATALOG.md` so Qwen2.5's primary scope is `model:qwen2.5:chat`, `model:32b:chat` is explicitly transition-only, and Qwen3 uses `model:qwen3:chat`. Amend the other mixed-age current-state documents identified by the audit only if they are intended to describe current state; retain historical statements when clearly date-qualified.

6. Add repository tests that parse the rendered Kubernetes YAML and fail unless all of these invariants hold:

   - each model Deployment uses its required `--served-model-name` and has a same-manifest Service whose selector matches its pod labels;
   - Portal Backend resolves both upstream URL variables through `aither-portal-backend-upstreams` and both token variables through Secret references, with no secret literal;
   - the Qwen3 URL targets `vllm-qwen3-32b-awq` and the Qwen2.5 URL targets `vllm-32b-instruct-awq`;
   - `30-services.sh` applies both current model manifests and waits for both current Deployment names;
   - the frontend renderer's `--check` succeeds;
   - new Identity users and the frontend key issuer request `model:qwen2.5:chat` and `model:qwen3:chat`, never `model:32b:chat`, while Portal Backend continues to accept the legacy scope only for Qwen2.5.

## Validation Plan

For the later repository implementation task, collect command output and exit status for each step without exposing secret data:

1. Run the frontend renderer in `--check` mode and verify a second normal render produces no Git diff.
2. Parse every changed YAML document with the repository's available YAML validator; run the invariant tests described above.
3. Run Portal Backend, Identity, and frontend test suites that cover model listing, key issuance, canonical authorization, Qwen2.5 legacy compatibility, wrong-scope denial, and upstream selection. Tests must use dummy token values supplied only in the test process environment.
4. Run `bash -n aither-v2/deploy/30-services.sh`. Exercise its manifest ordering and failure behavior with a stubbed `kubectl`; do not contact a cluster during repository validation.
5. Search tracked current implementation/deployment paths for `model:32b:chat` and classify every match as compatibility-only or historical. Fail if any active issuer default emits it.
6. Run the task-prescribed validation commands, including `git diff --check`, and verify that the diff contains only paths authorized by that later task.
7. Record the exact Git commit SHA and changed-path list for independent Architect/Connector audit. A local PASS is not acceptance and does not establish runtime state.

Repository validation is complete only when all checks above pass and an independent audit confirms the actual diff and scope. It still does not establish that any manifest is installed.

## Runtime Evidence Still Required

After repository acceptance, a separate task must explicitly authorize Kubernetes, deployment, and the required evidence collection. Secret values must remain redacted; evidence should show only object names, key names, references, and safe hashes where needed.

1. Before rollout, capture the live Portal Backend Deployment image identity, revision, environment variable sources, referenced ConfigMap name/keys, and referenced Secret name/keys. Capture the live upstream ConfigMap values for the two non-secret URLs.
2. Capture the live Qwen2.5 and Qwen3 Deployments, Services, selectors, ready endpoints, image digests, and `--served-model-name` arguments. This must demonstrate that each configured DNS target resolves to the intended ready workload.
3. Apply only the independently accepted manifests through the authorized deployment mechanism. Capture apply output, rollout revisions, rollout status, pod readiness, and rollback instructions/results required by that task.
4. After rollout, repeat the Deployment/ConfigMap/Service evidence and compare it with the accepted Git commit. Prove the live frontend ConfigMap content hashes match the deterministic render of the committed `index.html` and `app.js`.
5. Through the normal external path `https://fb1.spb.ru:10443/v1/*`, use registered non-admin accounts and newly issued `aither_...` API keys to verify model discovery and successful Bearer-authenticated chat for both current model IDs. Verify cross-model/wrong-scope denial. Do not substitute admin credentials, browser JWT, SSH, port-forwarding, gateway credentials, or direct in-cluster calls for this evidence.
6. Collect Owner-provided browser/WUI evidence that the deployed UI shows both current model IDs and issues only the canonical scopes. Command-line requests cannot replace required WUI evidence.
7. Under separate database-read authorization, measure existing users/keys that retain `model:32b:chat` and classify migration needs. Do not mutate records as part of evidence collection.

Only the ChatGPT Architect may classify the resulting evidence as `PASSED` or `CONNECTOR VERIFIED`.

## Result

PASS — an implementation-ready repository remediation and validation plan has been produced. No application code, manifest, configuration, workflow, runtime, database, Kubernetes resource, secret, or Git metadata was changed. D1 remains unverified pending a separately authorized implementation, repository audit, deployment, Kubernetes evidence, external API evidence, and Owner WUI evidence.
