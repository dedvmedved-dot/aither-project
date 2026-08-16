# TASK: HERMES-INTEGRATION-H7A-R1-OWNERSHIP-FAIL-CLOSED

## Goal

Correct one Architect-found safety defect in H7A before accepting the result-publication layer.

H7A implementation commit `859b75e03fc0e0a28056f5948d88e313afd279a2` added `verify_source_ownership()`, but it currently calls `Path.stat()` and silently skips **all** `OSError` conditions. That is not fail-closed: a broken symlink or another stat failure can bypass the ownership gate.

Implement the narrow correction only. The persistent scheduler must discover and execute this task automatically.

## Starting state

- Branch: `aither-v2`.
- Baseline: `859b75e03fc0e0a28056f5948d88e313afd279a2`.
- Persistent scheduler is expected enabled+active from H6.
- H7A result protocol now exists in source and should publish this task's result automatically.
- Root Hermes path remains observer -> H2 -> root Hermes `/root/.hermes`.
- Repository writes by root Hermes must be performed as Linux user `codex`; no direct root repo write is authorized.

## Authorized files

Only:

- `.agent/host_task_runner.py`
- `.agent/tests/test_host_task_runner.py`

Do not modify task-control locally. Do not modify `.agent/EXECUTION_RESULT.json` directly; it is runner-managed and must be written only by the host runner after executor validation.

## Required correction

Change source ownership verification so that it is genuinely fail-closed for every existing changed implementation path.

Required semantics:

1. Use `lstat()` semantics (or an exactly equivalent non-following ownership check) so symlink ownership is checked without following the target.
2. A path that is truly absent because the executor deleted it may be skipped only on `FileNotFoundError`.
3. A broken symlink is an existing filesystem object and MUST NOT be skipped. Its own uid must be checked.
4. Any other `OSError`/permission/stat failure MUST raise `RunnerError`; do not silently continue.
5. If uid differs from host runner effective uid, raise `RunnerError`.
6. Do not chown/chmod/repair ownership automatically.
7. Preserve all existing H7A result-publication, idempotence, retry suppression, remote-moved and executor-selection behavior.

## Required tests

Add/adjust tests proving at minimum:

- regular changed file with wrong uid is rejected;
- regular changed file with runner uid is accepted;
- truly absent/deleted path (`FileNotFoundError`) is allowed to be skipped;
- broken symlink is checked via non-following metadata and is not treated as missing;
- non-`FileNotFoundError` metadata failure fails closed with `RunnerError`;
- result-path handoff governance remains accepted;
- unrelated `.agent/*` remains rejected;
- result-path executor tamper remains rejected;
- PASS implementation+result commit still works once;
- PASS next poll remains IDLE without executor reinvocation;
- BLOCKED result publication and next-poll SUPPRESSED remain working;
- remote-moved protection still fails closed.

Run:

`python3 .agent/tests/test_host_task_runner.py`

## Source-write identity

For this corrective task itself:

- root Hermes MUST NOT directly write repository files as root;
- authorized file writes must run as Linux user `codex` through argv-safe `runuser -u codex -- <argv>` or the already installed exact equivalent;
- no `sudo`;
- no `sh -c` / `bash -c`;
- no chown repair;
- no safe.directory changes;
- no repository ownership changes.

The currently installed H7A runner ownership guard must observe the changed regular implementation files as owned by `codex` before it accepts the task.

## Expected autonomous result publication

Because H7A result publication is now installed, a successful H7A-R1 execution must cause the host runner to create and commit `.agent/EXECUTION_RESULT.json` automatically in the **same single host commit** as the two authorized implementation changes.

Expected result file semantics:

- `task_id` = this H7A-R1 task;
- `executor=hermes`;
- `result=PASS`;
- task fingerprint matches CURRENT_TASK JSON+MD;
- implementation paths contain only the changed authorized implementation files;
- no raw stdout/stderr/env/prompt/secrets.

Next unchanged scheduler poll must be `IDLE` and must not invoke Hermes/H2 again.

## Hard prohibitions

DO NOT:

- manually start timer/service/runner/observer/H2/Hermes;
- disable persistent scheduler on PASS;
- invoke Codex;
- modify Aither runtime/Kubernetes/database/deployment;
- modify Telegram Gateway;
- expose secrets;
- broaden scope beyond the ownership fail-closed correction and its tests.

## PASS criteria

PASS only if:

1. persistent scheduler autonomously discovers this task;
2. root Hermes executes once for this fingerprint;
3. only the two authorized implementation files are changed by executor;
4. changed implementation files are owned by codex and current ownership guard accepts them;
5. corrected ownership code uses non-following metadata and fails closed except for a genuinely absent/deleted path;
6. required tests pass;
7. host runner automatically creates `.agent/EXECUTION_RESULT.json`;
8. exactly one host commit contains implementation + result;
9. push is fast-forward and worktree finishes clean;
10. next same-fingerprint poll is IDLE without repeated executor;
11. scheduler remains enabled+active;
12. Telegram Gateway remains unchanged;
13. no Aither/Kubernetes/runtime/database mutation;
14. no secret values printed.

## Required final report

```text
TASK: HERMES-INTEGRATION-H7A-R1-OWNERSHIP-FAIL-CLOSED
AUTONOMOUS_PICKUP:
START_HEAD:
ROOT_HERMES_EXECUTION_COUNT:
ROOT_DIRECT_REPO_WRITE_USED: NO
RUNUSER_CODEX_WRITE_USED:
SHELL_WRAPPER_USED: NO
CHOWN_OR_OWNERSHIP_REPAIR_USED: NO
CHANGED_IMPLEMENTATION_PATHS:
CHANGED_FILE_OWNERS:
ALL_CHANGED_FILES_OWNED_BY_CODEX:
LSTAT_OR_EQUIVALENT_USED:
ONLY_FILENOTFOUND_SKIPPED:
OTHER_OSERROR_FAILS_CLOSED:
BROKEN_SYMLINK_TEST:
HOST_RUNNER_TESTS:
HOST_RUNNER_TEST_COUNT:
RESULT_FILE_AUTOPUBLISHED:
RESULT_FILE_TASK_ID:
RESULT_FILE_RESULT:
RESULT_FILE_SAFE_WHITELIST:
IMPLEMENTATION_COMMIT:
COMMIT_MESSAGE:
PUSH_RESULT:
NEXT_POLL_RESULT:
NEXT_POLL_EXECUTOR_REINVOKED:
TIMER_ENABLED_FINAL:
TIMER_ACTIVE_FINAL:
TELEGRAM_PID_UNCHANGED:
AITHER_RUNTIME_TOUCHED: NO
KUBERNETES_TOUCHED: NO
SECRET_VALUES_PRINTED: NO
RESULT: PASS|FAIL|BLOCKED
STOP
```

Do not declare Architect acceptance. STOP.
