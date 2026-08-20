# Hermes Live Observability R2 — Codex Execution Evidence

## R1 root cause

R1 stopped before implementation because its validation definition invoked executable unittest scripts with `python3 -m unittest` and hidden-directory paths. R2 validates those scripts directly.

## Observability model

Before R2, the observer synchronously connected, sent `RUN\n`, and waited as long as the hard timeout without publishing progress. After R2, it publishes sanitized transitions through `runner_live.publish_status`: `H2_DISPATCH`, `H2_CONNECTED`, `HERMES_RUNNING`, periodic `HERMES_HEARTBEAT`, and terminal `H2_COMPLETED`, `H2_TIMEOUT`, `H2_CONNECT_FAILED`, `H2_EMPTY`, or `H2_FAIL_RESPONSE`.

Published states are `RUNNING` during dispatch, connection, execution, and heartbeat; `COMPLETED` after a successful response; and `BLOCKED` for every fail-closed terminal condition. Publication is best-effort: a runner-live failure does not alter the fixed H2 protocol or expose response data.

## Sanitized field contract and timing

Only allowlisted metadata is supplied: `task_id`, `state`, `phase`, `started_at`, `heartbeat_at`, `last_event_at`, `silent_seconds`, `process_alive`, and a bounded byte counter represented by `event_count`. Prompt/task content, commands, environment values, credentials, stdout/stderr, and bridge response bodies are never supplied to the publisher.

The heartbeat defaults to 30 seconds and is narrowly configurable with `AITHER_HERMES_HEARTBEAT_SECONDS`. Receive polling advances heartbeats while preserving one monotonic overall deadline; expiry still raises `socket.timeout`. Response accumulation remains capped by `AITHER_HERMES_MAX_RESPONSE`.

## Validation evidence

Final validation results from this executor:

- `python3 .agent/tests/test_hermes_observer.py` — environment BLOCKED: 11 tests ran, 6 passed, 1 failed, and 4 errored because the sandbox denied every fake Unix-socket `bind()` with `EPERM`.
- `python3 .agent/tests/test_live_observability.py` — environment BLOCKED: 12 tests ran, 11 passed and 1 errored because the sandbox denied the fake Unix-socket `bind()` with `EPERM`.
- `python3 -m py_compile .agent/hermes_observer.py .agent/tests/test_hermes_observer.py .agent/tests/test_live_observability.py` — PASS.
- `git diff --check` — PASS.

Changed paths:

- `.agent/hermes_observer.py`
- `.agent/tests/test_hermes_observer.py`
- `.agent/tests/test_live_observability.py`
- `docs/evidence/HERMES_LIVE_OBS_R2.md`

All changed paths retain repository ownership uid/gid `1000:1000`.

No runtime H2 bridge, root Hermes, deployment, Kubernetes, database, or secret access occurred. Tests use deterministic local fake Unix sockets only. No secret, prompt, output, or bridge-body content is published.
