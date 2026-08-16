# TASK: HERMES-INTEGRATION-H4-SYNC-RETRY-GOVERNOR

## Goal

Eliminate the old infinite executor retry loop without sacrificing fast GitHub task delivery.

The current timer polls every ~1 minute. That cadence is useful for discovering a new Architect task, but after a BLOCKED executor result the same task fingerprint can be executed again every timer cycle. That behavior previously caused the Codex quota failure to repeat indefinitely.

Implement a fail-closed retry governor in the supervisor so:

- GitHub fetch/sync still happens on every poll;
- a newly published task fingerprint is eligible to run immediately;
- a task already completed successfully remains IDLE;
- a task that returned BLOCKED/FAIL does NOT automatically re-run every minute;
- the same failed fingerprint is suppressed until explicit Architect change to the task-control fingerprint;
- no timer re-enable occurs in this task.

This is repository implementation only. Do not execute Hermes/Codex from the modified runner during this task.

## Confirmed state

- Branch: `aither-v2`
- Baseline: `ad7d54f41a5543bbf0a0883dc386e55016839f64`
- H1 implementation: Architect accepted.
- H3-R2 E2E canary: PASS at runtime; full path through root Hermes is proven.
- Existing timer remains disabled/inactive.
- Current timer Source of Truth uses `OnUnitInactiveSec=1min`; the timer itself may remain frequent.
- Root H2 bridge and Telegram Gateway must not be changed.

## Required design

### 1. Keep sync independent from execution eligibility

`run_once()` must still:

1. acquire the existing lock;
2. require clean worktree;
3. resolve branch;
4. fast-forward/sync from GitHub;
5. load the synchronized CURRENT_TASK;
6. validate branch/baseline/governance;
7. calculate current task fingerprint;
8. consult runner state to decide whether executor invocation is allowed.

A suppressed task MUST NOT prevent future GitHub sync.

### 2. Persist last execution outcome by task fingerprint

Extend runner state safely so it can distinguish at least:

- last successful fingerprint;
- last attempted fingerprint;
- last attempt result (`PASS`, `BLOCKED`, optionally `FAIL` if used internally);
- last task id;
- last executor;
- last commit SHA when applicable.

Do not store raw prompts, stdout, stderr, secrets, tokens, reasoning, or arbitrary executor output.

### 3. Suppress repeated execution of the same failed fingerprint

If the synchronized task fingerprint equals the last attempted fingerprint and the last attempt result was `BLOCKED` or `FAIL`:

- DO NOT invoke Codex;
- DO NOT invoke Hermes observer/H2;
- return a safe non-error supervisor summary indicating execution is suppressed pending Architect task change;
- preserve task_id and executor;
- keep repository synced;
- do not mutate source/task files.

Use a distinct result/state such as `SUPPRESSED` or equivalent safe classification. Do not overload `PASS` in a way that hides the reason.

Systemd service should exit successfully for this suppression state so the timer can continue polling GitHub without entering a failed-service loop.

### 4. New fingerprint unlocks execution immediately

If Architect changes either CURRENT_TASK.json or CURRENT_TASK.md so the task fingerprint changes:

- suppression from the previous fingerprint must not block the new task;
- the new synchronized task is eligible immediately, subject to normal governance/capability checks.

This is the core task-delivery requirement.

### 5. Successful fingerprint remains idempotent

Existing behavior for a successful fingerprint should remain logically equivalent to `IDLE`:

- do not re-run executor;
- keep polling/sync operational;
- return task_id/executor safely.

### 6. Failure state must be recorded before returning BLOCKED

Currently a BLOCKED result can be returned without durable state that suppresses the next timer poll.

Update the flow so after a task has been synchronized, validated and an executor attempt actually occurs, a resulting BLOCKED/FAIL outcome records the attempted fingerprint/result in runner state before returning the summary.

Do not record a fingerprint as "attempted" when no executor invocation happened due to pre-execution governance failures that require Architect intervention before task execution eligibility is established, unless the implementation has a precise safe classification and tests prove the semantics. Prefer conservative behavior and document the distinction.

### 7. Safe summaries and live observability

Extend only safe scalar status as needed, e.g.:

- `retry_state`
- `suppressed`
- `last_attempt_result`

If adding fields, update `runner_live.py` whitelist and tests.

Never publish raw exception text to remote live state beyond existing safe message classification.

`systemd_runner.py` must map suppression to a non-failed observable state such as:

- state=`IDLE` or `WAITING`
- phase=`EXECUTOR_RETRY_SUPPRESSED`
- runner_result=`SUPPRESSED`

