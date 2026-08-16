# TASK: HERMES-INTEGRATION-H5A-SCHEDULER-SUPPRESSION-CANARY

## Goal

Validate the retry governor in the real systemd scheduler path without invoking any AI executor.

This canary must prove that:

1. the scheduler can poll GitHub through the installed timer/service path;
2. the first poll of this new task reaches the host runner and is blocked by `agent_exec=false` before any Hermes/Codex execution;
3. that failed attempt is persisted by task fingerprint;
4. the next scheduler poll of the same unchanged task returns `SUPPRESSED` with exit 0 and does not invoke the executor again;
5. GitHub sync/polling remains active between attempts;
6. the timer is returned to disabled/inactive after the test.

This is a runtime scheduler canary only. No repository implementation changes are authorized.

## Confirmed state

- Branch: `aither-v2`
- Baseline: `cb5b9de8dd6dc8d765c7ec5b187048a80c9c9bf9`
- H4 retry governor and H4-R1 governance ordering are Architect-accepted at repository level.
- Existing timer Source of Truth remains frequent (`OnUnitInactiveSec=1min`).
- Existing Telegram Hermes Gateway must remain active and unrestarted.
- H2 root bridge must not be invoked in this task.
- Codex must not be invoked.
- This task has `agent_exec=false` intentionally.

## Required runtime sequence

### Preconditions

Record before changes:

- local/remote HEAD;
- clean worktree;
- current task id/executor;
- timer enabled/active state;
- runner service state;
- host-runner/hermes-observer processes absent;
- H2 socket present;
- Telegram Gateway active/MainPID;
- current runner state file contents limited to safe scalar fields only.

If worktree is not clean or branch/task identity is wrong: BLOCKED and STOP.

### Scheduler canary

1. Ensure local checkout is fast-forward synced to current GitHub task-control HEAD.
2. Keep timer **disabled** persistently. Do NOT `enable` it.
3. Start the existing timer transiently with `systemctl start aither-codex-runner.timer`.
4. Observe the first service execution caused by the timer.
5. The first execution must:
   - sync GitHub;
   - load this task;
   - pass branch/baseline/handoff governance;
   - see `agent_exec=false`;
   - return `BLOCKED`;
   - record `last_attempt_fingerprint=<current fingerprint>` and `last_attempt_result=BLOCKED`;
   - NOT invoke Hermes observer, H2, root Hermes, or Codex.
6. Leave the timer active only long enough for one subsequent scheduled poll of the same unchanged task.
7. The second execution must:
   - sync GitHub again;
   - pass governance;
   - identify the same failed fingerprint;
   - return `SUPPRESSED`;
   - service exit status 0;
   - publish live state `WAITING / EXECUTOR_RETRY_SUPPRESSED`;
   - NOT invoke any executor.
8. As soon as the second poll is proven, stop the timer with `systemctl stop aither-codex-runner.timer`.
9. Confirm timer remains disabled and is now inactive.

Exactly two scheduler service executions are authorized for this task: first BLOCKED, second SUPPRESSED. Do not allow a third execution.

## Hard prohibitions

DO NOT:

- enable the timer persistently;
- allow more than two scheduler service executions;
- invoke Hermes manually;
- invoke H2 RUN;
- invoke Codex;
- modify root executor;
- modify repository files;
- modify task-control locally;
- commit or push implementation changes;
- modify timer/service unit files;
- restart/reconfigure Telegram Gateway;
- touch Aither runtime/Kubernetes/database;
- read/expose secrets;
- install packages or modify sudoers.

## PASS criteria

PASS only if all are true:

1. Timer was disabled before and remains disabled after.
2. Exactly two scheduler service executions occurred.
3. First result is BLOCKED due to `agent_exec=false` after governance.
4. First result records failed fingerprint/result in runner state.
5. No executor was invoked on first poll.
6. Second poll performs GitHub fetch/sync again.
7. Second result is SUPPRESSED for the same fingerprint.
8. Second service exits successfully (0).
9. Live state is WAITING / EXECUTOR_RETRY_SUPPRESSED with task_id/executor preserved and no unsafe fields.
10. No Hermes observer/H2/root Hermes/Codex execution occurs across both polls.
11. Repository HEAD/worktree unchanged except fast-forward of Architect task-control commits.
12. No implementation commit/push occurs.
13. Telegram Gateway remains active with unchanged MainPID and no second gateway process.
14. Timer is stopped immediately after second proven poll and ends inactive.

## Required final report

```text
TASK: HERMES-INTEGRATION-H5A-SCHEDULER-SUPPRESSION-CANARY

LOCAL_HEAD_BEFORE:
REMOTE_HEAD_BEFORE:
WORKTREE_CLEAN_BEFORE:
CURRENT_TASK:
CURRENT_EXECUTOR:
AGENT_EXEC:

TIMER_ENABLED_BEFORE:
TIMER_ACTIVE_BEFORE:
RUNNER_SERVICE_STATE_BEFORE:
TELEGRAM_GATEWAY_MAIN_PID_BEFORE:
H2_SOCKET_EXISTS:

TIMER_STARTED_TRANSIENTLY:
SERVICE_EXECUTION_COUNT:

FIRST_POLL_RESULT:
FIRST_POLL_TASK_ID:
FIRST_POLL_EXECUTOR:
FIRST_POLL_BLOCK_REASON:
FIRST_POLL_STATE_FINGERPRINT_RECORDED:
FIRST_POLL_STATE_RESULT_RECORDED:
FIRST_POLL_HERMES_OBSERVER_COUNT:
FIRST_POLL_H2_RUN_COUNT:
FIRST_POLL_ROOT_HERMES_COUNT:
FIRST_POLL_CODEX_COUNT:

SECOND_POLL_SYNC_OCCURRED:
SECOND_POLL_RESULT:
SECOND_POLL_TASK_ID:
SECOND_POLL_EXECUTOR:
SECOND_POLL_SERVICE_EXIT:
SECOND_POLL_LIVE_STATE:
SECOND_POLL_LIVE_PHASE:
SECOND_POLL_UNSAFE_FIELDS_PRESENT:
SECOND_POLL_HERMES_OBSERVER_COUNT:
SECOND_POLL_H2_RUN_COUNT:
SECOND_POLL_ROOT_HERMES_COUNT:
SECOND_POLL_CODEX_COUNT:

TIMER_STOPPED_AFTER_SECOND_POLL:
TIMER_ENABLED_AFTER:
TIMER_ACTIVE_AFTER:
LOCAL_HEAD_AFTER:
REMOTE_HEAD_AFTER:
WORKTREE_CLEAN_AFTER:
REPOSITORY_FILES_MODIFIED:
NEW_IMPLEMENTATION_COMMIT:
IMPLEMENTATION_PUSH:

TELEGRAM_GATEWAY_ACTIVE_AFTER:
TELEGRAM_GATEWAY_MAIN_PID_AFTER:
TELEGRAM_GATEWAY_RESTARTED:
SECOND_TELEGRAM_PROCESS:
AITHER_RUNTIME_TOUCHED: NO
KUBERNETES_TOUCHED: NO
SECRETS_EXPOSED: NO

RESULT: PASS|FAIL|BLOCKED
STOP
```

Do not declare Architect acceptance.

STOP.
