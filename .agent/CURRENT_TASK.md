# AITHER-MVP-EXT-API-CHAT-RECOVERY-R2

## Goal
Repeat the Test Zone external API recovery after R1 was rolled back by governance ownership enforcement. Preserve the same technical scope, but obey the repository ownership handoff contract so host runner can accept the result.

## Baseline
- Branch: `aither-v2`
- Baseline SHA: `f8557f930393138cf6a9fa6e6be1ab2383890529`
- R1 technical work was not committed; runner published BLOCKED because `docs/evidence/EXT_API_CHAT_RECOVERY_R1.md` was owned by uid 0 instead of uid 1000.

## Mandatory ownership contract
Root Hermes MUST NOT leave any changed repository path owned by uid/gid 0.

For every repository file created or replaced during this task, ensure final ownership is exactly the repository owner (`codex`, uid 1000, gid 1000) BEFORE returning control to host runner.

Preferred safe methods:
- write/create the repository file as user `codex`; or
- if root execution is unavoidable, immediately set ownership only on the exact changed allowed path to `1000:1000`.

Do NOT recursively chown the repository. Do NOT change repository root ownership. Do NOT use `safe.directory=*`.

Before STOP, run ownership verification for every changed allowed path and record only uid/gid/mode/path, never secret content. PASS requires every existing changed implementation path to show uid 1000 and gid 1000.

## Proven runtime facts
- `GET http://10.129.13.78:30080/api/v1/models` returns HTTP 200.
- Models returned: `qwen2.5-32b-instruct`, `qwen3-32b`.
- `POST http://10.129.13.78:30080/api/v1/chat/completions` returns HTTP 404 with `{"detail":"Not Found"}`.
- Astra Monitoring correctly proxies to that POST and reproduces the Aither-side 404.
- A full API key was previously exposed in logs. Treat it as compromised. Never print or commit any secret value.

## Required execution order
INSPECT -> PROVE ROOT CAUSE -> MINIMAL FIX -> DEPLOY -> TEST -> RETEST -> OWNERSHIP VERIFY -> EVIDENCE -> STOP.

## Preflight
Record hostname/user/uid/pwd, `git rev-parse HEAD`, `git status --short`. Worktree must be clean. Do not reset/clean/checkout/switch.

Determine exact NodePort 30080 topology:
NodePort -> Service -> endpoints -> Pod -> container -> image/imageID -> command/args -> mounted ConfigMap/Secret names and env variable names only.

Do not print Secret values.

## Route matrix before
Record status codes for:
- GET `/`
- GET `/health`
- GET `/api/v1/health`
- GET `/api/v1/models`
- POST `/api/v1/chat/completions`

For POST test no-auth, wrong-auth and valid-auth safely. Never use verbose curl with a real Authorization header.

Prove which component emits `{"detail":"Not Found"}` by inspecting actual runtime routes/OpenAPI or equivalent.

## Source/runtime drift audit
Compare deployed runtime against repository, especially:
- `portal/server.ts`
- `portal/api-gateway.ts`
- `portal/nginx/default.conf`
- `portal/nginx.conf`
- actual live Test Zone image/config

Prove root cause: stale image, stale ConfigMap, wrong image, wrong Service selector, nginx upstream/rewrite, absent route, different prefix, mixed runtime artifacts, or another evidenced cause.

Explain the new live model IDs versus any legacy source model map.

## Minimal correction
External contract must remain:
- Base URL `http://10.129.13.78:30080/api/v1`
- GET `/models`
- POST `/chat/completions`
- models `qwen2.5-32b-instruct`, `qwen3-32b`

Do not create a second NodePort. Do not bypass Gateway directly to vLLM. Do not disable authentication. Do not revert to legacy model IDs.

POST must accept at least `model`, `messages`, `max_tokens`, `temperature`, `stream`. For `stream:false`, return OpenAI-compatible JSON with non-empty `choices[0].message.content`.

## Security logging
Inspect relevant edge/backend source/runtime logging for full Authorization/Bearer/API key/token/secret/password output. If present, minimally redact/mask it. New logs after E2E must contain no real secret.

Do not rotate/delete the compromised key by DB mutation. Report rotation as OWNER REQUIRED or SAFE API AVAILABLE. Never include the key itself.

## Deployment constraints
Apply only exact changed workload/config objects needed by the proven root cause. Do not apply a whole manifests directory. Verify rollout/readiness/endpoints afterward.

Do not modify CNI, control-plane, PostgreSQL schema/data, billing, users, ROADMAP, E1 evidence, observability, Telegram, YooKassa, Parsec, backups or `.agent/*`.

## Required E2E tests
1. GET `/api/v1/models` -> HTTP 200, both canonical model IDs present.
2. POST chat `qwen2.5-32b-instruct`, `stream:false`, prompt `Reply exactly: AITHER_OK` -> HTTP 200, non-empty assistant content.
3. POST chat `qwen3-32b` -> HTTP 200, non-empty assistant content.
4. Invalid model -> 4xx, not 500.
5. No auth -> 401/403.
6. Wrong auth -> 401/403.
7. Health -> record actual supported path/status.
8. Fresh logs -> no full secret exposure.

Astra Monitoring itself must remain unchanged.

## Allowed repository changes
Only exact paths from CURRENT_TASK.json. Evidence file is `docs/evidence/EXT_API_CHAT_RECOVERY_R2.md`.

## Git/governance prohibitions
Hermes MUST NOT run git add/commit/push/reset/clean/checkout/switch/merge/rebase/tag/ref/index/history mutation. Read-only git commands only. Hermes MUST NOT modify `.agent/EXECUTION_RESULT.json`.

## Final ownership gate
Before STOP, determine changed implementation paths using read-only Git status. For each existing changed allowed path, output safe metadata equivalent to `uid gid mode path`.

Required:
- UID = 1000
- GID = 1000

If any changed path is still owned by root, correct ownership only for that exact allowed path before STOP. Do not recursively change ownership.

## PASS gate
PASS only if:
- source of 404 and root cause proven;
- NodePort topology proven;
- `/api/v1/models` stays HTTP 200;
- both model chat requests return HTTP 200 through `10.129.13.78:30080`;
- invalid/no-auth/wrong-auth tests behave correctly;
- new logs expose no secret;
- K8s healthy after minimal fix;
- only allowed paths changed;
- every changed repository path is uid/gid 1000:1000;
- no secret committed;
- Hermes performed no Git write.

Otherwise BLOCKED/FAIL with evidence and STOP.
