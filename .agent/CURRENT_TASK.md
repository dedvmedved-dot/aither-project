# AITHER-LIVE-PORTAL-SOURCE-DISCOVERY-R2

## Purpose

Read-only discovery only. Establish with runtime evidence which frontend artifact is actually serving the live Aither Portal seen by users. This R2 supersedes the blocked R1 handoff and uses a clean baseline at `a29eb83833bfb004c18bfdb2c9f94aa2b719c033` so that the root-executor handoff scope contains only `.agent/CURRENT_TASK.json` and `.agent/CURRENT_TASK.md`.

Do not modify Portal, Kubernetes objects, models, backend, Identity, Gateway, documentation outside the single evidence file, or any runtime state.

## Governance

- Source of Truth: `dedvmedved-dot/aither-project`, branch `aither-v2`.
- Executor: **Hermes only** through the existing host runner/H2 path.
- ChatGPT is Architect / External Auditor / Acceptance Authority.
- No Codex execution is authorized.
- Hermes must not commit or push; host runner finalizes.
- This task is diagnostic and read-only except for writing the allowed evidence file.
- Do not weaken or bypass root-executor governance checks.

## Exact objective

Prove the complete live serving chain:

`user-facing Portal URL -> ingress/reverse proxy -> service -> workload/deployment -> pod/container -> image and/or mounted ConfigMap/static content -> served HTML/JS fingerprint -> matching repository artifact (if any)`.

Do not infer from filenames. Do not assume `portal/static/index.html`, `deploy/portal-frontend-combined.html`, `portal/dist/index.html`, or any manifest is active until runtime evidence proves it.

## Required checks

1. Record UTC timestamp and start HEAD.
2. Identify the namespace and all Kubernetes objects that participate in serving the user-facing Portal frontend: ingress/route/reverse proxy if visible, Service, Deployment/StatefulSet/Pod, container name, image reference/digest where available.
3. Record relevant volume mounts and ConfigMap/static-file sources without reading or printing any Secret values.
4. Determine the exact file/content served for the Portal entry page and relevant model-selector JavaScript. Use read-only commands only.
5. Compute deterministic SHA-256 fingerprints for the live served entry HTML and, where separate, the relevant JS bundle/static asset. Do not alter those files.
6. Compute/compare SHA-256 fingerprints for candidate repository frontend artifacts and determine whether any is byte-identical to the live asset.
7. Classify each candidate examined as one of:
   - `ACTIVE/CANONICAL` — runtime proves it maps to the live served content;
   - `SUPERSEDED` — historical/previous deployment artifact;
   - `UNREFERENCED/UNKNOWN` — no runtime evidence ties it to live Portal.
8. From the live served content, record the model labels/IDs that are actually presented or referenced by the current Portal. This is observation only; do not change anything.
9. Record whether the live selector appears hardcoded or populated from `/api/v1/models`, based on served source/runtime evidence. Do not authenticate using secrets and do not create credentials in this task.
10. If an unauthenticated request can safely show the Portal HTML/static assets, capture only non-sensitive status/headers/fingerprints needed for evidence. No credentials, cookies, tokens, Secret values, Authorization headers, or generated model content may be recorded.
11. Do not restart, rollout, patch, scale, exec-write, delete, create, or apply any Kubernetes object.
12. Do not modify backend routing or model deployments.

## Candidate repository artifacts to examine read-only

At minimum, if present:

- `portal/static/index.html`
- `deploy/portal-frontend-combined.html`
- `portal/dist/index.html`
- `aither-v2/services/portal-frontend/k8s/portal-frontend.yaml`
- any frontend file/manifests directly referenced by the live workload or its ConfigMap/image build chain.

If the live runtime points to another repository path, include that exact path in the evidence. Do not modify it in this task.

## Required evidence file

Write exactly:

`docs/evidence/AITHER_LIVE_PORTAL_SOURCE_DISCOVERY_R2.md`

It must contain:

- task ID, baseline/start HEAD, timestamps;
- exact live Portal serving chain;
- namespace/workload/service/pod/container/image identity;
- mounts/ConfigMaps/static source identity, excluding secrets;
- live HTML/JS SHA-256 fingerprints;
- repository candidate fingerprints;
- mapping table: runtime artifact -> repository artifact;
- candidate classification table (`ACTIVE/CANONICAL`, `SUPERSEDED`, `UNREFERENCED/UNKNOWN`);
- actual model labels/IDs observed in live served frontend;
- evidence whether model catalog is hardcoded vs API-populated;
- list of commands used, sanitized of sensitive values;
- explicit statement `RUNTIME_MUTATIONS: NONE`;
- explicit statement `SECRETS_EXPOSED: NO`;
- final conclusion naming the canonical live frontend source, or `NOT PROVEN` with the exact missing evidence.

## PASS criteria

PASS only if:

- no runtime mutation occurred;
- no secret was read or exposed;
- the actual live Portal serving chain is proven to a specific workload/content source;
- the live served frontend fingerprint is captured;
- repository candidates are classified using evidence rather than filename assumptions;
- the evidence clearly states which repository artifact is canonical, or explicitly proves that no current repository artifact matches the live content.

If any required runtime identity cannot be established, return `BLOCKED` rather than guessing.

STOP after producing the evidence file. Do not proceed to Portal correction, documentation correction, deployment, authentication testing, or any later roadmap stage.
