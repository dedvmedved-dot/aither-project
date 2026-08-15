# TASK: HERMES-INTEGRATION-H1-R4-ROOT-BRIDGE-EXECUTOR-ABSTRACTION

## Goal

Finish the executor abstraction so the Aither host supervisor can select `executor=codex` or `executor=hermes`, while preserving fail-closed Git/scope/capability behavior and using the already accepted H2 root-owned systemd socket bridge for Hermes.

This is a **manual Hermes implementation task**. Hermes is already running through the Owner's existing Telegram-connected root profile. Do **not** invoke Hermes again from the code under test.

## Confirmed facts

Treat these as inputs and do not reconfigure them:

- Repository: `dedvmedved-dot/aither-project`
- Branch: `aither-v2`
- Baseline SHA: `8ae6bddb90dfabc5eee6383d3d5765d502b8b714`
- Codex CLI path is currently blocked by account usage quota; do not use Codex to execute this task.
- `aither-codex-runner.timer` is disabled and must remain disabled throughout this task.
- H2 root socket bridge is accepted and exists outside the repository:
  - `/run/aither-hermes/execute.sock`
  - root:codex
  - mode 0660
  - protocol accepts exactly literal `RUN`
  - root executor validates current task/governance before spawning Hermes
- Existing Telegram Hermes Gateway is a root user-systemd unit and must remain active, same profile `/root/.hermes`, no restart/reconfiguration.
- Direct `codex -> hermes -z` is forbidden because it would use `/home/codex/.hermes`, not Owner's root profile.
- Generic sudo for `codex` is forbidden.

## Required implementation

### 1. Executor field validation

Update `.agent/host_task_runner.py` so `executor` is a required task field and must be exactly one of:

- `codex`
- `hermes`

The task validator must fail closed for missing/invalid executor values.

### 2. Executor-neutral dispatch

Preserve the existing Codex argv behavior for `executor=codex`.

Add an executor-neutral dispatcher such as:

- `build_codex_argv()`
- `build_hermes_argv()` or equivalent
- `build_executor_argv(task)`

For `executor=hermes`, **do not call the Hermes binary directly**.

The Hermes path must invoke the accepted H2 root socket bridge using a local, argv-safe helper/wrapper that writes exactly `RUN` to `/run/aither-hermes/execute.sock` and reads only the bridge response.

No shell interpolation. No arbitrary prompt. No arbitrary command. No secret handling.

If a dedicated `.agent/hermes_observer.py` is used, it must be a small client/observer for the socket bridge, not a direct Hermes CLI launcher.

### 3. Hermes bridge observer/client

Create `.agent/hermes_observer.py` if not present.

Requirements:

- connect only to `/run/aither-hermes/execute.sock` by default;
- optional socket path override only through a clearly named test environment variable;
- send exactly `RUN` plus required protocol framing if any;
- do not accept a prompt from caller;
- do not accept an arbitrary command from caller;
- do not invoke `/usr/local/lib/hermes-agent/venv/bin/hermes` directly;
- do not use `shell=True`, `os.system`, `eval`, or `exec`;
- bounded response size;
- hard timeout;
- return non-zero for bridge statuses beginning with `BLOCKED_` or `FAIL`;
- do not publish raw Hermes output/reasoning into live status;
- emit only sanitized lifecycle/result metadata through `runner_live.py` if live updates are used.

### 4. Host runner summary

Extend host-runner summaries so every normal result includes the selected `executor`.

When an execution error occurs after the task has been loaded, preserve task identity and executor in the returned BLOCKED summary instead of replacing them with empty strings.

Do not expose raw command lines, prompts, stdout/stderr, tokens, credentials, or secret values.

### 5. Systemd runner accuracy

Update `.agent/systemd_runner.py` so final live status uses the actual `task_id` and `executor` returned by the host-runner summary.

Do not intentionally publish a stale pre-fetch task id.

For the initial pre-sync poll, task identity may be omitted until synchronized.

Add a specific safe message classification for executor failures where practical; do not expose raw stderr.

### 6. Live schema

Extend `.agent/runner_live.py` sanitized optional scalar schema with at least:

- `executor`
- `repo_state`
- `aither_state`
- `deployed_sha`
- `progress_current`
- `progress_total`

The sanitizer must continue to reject/omit prompt, command, stdout, stderr, token, credential, secret-like, and arbitrary unapproved fields.

### 7. Execution semantics

`execute_task()` or equivalent must dispatch according to the validated executor.

For this implementation task itself, `capabilities.agent_exec=false`, therefore the automated runner MUST NOT execute the current task. Hermes is implementing it manually through the already-running Owner session.

Do not temporarily flip capability values locally to test real agent execution.

