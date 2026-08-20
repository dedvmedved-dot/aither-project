# AITHER-MVP-HERMES-LIVE-OBS-R2

## Goal
Repair the Hermes execution observability gap without changing the accepted H2 socket protocol, root-Hermes boundary, repository ownership model, or host-runner governance.

R1 was BLOCKED before implementation with `command exited with status 1`. The Architect review identified a task-definition defect: validation invoked existing executable unittest scripts through `python3 -m unittest` using hidden-directory paths. R2 uses direct script execution and switches the executor to `codex` because this task modifies the Hermes execution wrapper itself.

## Baseline
- Branch: `aither-v2`
- Baseline SHA: `a9279170c4d6d9fb4154f9135663eb04bf32b930`
- R1 result commit: `7c5bc3061b9ec4ccdbcf86a0d03b6988b5e089a0` — BLOCKED, no implementation paths committed.

## Required design
Keep the existing H2 contract exactly:
- Unix socket default `/run/aither-hermes/execute.sock`.
- Send exactly `RUN\n`.
- No caller prompt/command accepted.
- No direct Hermes CLI invocation.
- No shell/eval/exec.
- Existing timeout/max-response fail-closed behavior preserved.

Add sanitized live observability to the Hermes observer, using the existing `.agent/runner_live.py` publication mechanism and following the safety model of `.agent/codex_observer.py` where applicable.

Required externally visible states/phases must make these moments distinguishable in `runner-live`:
1. observer started / dispatch beginning;
2. H2 socket connected;
3. fixed RUN signal sent and Hermes execution considered running;
4. periodic heartbeat while waiting for bridge response;
5. bridge response completed successfully;
6. fail-closed terminal states for timeout/connect/empty/fail responses.

The exact naming may be concise, but evidence must show that a long-running Hermes call is distinguishable from a dead/stuck supervisor.

## Mandatory sanitized fields
Where applicable publish only safe metadata such as:
- `task_id`
- `state`
- `phase`
- `heartbeat_at`
- `started_at`
- `last_event_at`
- `silent_seconds`
- `process_alive`
- bounded non-sensitive counters/status codes

Never publish:
- bridge response body;
- Hermes stdout/stderr text;
- prompt/task markdown content;
- commands/argv containing user content;
- Authorization/API keys/tokens/passwords/secrets;
- environment values.

## Heartbeat behavior
- Default heartbeat interval should be comparable to Codex observer (about 30 seconds) and configurable through a narrowly named environment variable.
- Heartbeat publication must continue while blocked in socket receive; therefore implementation may need polling/select or bounded socket receive time slices rather than one synchronous 3600-second `recv` wait.
- The overall hard timeout remains fail-closed and must not be weakened.
- `runner-live` publication failure must not leak response content. Decide and document whether publication failure is fail-closed or best-effort; preserve executor safety either way.

## Tests
Extend/create tests to prove at minimum:
1. exactly `RUN\n` is sent;
2. arbitrary args remain rejected;
3. success response exits 0;
4. `BLOCKED_*` / `FAIL*` responses fail closed;
5. connection failure fails closed;
6. hard timeout fails closed;
7. bounded response remains bounded;
8. live status includes dispatch/connected/running/completed states for a fake Unix-socket bridge;
9. heartbeat advances during a deliberately delayed fake bridge response without exposing response text;
10. status payload contains no prompt/secret/bridge-body text;
11. no direct Hermes CLI, `shell=True`, `os.system`, eval/exec is introduced.

Use deterministic local fake Unix-socket tests. Do not call the real H2 bridge or root Hermes during unit tests.

## Validation
The host runner will run these directly:
- `python3 .agent/tests/test_hermes_observer.py`
- `python3 .agent/tests/test_live_observability.py`

Also run `python3 -m py_compile` on changed Python files and `git diff --check` before STOP.

## Evidence
Create `docs/evidence/HERMES_LIVE_OBS_R2.md` containing:
- root cause of R1 BLOCKED;
- before/after observability model;
- state/phase contract;
- sanitized field contract;
- heartbeat and hard-timeout semantics;
- test commands and exact PASS counts;
- changed paths;
- ownership metadata for changed paths;
- confirmation no runtime/H2/root-Hermes execution occurred;
- confirmation no secret/output content is published.

## Ownership and Git governance
All final changed repository paths must be owned by uid/gid 1000:1000. Codex is the executor, so preserve normal repository ownership.

Executor MUST NOT run git add/commit/push/reset/clean/checkout/switch/merge/rebase/tag/ref/history mutation. Read-only Git commands are allowed. Host runner alone finalizes commit/push.

## Scope
Allowed repository changes are exactly those listed in CURRENT_TASK.json:
- `.agent/hermes_observer.py`
- `.agent/tests/test_hermes_observer.py`
- `.agent/tests/test_live_observability.py`
- `docs/evidence/HERMES_LIVE_OBS_R2.md`

Do not modify `host_task_runner.py`, `systemd_runner.py`, `runner_live.py`, service units, H2 server, `/root/.hermes`, Kubernetes, database, portal, roadmap, or any other path.

## PASS gate
PASS only if:
- H2 fixed-signal contract is unchanged;
- heartbeat visibly progresses during delayed fake bridge execution;
- terminal success/failure states are published safely;
- no bridge body/prompt/secret is published;
- all direct validation scripts pass;
- only exact allowed paths changed;
- ownership gate passes;
- no Git write by executor.

Otherwise BLOCKED/FAIL with safe evidence and STOP.
