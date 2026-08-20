# AITHER-MVP-SOURCE-RUNTIME-DRIFT-AUDIT-R1

## Goal
Perform a read-only audit of Test Zone source/runtime drift after the external API recovery and Hermes live-observability work. Produce exact evidence of which deployed runtime components/configs differ from GitHub Source of Truth, and identify the narrowest reconciliation scope. Do not modify runtime or source code other than the evidence file.

## Baseline
- Branch: `aither-v2`
- Baseline SHA: `11574b78b992009cb72727514a83908b51eea8ed`

## Required execution order
PREFLIGHT -> OBSERVE LIVE HERMES STATUS -> INSPECT RUNTIME READ-ONLY -> COMPARE WITH GITHUB WORKTREE -> CLASSIFY DRIFT -> PROPOSE EXACT RECONCILIATION PATHS -> EVIDENCE -> STOP.

## Hermes live-observability acceptance sub-gate
This is the first real Hermes task after OBS-R2. During execution, the external runner-live observer should expose sanitized Hermes phases without prompt/command/secret content. Do not alter observer code in this task. Evidence should record only whether the expected phases were observed by the execution environment if available; never copy runner-live secret-bearing content (none should exist).

## Read-only runtime scope
You MAY use read-only Kubernetes commands such as get/describe/logs limited to the Test Zone components needed to prove drift. Do not apply/patch/edit/delete/restart/rollout anything.

Inspect at minimum:
- NodePort/Service/Endpoint path for `10.129.13.78:30080`.
- `aither-portal` nginx-only runtime and mounted ConfigMap names/keys.
- `aither-portal-backend` runtime image, routes/OpenAPI or equivalent route inventory, non-secret env variable names, mounted ConfigMap/Secret names only.
- `aither-bff`, `aither-identity`, and model upstream Services only as needed to prove routing ownership.
- Canonical model IDs and external API prefixes.

Never print Secret values, Authorization headers, full API keys, passwords, JWTs, tokens, or environment values that are credentials.

## Repository comparison scope
Compare the live runtime against relevant current repository files. Read as many source files as needed, but do not modify them. At minimum examine whether these are current, legacy, or superseded:
- `portal/server.ts`
- `portal/api-gateway.ts`
- `portal/nginx/default.conf`
- `portal/nginx.conf`
- `portal/Dockerfile`
- any deploy/manifests/tools files actually corresponding to the live `aither-portal`, `aither-portal-backend`, `aither-bff`, or identity runtime
- architecture/governance docs that define the canonical external API and model IDs

Use exact evidence, not assumptions.

## Required drift classification
For every material mismatch classify one of:
- `RUNTIME_AHEAD_OF_SOURCE`
- `SOURCE_AHEAD_OF_RUNTIME`
- `LEGACY_SOURCE_RETAINED`
- `GENERATED_RUNTIME_NOT_CAPTURED`
- `NO_DRIFT`
- `UNKNOWN_NEEDS_OWNER_EVIDENCE`

For each mismatch state:
1. live object/component;
2. runtime fact;
3. repository path(s);
4. exact mismatch;
5. operational/security impact;
6. whether it blocks E1 Final Acceptance;
7. narrowest exact repository paths that a later reconciliation task would need to change.

## Mandatory acceptance questions
Answer explicitly:
1. Is the currently working external API configuration reproducible from GitHub alone on a fresh deployment?
2. Are canonical models `qwen2.5-32b-instruct` and `qwen3-32b` represented correctly in the active Source of Truth?
3. Is the live `/api/v1/models` + `/api/v1/chat/completions` routing represented in a source-controlled deployment/config artifact?
4. Is legacy Fastify portal source still authoritative, compatibility-only, or stale?
5. Which exact files should become the canonical deployment Source of Truth before E1 can be accepted?
6. Can E1 be rerun now, or must reconciliation occur first?

## Sanity checks
Read-only only:
- GET `/health` if safely reachable without auth.
- GET `/api/v1/models` only if an already-existing authorized credential can be used without exposing it and without creating/modifying credentials; otherwise record AUTH_REQUIRED and do not create a key.
- POST no-auth `/api/v1/chat/completions` may be used to confirm 401/403 contract. Do not create a new credential.

## Repository evidence
Create exactly:
`docs/evidence/SOURCE_RUNTIME_DRIFT_AUDIT_R1.md`

Final ownership must be uid/gid 1000:1000. Hermes must not perform any Git write. Host runner will commit/push.

## Forbidden
- Any runtime mutation.
- Any deployment restart/rollout/apply/patch/edit/delete.
- Any DB write or direct DB mutation.
- Creating, rotating, revoking, or modifying API keys/users/sessions.
- Secret access/value extraction.
- Changes to `.agent/*`, ROADMAP, application source, manifests, portal code, identity code, or deployment files.
- Any git add/commit/push/reset/clean/checkout/switch/merge/rebase/tag/ref write.

## PASS gate
PASS only if:
- drift is proven with concrete runtime + repository evidence;
- all mandatory acceptance questions are answered;
- exact next reconciliation paths are identified;
- no runtime/DB/credential/source mutation occurred;
- only the evidence file changed;
- evidence ownership is 1000:1000;
- no secret is printed or committed;
- Hermes performed no Git write.

Otherwise BLOCKED with evidence and STOP.
