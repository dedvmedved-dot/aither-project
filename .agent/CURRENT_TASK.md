# TASK: HERMES-INTEGRATION-H7A-SAFE-RESULT-PUBLICATION

## Goal

Implement the minimum safe feedback channel required for autonomous Aither orchestration:

1. repository changes produced by root Hermes must never be left root-owned in the codex-owned checkout;
2. the codex host runner must publish a fixed machine-readable `.agent/EXECUTION_RESULT.json` to GitHub for governed executed-task outcomes;
3. result publication must not change the task fingerprint or cause the same task to execute again;
4. executor-controlled content must never be able to forge or modify the runner-managed result file.

This is the first task after persistent scheduler activation. The scheduler is already enabled and active. This task must be discovered and executed by the scheduler automatically. Owner/manual service start is forbidden.

## Accepted starting state

- Branch: `aither-v2`.
- Baseline: `e5dea631e01ac73f3ed20cf63194058725c8b5ea`.
- H6 is Architect-accepted: persistent timer is enabled+active and unchanged H6 polls are IDLE.
- Runner service executes as Linux user `codex` in `/home/codex/aither-project`.
- Hermes execution path remains observer -> H2 -> root Hermes with `HOME=/root` and `/root/.hermes`.
- H2 Git governance already runs as `codex`.
- Generic sudo, `safe.directory=*`, repository ownership changes and a second Telegram Gateway remain forbidden.

## Critical source-write identity rule

Root Hermes MAY inspect the repository read-only as root, but MUST NOT create, overwrite, replace, rename, truncate or otherwise write repository files directly as root.

Every repository file write for this task MUST execute as Linux user `codex` using the already proven root-to-codex identity transition (`runuser -u codex -- <argv>` or the exact installed equivalent), with an argv-safe command and **no shell**.

Hard rules:

- no `sudo`;
- no `sh -c`, `bash -c` or equivalent shell wrapper;
- no `chown`/`chmod` repair after a root write;
- no repository ownership changes;
- no Git `safe.directory` changes;
- no direct root write followed by ownership correction;
- if `codex` cannot perform an authorized write, return BLOCKED instead of bypassing this rule.

Before returning PASS, prove every existing changed implementation file is owned by the same uid as the host runner (`codex`).

## Authorized source scope

Only these implementation files may change:

- `.agent/host_task_runner.py`
- `.agent/tests/test_host_task_runner.py`

Do not modify CURRENT_TASK locally. Do not modify systemd units, Hermes observer, H2 root executor, Telegram Gateway, Aither runtime, Kubernetes, database, packages, secrets or sudoers.

## Required implementation

### A. Fixed runner-managed result path

Introduce one fixed runner-managed path:

`.agent/EXECUTION_RESULT.json`

It is host-runner managed, not Architect task-control and not executor implementation scope.

Required governance semantics:

- committed handoff governance may accept this fixed runner-managed path in addition to Architect task-control and task `allowed_paths`;
- the executor itself is forbidden to modify/create/delete the runner-managed result path;
- the result path must not be included in the task fingerprint;
- arbitrary paths under `.agent/` are NOT trusted merely because this path is trusted.

### B. Source ownership enforcement

After executor return and before validation/commit, verify each existing changed implementation path is owned by the effective uid of the host runner process.

Expected production uid is `codex` because `aither-codex-runner.service` runs as `User=codex`.

If any existing changed implementation path is owned by another uid (including root), fail closed and restore to `start_head`.

Do not weaken this by chowning files automatically.

### C. Machine-readable execution result

For a task that reaches executor execution, the host runner must create `.agent/EXECUTION_RESULT.json` itself after executor-controlled changes have been validated/restored as appropriate.

The file must contain only a safe deterministic whitelist of fields sufficient for Architect audit, including at minimum:

- `schema_version`
- `task_id`
- `task_fingerprint`
- `executor`
- `result`
- `start_head`
- `changed_paths`
- `implementation_paths`
- `message`

Do NOT include:

- raw executor stdout/stderr;
- prompts;
- environment variables;
- secret values;
- credentials/tokens;
- arbitrary model text.

The runner, executing as `codex`, writes this file. Root Hermes must not write it.

### D. PASS publication

On a successful executed task:

1. validate executor changes and ownership;
2. write a safe `result=PASS` result file;
3. stage exactly the authorized implementation paths plus the fixed runner-managed result path;
4. make at most one host commit;
5. push fast-forward to the task branch using existing remote-moved protection;
6. store the successful task fingerprint and resulting commit SHA in runner state;
7. leave the worktree clean.

A read-only future task with host `commit=true`, `push=true`, `max_commits=1` must therefore be able to produce a **result-only commit** even when `implementation_paths=[]`.

### E. Controlled BLOCKED publication

If executor execution is attempted and then becomes BLOCKED after task governance/eligibility (for example executor failure or post-executor validation failure), restore executor changes to `start_head` first, then publish a safe `result=BLOCKED` result-only commit when host commit/push capability permits.

After this result commit:

- persist failed fingerprint/result in runner state;
- the next unchanged poll must perform sync+governance and return `SUPPRESSED`;
- it must not invoke executor again;
- result publication failure must not be disguised as PASS.