Use whichever exact names are simplest, but tests must make semantics unambiguous.

### 8. Do not change the timer cadence in this task

Do not modify:

- `.agent/systemd/aither-codex-runner.timer`
- installed timer unit
- timer enablement state

The point is to preserve frequent GitHub polling while preventing repeated executor invocation.

## Mandatory tests

Add/adjust tests proving at least:

1. First unseen task fingerprint is eligible for execution.
2. PASS fingerprint becomes IDLE on next poll and executor is not called.
3. BLOCKED executor attempt records the fingerprint/result.
4. Same BLOCKED fingerprint on next poll returns SUPPRESSED and executor is not called.
5. Repeated SUPPRESSED polls still perform fetch/sync.
6. A new Architect task fingerprint immediately clears the suppression and is eligible for execution.
7. Suppression preserves `task_id` and `executor` in summary.
8. `SUPPRESSED` is treated as successful service/poll outcome by CLI/systemd wrapper, not a failed service.
9. Live status publishes only allowed safe fields and identifies retry suppression without raw stderr/stdout.
10. Existing Codex/Hermes dispatcher behavior remains unchanged.
11. Existing task governance, scope validation, rollback, clean-worktree, and success-idempotence tests still pass.
12. No agent execution occurs when `agent_exec=false` for this implementation task.

## Hard prohibitions

DO NOT:

- modify `.agent/CURRENT_TASK.json` or `.agent/CURRENT_TASK.md` locally;
- modify timer files or installed timer state;
- enable/start recurring timer;
- run Codex;
- invoke real H2 RUN;
- spawn Hermes recursively;
- change root executor;
- restart/reconfigure Telegram Gateway;
- touch Aither runtime/Kubernetes/database;
- read/expose secrets;
- install packages;
- modify sudoers;
- modify paths outside CURRENT_TASK.json allowed_paths.

## Validation

Run every validation command in CURRENT_TASK.json.

All must PASS, including scope validator and diff check.

## Commit / push

If and only if all validations pass:

- exactly one implementation commit;
- commit message exactly: `feat: add sync-preserving executor retry governor`;
- push fast-forward to `aither-v2`;
- clean worktree after push.

## Required final report

```text
TASK: HERMES-INTEGRATION-H4-SYNC-RETRY-GOVERNOR
BASELINE_SHA:
START_HEAD:
WORKTREE_BEFORE:

SYNC_BEFORE_ELIGIBILITY: PASS|FAIL
STATE_LAST_ATTEMPT_FINGERPRINT_ADDED:
STATE_LAST_ATTEMPT_RESULT_ADDED:
BLOCKED_FINGERPRINT_RECORDED:
SAME_BLOCKED_FINGERPRINT_SUPPRESSED:
SUPPRESSED_EXECUTOR_NOT_CALLED:
SUPPRESSED_STILL_FETCHES:
NEW_FINGERPRINT_UNLOCKS_EXECUTION:
SUCCESS_IDEMPOTENCE_PRESERVED:
TASK_ID_EXECUTOR_PRESERVED:
SYSTEMD_SUPPRESSED_NONFAILED:
LIVE_SUPPRESSION_SAFE:

CODEX_DISPATCH_UNCHANGED:
HERMES_DISPATCH_UNCHANGED:
REAL_CODEX_EXECUTED: NO
REAL_H2_RUN_INVOKED: NO
REAL_HERMES_EXECUTED: NO

PY_COMPILE:
HOST_RUNNER_TESTS:
LIVE_OBSERVABILITY_TESTS:
TASK_SCOPE_VALIDATOR:
GIT_DIFF_CHECK:

CHANGED_PATHS:
OUTSIDE_ALLOWLIST:
CURRENT_TASK_FILES_MODIFIED: NO
TIMER_FILES_MODIFIED: NO
TIMER_ENABLED: disabled
TIMER_ACTIVE: inactive
ROOT_EXECUTOR_MODIFIED: NO
TELEGRAM_GATEWAY_RESTARTED: NO
AITHER_RUNTIME_MODIFIED: NO
KUBERNETES_TOUCHED: NO
SECRETS_EXPOSED: NO

RESULT_COMMIT:
PUSH:
REMOTE_HEAD:
WORKTREE_AFTER:
RESULT: PASS|FAIL|BLOCKED
STOP
```

PASS only if all required tests/validations pass and exactly one allowed implementation commit is pushed.

Do not declare Architect acceptance.

STOP.
