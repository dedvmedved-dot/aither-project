# TASK: HERMES-INTEGRATION-H5B-SCHEDULER-HERMES-IDEMPOTENCE-CANARY

## Goal

Validate the complete real scheduler path to root Hermes and prove success idempotence under the existing timer/service path.

The required path is:

`systemd timer -> aither-codex-runner.service -> systemd_runner.py -> host_task_runner.py -> executor=hermes -> hermes_observer.py -> H2 root bridge -> Git governance as codex -> root Hermes (/root/.hermes) -> PASS -> next poll IDLE without a second Hermes execution`.

This is a runtime-only read-only canary. No repository implementation changes are authorized.

## Confirmed state

- Branch: `aither-v2`
- Baseline: `5feeaf41bebdf6f734bc2f14330a45f1e41da2a2`
- H3-R2 proved manual supervisor -> H2 -> root Hermes E2E PASS.
- H4/H4-R1 retry governor and governance ordering are Architect-accepted.
- H5A proved real timer retry suppression: BLOCKED -> SUPPRESSED with continued sync and no AI execution.
- Timer must remain persistently disabled; only transient `systemctl start` is allowed for this canary.
- Existing Telegram Gateway must remain active and unrestarted.
- Codex must not execute.

## Root Hermes task semantics

When invoked through H2, root Hermes must perform only this read-only canary:

1. Read `AGENTS.md`, `.agent/CURRENT_TASK.json`, `.agent/CURRENT_TASK.md`.
2. Verify task id is `HERMES-INTEGRATION-H5B-SCHEDULER-HERMES-IDEMPOTENCE-CANARY`.
3. Verify `executor=hermes`, `agent_exec=true`, `source_write=false`.
4. Read-only inspect branch, HEAD and clean worktree.
5. Do not modify any file.
6. Do not touch Aither runtime, Kubernetes, database, deployment, packages or secrets.
7. Return concise PASS and STOP.

## Preconditions

Before transiently starting the timer, record:

- local/remote HEAD and clean worktree;
- current task identity/executor/capabilities;
- timer enabled/active state;
- runner service state;
- host-runner/hermes-observer absence;
- H2 socket owner/group/mode;
- Telegram Gateway active/MainPID;
- H2/root-executor state sufficient to prove root Hermes will use root identity and `/root/.hermes`, without reading secrets.

If any precondition fails: BLOCKED and STOP.

## Required scheduler sequence

1. Fast-forward sync local checkout to current GitHub task-control HEAD.
2. Keep timer persistently **disabled**. Do not enable it.
3. Start timer transiently with `systemctl start aither-codex-runner.timer`.
4. Observe the first scheduler-triggered service execution.
5. First poll must:
   - sync GitHub;
   - load this task;
   - pass branch/baseline/handoff governance;
   - select `executor=hermes`;
   - invoke `hermes_observer.py` exactly once;
   - send fixed H2 `RUN` exactly once;
   - pass H2 Git governance as `codex`;
   - invoke root Hermes exactly once as `root`, `HOME=/root`, using existing `/root/.hermes` profile;
   - return executor canary PASS;
   - produce host-runner PASS and live PASS;
   - record successful fingerprint in runner state;
   - not invoke Codex.
6. Leave timer active only long enough for exactly one subsequent scheduled poll of the same unchanged task.
7. Second poll must:
   - sync GitHub again;
   - pass governance again;
   - identify the same successful fingerprint;
   - return `IDLE`;
   - service exit 0;
   - NOT invoke Hermes observer, H2, root Hermes or Codex a second time;
   - publish safe live IDLE state with task_id/executor preserved.
8. Immediately after the second proven poll, stop timer with `systemctl stop aither-codex-runner.timer`.
9. Confirm timer remains disabled and inactive.

Exactly two scheduler service executions are authorized: first PASS with one root Hermes execution, second IDLE with zero executor execution.

## Hard prohibitions

DO NOT:

