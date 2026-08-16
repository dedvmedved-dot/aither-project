# TASK: HERMES-INTEGRATION-H6-PERSISTENT-SCHEDULER-ACTIVATION

## Goal

Activate the existing governed scheduler persistently after H5A/H5B proved both failure suppression and success idempotence in the real timer path.

Target operating state:

`GitHub CURRENT_TASK -> enabled+active systemd timer -> aither-codex-runner.service -> systemd_runner.py -> host_task_runner.py -> governed executor selection -> Hermes main path / Codex optional -> live status`.

This task is the production activation gate for the scheduler. No source implementation changes are authorized.

## Confirmed accepted prerequisites

- Branch: `aither-v2`.
- Baseline before this task: `8ab4c077a0afbe21d904f18ee83be3b51e3d7416`.
- H3-R2: full supervisor -> observer -> H2 -> root Hermes E2E PASS.
- H4/H4-R1: retry governor and governance-before-eligibility accepted.
- H5A: real timer path proved BLOCKED -> SUPPRESSED, continued GitHub sync, no repeated executor.
- H5B: real timer path proved PASS -> IDLE with exactly one root Hermes execution.
- Existing timer Source of Truth remains `OnActiveSec=15s`, `OnUnitInactiveSec=1min`.
- Existing Telegram Gateway must remain active and unrestarted.
- H2 root bridge must remain unchanged.
- Codex must not execute in this activation task.

## Root Hermes activation-canary semantics

On the first scheduler poll after persistent activation, root Hermes must perform only a read-only canary:

1. Read `AGENTS.md`, `.agent/CURRENT_TASK.json`, `.agent/CURRENT_TASK.md`.
2. Verify task id `HERMES-INTEGRATION-H6-PERSISTENT-SCHEDULER-ACTIVATION`.
3. Verify `executor=hermes`, `agent_exec=true`, `source_write=false`.
4. Read-only inspect branch, HEAD, clean worktree.
5. Do not modify source/task-control/runtime/Kubernetes/database/deployment/packages/secrets.
6. Return concise PASS and STOP.

## Preconditions

Before activation record:

- local and remote HEAD;
- clean worktree;
- task id/executor/capabilities;
- timer enabled and active state;
- runner service state;
- host-runner/hermes-observer process absence;
- H2 socket owner/group/mode;
- Telegram Gateway active/MainPID;
- root executor/Hermes identity continuity sufficient to prove root Hermes remains root with `HOME=/root` and existing `/root/.hermes`, without reading secrets.

Expected precondition: timer `disabled` and `inactive`.

If repository is dirty, task identity is wrong, H2 socket is unhealthy, or Telegram Gateway is not healthy: do not activate scheduler; return BLOCKED and STOP.

## Activation sequence

1. Fast-forward sync `/home/codex/aither-project` to the current GitHub task-control HEAD.
2. Reconfirm all preconditions.
3. Persistently activate the timer using the existing installed unit, equivalent to:
   `systemctl enable --now aither-codex-runner.timer`
4. Do NOT manually start the service/host-runner/observer/H2/Hermes.
5. Observe scheduler-triggered execution only.

### First post-enable poll

The first poll of this new H6 fingerprint must:

- sync GitHub;
- pass branch/baseline/handoff governance;
- select `executor=hermes`;
- invoke Hermes observer exactly once;
- invoke H2 exactly once;
- run H2 Git governance as `codex` and PASS;
- invoke root Hermes exactly once as root with `HOME=/root`, existing `/root/.hermes` profile;
- invoke no Codex;
- return executor PASS;
- return host-runner PASS;
- publish live PASS / HOST_RUNNER_COMPLETE;
- record successful H6 fingerprint.

### Second post-enable poll

The next poll of the unchanged H6 task must:

- sync GitHub again;
- pass governance again;
- return `IDLE` with service exit 0;
- publish live `IDLE / HOST_RUNNER_IDLE`;
- not invoke Hermes observer, H2, root Hermes, or Codex again.