Pre-task failures where the task cannot be safely loaded/governed are not required to commit a result in this task.

### F. Idempotence after result commit

After a PASS result commit, the next scheduler poll sees a branch HEAD that includes `.agent/EXECUTION_RESULT.json` but the same task fingerprint.

It MUST:

- pass baseline/handoff governance;
- recognize the successful fingerprint;
- return IDLE;
- not invoke Hermes/H2/Codex again;
- not create another result commit.

After a BLOCKED result commit, the analogous next poll must return SUPPRESSED without executor execution or another result commit.

## Required tests

Extend `.agent/tests/test_host_task_runner.py` to cover at minimum:

1. fixed result path accepted by committed handoff governance;
2. unrelated `.agent/*` path still rejected;
3. executor attempt to modify result path rejected;
4. changed implementation file with uid different from runner uid rejected;
5. correctly owned implementation file accepted;
6. successful source-write task commits implementation + result exactly once;
7. successful read-only task can produce a result-only commit;
8. result JSON contains only safe whitelisted data and no raw stdout/stderr/environment;
9. PASS result commit does not alter task fingerprint semantics and next poll is IDLE without executor call;
10. post-executor BLOCKED can publish result-only commit after restore;
11. next unchanged poll after BLOCKED result is SUPPRESSED without executor call;
12. remote-moved protection still fails closed;
13. existing H4 governance-before-IDLE/SUPPRESSED tests remain passing;
14. existing Hermes observer/executor selection behavior remains passing.

Run at least:

`python3 .agent/tests/test_host_task_runner.py`

and existing validation invoked by the host runner.

## Runtime/scheduler constraints

- Do NOT manually start the timer, service, host runner, observer, H2 or Hermes.
- Persistent timer must discover this task automatically.
- Do NOT disable/stop the timer on PASS.
- If an unsafe retry loop, repeated root Hermes execution for the same fingerprint, repository ownership violation, or scheduler failure loop occurs, fail closed and report it. Do not improvise broad privilege changes.
- Telegram Gateway must remain active and unrestarted.

## PASS criteria

PASS only if all are true:

1. task was discovered by the already-running persistent scheduler;
2. root Hermes executed exactly once for the H7A fingerprint;
3. source changes are only the two allowed files;
4. every existing changed implementation file is owned by codex, not root;
5. no direct root repository write or ownership repair was used;
6. tests pass;
7. host runner creates at most one implementation commit and pushes it fast-forward;
8. worktree finishes clean;
9. scheduler remains enabled+active;
10. Telegram Gateway remains unchanged;
11. no Aither/Kubernetes/database/runtime changes;
12. no secrets are printed.

Note: the newly implemented result protocol is not required to publish H7A's own result because the currently running host-runner process was loaded from the pre-H7A implementation. H7B will be the first live validation of autonomous result publication.

## Required final report

```text
TASK: HERMES-INTEGRATION-H7A-SAFE-RESULT-PUBLICATION

DISCOVERED_BY_PERSISTENT_SCHEDULER:
START_HEAD:
REMOTE_HEAD_AT_START:
WORKTREE_BEFORE:
TIMER_ENABLED_BEFORE:
TIMER_ACTIVE_BEFORE:
TELEGRAM_PID_BEFORE:

ROOT_HERMES_EXECUTION_COUNT:
ROOT_HERMES_USER:
ROOT_HERMES_HOME:
ROOT_HERMES_PROFILE:
CODEX_EXECUTION_COUNT:

ROOT_DIRECT_REPO_WRITE_USED: NO
RUNUSER_CODEX_WRITE_USED:
SHELL_WRAPPER_USED: NO
CHOWN_OR_OWNERSHIP_REPAIR_USED: NO
CHANGED_IMPLEMENTATION_PATHS:
CHANGED_FILE_OWNERS:
ALL_CHANGED_FILES_OWNED_BY_CODEX:

RESULT_PATH_IMPLEMENTED:
RESULT_PATH_EXECUTOR_PROTECTED:
OWNERSHIP_GUARD_IMPLEMENTED:
PASS_RESULT_PUBLICATION_IMPLEMENTED:
BLOCKED_RESULT_PUBLICATION_IMPLEMENTED:
RESULT_IDEMPOTENCE_IMPLEMENTED:

HOST_RUNNER_TESTS:
HOST_RUNNER_TEST_COUNT:
VALIDATION_RESULT:

IMPLEMENTATION_COMMIT:
COMMIT_MESSAGE:
PUSH_RESULT:
REMOTE_HEAD_AFTER_PUSH:
WORKTREE_AFTER:

TIMER_ENABLED_FINAL:
TIMER_ACTIVE_FINAL:
TELEGRAM_PID_AFTER:
TELEGRAM_PID_UNCHANGED:
AITHER_RUNTIME_TOUCHED: NO
KUBERNETES_TOUCHED: NO
SECRET_VALUES_PRINTED: NO

RESULT: PASS|FAIL|BLOCKED
STOP
```

Do not declare Architect acceptance. STOP.
