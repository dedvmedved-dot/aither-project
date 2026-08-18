# AITHER-MVP-EXT-API-CHAT-RECOVERY-R1

## Goal
Restore the Aither Test Zone external OpenAI-compatible chat endpoint on `http://10.129.13.78:30080/api/v1` and eliminate logging of full API/Bearer secrets.

## Proven current runtime facts
- `GET /api/v1/models` on `10.129.13.78:30080` returns HTTP 200.
- Returned canonical models: `qwen2.5-32b-instruct`, `qwen3-32b`.
- `POST /api/v1/chat/completions` on the same endpoint returns HTTP 404 with `{"detail":"Not Found"}`.
- Astra Monitoring proxies correctly to `http://10.129.13.78:30080/api/v1/chat/completions`; it reproduces the Aither-side 404.
- A full API key was previously exposed in diagnostic/application logs. Treat it as compromised. Never print or commit secret values.

## Mandatory execution order
INSPECT -> PROVE ROOT CAUSE -> MINIMAL FIX -> DEPLOY -> TEST -> RETEST -> EVIDENCE -> STOP.

Do not assume which component is broken. First prove which Service/Pod/container/image serves NodePort 30080 and which component emits the 404.

## Preflight and topology
Record safe evidence for:
- hostname/user/uid/pwd
- `git rev-parse HEAD`
- `git status --short`
- nodes, pods, services, deployments, endpoints matching aither/portal/bff/gateway/nginx/vllm
- exact Service owning NodePort 30080
- selector, targetPort, endpoints
- backend Deployment/Pod/container/image/imageID/command/args
- mounted ConfigMap/Secret names and environment variable names only; never secret values

If repository is dirty at start, STOP BLOCKED. Do not reset/clean/checkout/switch.

## Route matrix before change
Test and record status codes for:
- GET `/`
- GET `/health`
- GET `/api/v1/health`
- GET `/api/v1/models`
- POST `/api/v1/chat/completions`

For POST test no-auth, wrong-auth, and valid-auth safely. Never use verbose curl with a real Authorization header. Use an existing secret source/secure environment variable without echoing it.

Determine the exact component returning `{"detail":"Not Found"}`. Inspect application routes/OpenAPI or registered route table inside the runtime where safe.

## Source/runtime drift audit
Compare deployed runtime against the repository, especially:
- `portal/server.ts`
- `portal/api-gateway.ts`
- `portal/nginx/default.conf`
- `portal/nginx.conf`
- the actual image/config used by the live Test Zone

Prove one root cause such as stale image, stale ConfigMap, wrong image, wrong Service selector, wrong nginx upstream/rewrite, absent route, different prefix, mixed old/new runtime artifacts, or another evidenced cause.

Explain why live `/api/v1/models` returns `qwen2.5-32b-instruct` and `qwen3-32b` even if some repository source still contains legacy model IDs.

## Minimal correction only
Target external contract:
- Base URL: `http://10.129.13.78:30080/api/v1`
- GET `/models`
- POST `/chat/completions`
- canonical models only: `qwen2.5-32b-instruct`, `qwen3-32b`

Do not revert runtime to legacy `qwen2.5-14b` / `qwen2.5-32b`.

`POST /api/v1/chat/completions` must support at least `model`, `messages`, `max_tokens`, `temperature`, `stream`. With `stream:false`, return OpenAI-compatible JSON with non-empty `choices[0].message.content`.

Do not disable existing auth. Do not create a second arbitrary NodePort or bypass the Aither Gateway directly to vLLM.

## Security fix
Inspect source/runtime logging for full `Authorization`, Bearer/API key, token, secret, or password values. If the real API key can be emitted, fix logging so secrets are redacted/masked. Confirm new logs after E2E contain no real secret.

Do not rotate/revoke/delete keys by database mutation in this task. Report compromised-key rotation as OWNER REQUIRED or SAFE API AVAILABLE. Never include the key itself in evidence.

## Deployment constraints
Apply only the exact changed workload/config objects required by the proven root cause. Do not apply an entire manifests directory. Verify rollout, readiness, pods and endpoints afterward.

Do not change CNI, control-plane, model GPU placement, PostgreSQL data/schema, billing, users, ROADMAP, E1 evidence, observability, Telegram, YooKassa, Parsec, backups or `.agent/*`.

## Required E2E acceptance tests
1. GET `/api/v1/models` -> HTTP 200 and both canonical model IDs present.
2. POST chat with `qwen2.5-32b-instruct`, `stream:false`, prompt `Reply exactly: AITHER_OK` -> HTTP 200, non-empty assistant content.
3. POST chat with `qwen3-32b`, same conditions -> HTTP 200, non-empty assistant content.
4. Invalid model -> 4xx, not 500.
5. No auth -> 401/403.
6. Wrong auth -> 401/403.
7. Health endpoint -> record real path/status.
8. Fresh edge/backend logs after tests -> no full secret exposure.

Astra Monitoring must remain unchanged. Final compatibility target:
- API key: Aither bearer key (value never shown)
- Base URL: `http://10.129.13.78:30080/api/v1`
- Model: `qwen2.5-32b-instruct` or `qwen3-32b`

## Evidence
Create only `docs/evidence/EXT_API_CHAT_RECOVERY_R1.md` for the audit report, plus the minimum allowed source files actually needed for the repair.

Evidence must include baseline/start HEAD, safe runtime topology before/after, route matrix before/after, backend image/imageID, proven root cause, source/runtime drift conclusion, exact files/objects changed, rollout result, both model E2E results, negative auth tests, secret logging result, Astra compatibility conclusion, remaining blockers, and final worktree state.

No API keys, JWTs, passwords, cookies, Secret values, private keys, or sensitive request dumps in evidence.

## Git/governance prohibitions for Hermes
Hermes MUST NOT run git add/commit/push/reset/clean/checkout/switch/merge/rebase/tag/ref/index/history mutation. Read-only git commands are allowed. Hermes MUST NOT modify `.agent/EXECUTION_RESULT.json`. Host runner owns final sync/commit/push/result.

## PASS gate
PASS only if the 404 source and root cause are proven; NodePort topology is proven; `/api/v1/models` is still 200; both canonical model chats return HTTP 200 through `10.129.13.78:30080`; invalid/no-auth/wrong-auth tests behave correctly; new logs expose no real secret; K8s is healthy after the minimal fix; only allowed source/evidence paths changed; no secret is committed; and Hermes performed no Git write.

Otherwise report BLOCKED/FAIL with evidence and STOP.