- persistently enable the timer;
- allow a third scheduler service execution;
- manually start `aither-codex-runner.service`;
- invoke host runner manually;
- invoke Hermes observer manually;
- send H2 RUN manually;
- invoke Hermes directly;
- invoke Codex;
- modify source/task-control locally;
- commit or push implementation changes;
- modify timer/service unit files;
- modify root executor;
- restart/reconfigure Telegram Gateway;
- touch Aither runtime/Kubernetes/database/deployment;
- read/expose secrets;
- install packages or modify sudoers.

If first poll returns BLOCKED/FAIL, stop timer immediately; do not wait for or allow a retry poll. Capture evidence and STOP.

## PASS criteria

PASS only if all are true:

1. Timer disabled before and after, transiently active only for the canary.
2. Exactly two scheduler service executions occur.
3. First poll selects Hermes and reaches root Hermes exactly once through observer/H2.
4. H2 Git governance runs as `codex` and passes.
5. Root Hermes runs as `root`, HOME `/root`, existing `/root/.hermes` identity/profile.
6. First poll executor, host-runner and live state are PASS.
7. Successful fingerprint is recorded.
8. Second poll performs GitHub sync/governance but returns IDLE for same successful fingerprint.
9. Second poll does not invoke observer/H2/root Hermes/Codex.
10. Second service exit is 0 and live state identifies IDLE safely.
11. Telegram Gateway stays active with unchanged MainPID and no second gateway.
12. Repository HEAD/worktree unchanged except Architect task-control fast-forward.
13. No implementation commit/push.
14. No Aither/Kubernetes/runtime/database mutation.
15. Timer is stopped immediately after second poll and ends inactive.

## Required final report

```text
TASK: HERMES-INTEGRATION-H5B-SCHEDULER-HERMES-IDEMPOTENCE-CANARY

LOCAL_HEAD_BEFORE:
REMOTE_HEAD_BEFORE:
WORKTREE_CLEAN_BEFORE:
CURRENT_TASK:
CURRENT_EXECUTOR:
AGENT_EXEC:
SOURCE_WRITE:

TIMER_ENABLED_BEFORE:
TIMER_ACTIVE_BEFORE:
RUNNER_SERVICE_STATE_BEFORE:
HOST_RUNNER_PROCESS_BEFORE:
HERMES_OBSERVER_PROCESS_BEFORE:
H2_SOCKET_OWNER_GROUP_MODE:
TELEGRAM_GATEWAY_ACTIVE_BEFORE:
TELEGRAM_GATEWAY_MAIN_PID_BEFORE:

TIMER_STARTED_TRANSIENTLY:
SERVICE_EXECUTION_COUNT:

FIRST_POLL_SYNC_OCCURRED:
FIRST_POLL_RESULT:
FIRST_POLL_TASK_ID:
FIRST_POLL_EXECUTOR:
FIRST_POLL_HERMES_OBSERVER_COUNT:
FIRST_POLL_H2_RUN_COUNT:
FIRST_POLL_H2_GOVERNANCE_IDENTITY:
FIRST_POLL_H2_GOVERNANCE_RESULT:
FIRST_POLL_ROOT_HERMES_COUNT:
FIRST_POLL_ROOT_HERMES_USER:
FIRST_POLL_ROOT_HERMES_HOME:
FIRST_POLL_ROOT_PROFILE_USED:
FIRST_POLL_CODEX_COUNT:
FIRST_POLL_EXECUTOR_CANARY_RESULT:
FIRST_POLL_HOST_RUNNER_RESULT:
FIRST_POLL_LIVE_STATE:
FIRST_POLL_LIVE_PHASE:
FIRST_POLL_SUCCESS_FINGERPRINT_RECORDED:

SECOND_POLL_SYNC_OCCURRED:
SECOND_POLL_RESULT:
SECOND_POLL_TASK_ID:
SECOND_POLL_EXECUTOR:
SECOND_POLL_SERVICE_EXIT:
SECOND_POLL_LIVE_STATE:
SECOND_POLL_LIVE_PHASE:
SECOND_POLL_HERMES_OBSERVER_COUNT:
SECOND_POLL_H2_RUN_COUNT:
SECOND_POLL_ROOT_HERMES_COUNT:
SECOND_POLL_CODEX_COUNT:
SECOND_POLL_UNSAFE_FIELDS_PRESENT:

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
