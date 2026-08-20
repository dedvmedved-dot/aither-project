# TASK: AITHER-MVP-HERMES-LIVE-OBS-R1

## Goal
Add safe live observability for Hermes execution so `runner-live` shows that the H2 bridge is connected/alive during long-running Hermes tasks instead of exposing only the initial `HOST_RUNNER_START` state.

## Baseline
- Repository: `dedvmedved-dot/aither-project`
- Branch: `aither-v2`
- Baseline SHA: `5b67c3eba402ce8bd0d7e4a5c143c634237a4c97`
- GitHub is Source of Truth.

## Proven defect
`codex_observer.py` publishes periodic safe heartbeat/progress metadata. `hermes_observer.py` currently connects to `/run/aither-hermes/execute.sock`, sends fixed `RUN\n`, and blocks waiting for the final bridge response for up to 3600s without publishing intermediate live status. Therefore an active Hermes run is externally indistinguishable from a stalled H2 bridge.

## Required behavior
Implement safe live status for Hermes without changing the accepted H2 execution contract:
- still send exactly `RUN\n`;
- accept no prompt or arbitrary command from caller;
- do not invoke Hermes CLI directly;
- do not use shell/eval/exec;
- keep bounded response and fail-closed behavior;
- preserve 3600s hard timeout semantics unless tests prove an equivalent safer implementation.

## Required live states
At minimum publish sanitized `runner-live` metadata for:
- `HERMES_DISPATCH` before connect/send;
- `H2_CONNECTED` after successful socket connect;
- `HERMES_RUNNING` while waiting for the bridge response;
- periodic heartbeat while waiting;
- `HERMES_COMPLETE` on successful response;
- `HERMES_BLOCKED` or equivalent on timeout/connect/empty/fail-closed result.

Use existing `.agent/runner_live.py` and its safe-key whitelist. Do not publish response text, prompt text, commands, stdout/stderr, socket payload contents, secrets, credentials, or reasoning.

A safe status may include only already-whitelisted metadata such as task_id, state, phase, pid, timestamps, silent_seconds, stall_warning, process_alive, exit_code, executor, and message_code.

## Task identity
Read task_id safely from `.agent/CURRENT_TASK.json` as `codex_observer.py` already does. Never include the task prompt/body in live status.

## Heartbeat
Reuse the same environment conventions where practical:
- `AITHER_HEARTBEAT_SECONDS` default 30;
- `AITHER_STALL_WARNING_SECONDS` default 600;
- Hermes hard timeout remains bounded by `AITHER_HERMES_TIMEOUT` / 3600s.

The implementation must publish heartbeat while the socket call is waiting. Do not solve this by weakening the timeout or by busy-looping aggressively.

## Testing
Extend unit tests to prove at minimum:
1. fixed signal remains exactly `RUN\n`;
2. no arbitrary argv accepted;
3. successful bridge response still returns success;
4. BLOCKED_/FAIL responses remain fail-closed;
5. connect failure produces safe blocked status;
6. timeout produces safe blocked status;
7. periodic heartbeat can occur while a fake bridge delays its response;
8. no response body/prompt/secret appears in published status;
9. `runner_live.sanitize_status` remains the final safety boundary;
10. no direct Hermes CLI / shell=True / os.system / eval / exec is introduced.

Tests must not require root, Kubernetes, network access, package installation, or the real H2 socket.

## Scope
Allowed repository changes only:
- `.agent/hermes_observer.py`
- `.agent/tests/test_hermes_observer.py`
- `.agent/tests/test_live_observability.py`
- `docs/evidence/HERMES_LIVE_OBS_R1.md`

Do not modify host_task_runner, systemd units, runner_live, governance docs, CURRENT_TASK/EXECUTION_RESULT, application source, manifests, runtime, DB, users, credentials, Kubernetes, or `/root/.hermes`.

## Ownership contract
Root Hermes MUST NOT leave any changed repository file owned by uid/gid 0. Every changed path must be uid=1000 gid=1000 before STOP. Prefer writing as `codex`; otherwise chown only the exact changed allowed paths. No recursive chown. No `safe.directory=*`.

## Git prohibitions
Hermes MUST NOT run git add/commit/push/reset/clean/checkout/switch/merge/rebase/tag/ref/index/history mutation. Read-only git commands only. Host runner owns final validation/commit/push/result.

## Evidence
Create `docs/evidence/HERMES_LIVE_OBS_R1.md` with:
- baseline/start HEAD;
- defect statement;
- implementation summary;
- exact live-state contract;
- security/sanitization proof;
- unit-test results;
- changed paths;
- ownership metadata;
- final worktree state;
- explicit statement that H2 protocol stayed `RUN\n` only and no Hermes direct CLI was introduced.

## PASS gate
PASS only if tests pass; heartbeat/status updates are implemented without exposing sensitive content; H2 contract remains unchanged; no runtime or systemd modification occurs; only allowed paths change; ownership is 1000:1000; Hermes performs no Git write.

Otherwise BLOCKED/FAIL with exact evidence and STOP.