### Persistent-state verification

After the second proven poll, DO NOT stop the timer.

Verify:

- timer is `enabled`;
- timer is `active (waiting)` or equivalent active scheduler state;
- next trigger is scheduled;
- runner service is not stuck active/failed;
- no host-runner/hermes-observer/root-Hermes task process remains after completion;
- Telegram Gateway remains active with unchanged MainPID;
- repository remains clean and HEAD matches remote;
- no implementation commit/push occurred.

It is acceptable for additional same-fingerprint polls to occur while evidence is being collected. Every such additional poll MUST be `IDLE` and MUST NOT invoke Hermes observer/H2/root Hermes/Codex. Record the observed total service poll count and confirm root Hermes total remains exactly 1 for H6.

## Rollback trigger

If any post-enable scheduler execution produces:

- `BLOCKED` or `FAIL` unexpectedly;
- a second Hermes observer/H2/root Hermes execution for the same H6 fingerprint;
- Codex execution;
- repository/runtime mutation;
- Telegram Gateway disruption;
- service stuck/failure loop;

then immediately run the equivalent of:

`systemctl disable --now aither-codex-runner.timer`

Capture evidence, report FAIL/BLOCKED, and STOP. Do not retry executor manually.

## Hard prohibitions

DO NOT:

- modify repository source or task-control locally;
- modify timer/service unit files;
- modify root executor;
- manually start the runner service;
- manually invoke host runner;
- manually invoke Hermes observer;
- manually send H2 RUN;
- directly invoke Hermes;
- invoke Codex;
- restart/reconfigure Telegram Gateway;
- touch Aither application runtime/Kubernetes/database/deployment;
- read/expose secrets;
- install packages;
- modify sudoers.

## PASS criteria

PASS only if all are true:

1. Scheduler activation uses the existing timer without unit/source changes.
2. Timer transitions from disabled/inactive to enabled/active.
3. First H6 scheduler poll is PASS with exactly one root Hermes execution through observer/H2.
4. H2 Git governance runs as codex and passes.
5. Root Hermes uses root, `HOME=/root`, existing `/root/.hermes`.
6. Codex count is zero.
7. H6 successful fingerprint is recorded.
8. Second poll is IDLE with exit 0 and zero executor execution.
9. Any additional observed same-fingerprint polls are also IDLE with zero executor execution.
10. Timer remains enabled and active after verification; it is NOT stopped on success.
11. Runner service is healthy/not stuck after each completed poll.
12. Telegram Gateway stays active with unchanged MainPID and no second gateway.
13. Repository HEAD/worktree unchanged except Architect task-control fast-forward.
14. No implementation commit/push.
15. No Aither/Kubernetes/runtime/database mutation.
16. No secrets exposed.

## Required final report

```text
TASK: HERMES-INTEGRATION-H6-PERSISTENT-SCHEDULER-ACTIVATION

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

TIMER_ENABLE_NOW_EXECUTED:
TIMER_ENABLED_AFTER_ENABLE:
TIMER_ACTIVE_AFTER_ENABLE:

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

OBSERVED_SERVICE_POLL_COUNT:
ADDITIONAL_POLLS_ALL_IDLE:
TOTAL_HERMES_OBSERVER_COUNT_FOR_H6:
TOTAL_H2_RUN_COUNT_FOR_H6:
TOTAL_ROOT_HERMES_COUNT_FOR_H6:
TOTAL_CODEX_COUNT_FOR_H6:

TIMER_ENABLED_FINAL:
TIMER_ACTIVE_FINAL:
TIMER_NEXT_TRIGGER_PRESENT:
RUNNER_SERVICE_STATE_FINAL:
HOST_RUNNER_PROCESS_FINAL:
HERMES_OBSERVER_PROCESS_FINAL:
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

ROLLBACK_EXECUTED: YES|NO
RESULT: PASS|FAIL|BLOCKED
STOP
```

On PASS, leave the scheduler enabled and active. Do not declare Architect acceptance.

STOP.