Tests must use mocks/fakes/temp UNIX sockets where execution behavior needs coverage.

### 8. Tests

Update/add tests proving at least:

- task without `executor` fails validation;
- invalid executor fails validation;
- `codex` executor is accepted;
- `hermes` executor is accepted;
- exact existing Codex argv behavior remains correct;
- executor dispatcher selects Codex vs Hermes correctly;
- Hermes dispatcher/client never builds a direct Hermes CLI invocation;
- Hermes bridge client sends only fixed `RUN`;
- no arbitrary prompt or command can be supplied through the Hermes path;
- bridge `BLOCKED_*` becomes non-zero/fail-closed;
- timeout becomes non-zero/fail-closed;
- bounded response handling works;
- execution summary includes executor;
- task id/executor are preserved in BLOCKED summary after task load;
- live sanitizer accepts the new safe fields;
- live sanitizer rejects/omits prompt/output/secret-like fields;
- systemd final status uses summary task id/executor rather than stale pre-fetch values;
- existing scope, tamper, rollback, idempotence, clean-worktree and push tests still pass.

## Hard prohibitions

- DO NOT modify `.agent/CURRENT_TASK.json` or `.agent/CURRENT_TASK.md`.
- DO NOT modify application code or manifests.
- DO NOT run Codex.
- DO NOT invoke the H2 bridge with a real `RUN` during this task.
- DO NOT spawn Hermes from tests or implementation.
- DO NOT invoke Telegram.
- DO NOT restart/reconfigure Hermes Gateway.
- DO NOT enable/start `aither-codex-runner.timer`.
- DO NOT change systemd unit files.
- DO NOT run Kubernetes/deployment/database operations.
- DO NOT read or expose secrets.
- DO NOT install packages.
- DO NOT change sudoers.
- DO NOT expand allowed paths.

## Required validation

Run all commands from `CURRENT_TASK.json`:

```bash
python3 -m py_compile .agent/host_task_runner.py .agent/systemd_runner.py .agent/runner_live.py .agent/hermes_observer.py
python3 .agent/tests/test_host_task_runner.py
PYTHONPATH=.agent python3 .agent/tests/test_live_observability.py
PYTHONPATH=.agent python3 .agent/tests/test_hermes_observer.py
git diff --check
```

Also run the repository task-scope validator if present.

All tests must be local/mocked. No real Codex/Hermes execution.

## Commit / push

If and only if all validations pass and changed paths are within the allowlist:

- create exactly one implementation commit;
- commit message: `feat: add governed Hermes root-bridge executor support`;
- push to `aither-v2`.

Do not modify task-control files.

## Required final report

```text
TASK: HERMES-INTEGRATION-H1-R4-ROOT-BRIDGE-EXECUTOR-ABSTRACTION
BASELINE_SHA:
START_HEAD:
WORKTREE_BEFORE:

EXECUTOR_VALIDATION:
CODEX_DISPATCH:
HERMES_DISPATCH:
HERMES_DIRECT_CLI_USED:
HERMES_SOCKET_PATH:
HERMES_PROTOCOL_FIXED_RUN:
ARBITRARY_PROMPT_ACCEPTED:
ARBITRARY_COMMAND_ACCEPTED:
BRIDGE_BLOCKED_FAIL_CLOSED:
BRIDGE_TIMEOUT_FAIL_CLOSED:
RESPONSE_BOUNDED:

SUMMARY_EXECUTOR_FIELD:
BLOCKED_IDENTITY_PRESERVED:
SYSTEMD_FINAL_TASK_ID_FROM_SUMMARY:
SYSTEMD_FINAL_EXECUTOR_FROM_SUMMARY:
LIVE_SCHEMA_SAFE_FIELDS:
LIVE_SCHEMA_SECRET_FIELDS_REJECTED:

PY_COMPILE:
HOST_RUNNER_TESTS:
LIVE_OBSERVABILITY_TESTS:
HERMES_OBSERVER_TESTS:
TASK_SCOPE_VALIDATOR:
GIT_DIFF_CHECK:

CHANGED_PATHS:
OUTSIDE_ALLOWLIST:
CURRENT_TASK_FILES_MODIFIED:
APPLICATION_RUNTIME_MODIFIED:
SYSTEMD_UNIT_FILES_MODIFIED:
CODEX_EXECUTED:
REAL_HERMES_EXECUTED:
TELEGRAM_GATEWAY_RESTARTED:
SECRETS_EXPOSED:

RESULT_COMMIT:
PUSH:
WORKTREE_AFTER:
RESULT: PASS|FAIL|BLOCKED
STOP
```

Return `PASS` only when implementation, tests, scope validation, single commit, push, and clean finish all succeed.

Do not declare Architect acceptance.

STOP.
