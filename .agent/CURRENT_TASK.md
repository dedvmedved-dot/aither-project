# TASK: HERMES-INTEGRATION-H3-E2E-READONLY-CANARY

## Goal

Prove the complete automated Hermes execution path end to end, with zero source/runtime mutations:

`systemd runner -> host_task_runner -> executor=hermes -> hermes_observer -> H2 root socket bridge -> root Hermes profile -> governed task result -> supervisor summary/live status`.

This is the first real automated Hermes canary after H1 implementation acceptance.

## Confirmed state

- Branch: `aither-v2`
- Baseline: `dadfc21d07088ea1b29dd35220ff03de4009668b`
- H1 implementation and validator corrections are Architect-accepted at repository level.
- H2 root socket bridge is previously accepted.
- Existing Telegram Hermes Gateway must remain active and unrestarted.
- `aither-codex-runner.timer` remains disabled; this canary is ONE manual service/run-once invocation only.
- Codex usage quota remains irrelevant; Codex must not be invoked.

## Task semantics for root Hermes

When the H2 bridge invokes root Hermes, Hermes must perform only this read-only canary:

1. Read `AGENTS.md`, `.agent/CURRENT_TASK.json`, `.agent/CURRENT_TASK.md`.
2. Verify current task identity is `HERMES-INTEGRATION-H3-E2E-READONLY-CANARY`.
3. Verify `executor=hermes`, `agent_exec=true`, `source_write=false`.
4. Read-only inspect repository identity:
   - branch;
   - HEAD;
   - `git status --porcelain`.
5. Do not modify any file.
6. Do not run Kubernetes/runtime/database/deployment/package/secret operations.
7. Return a concise PASS report and STOP.

Expected executor-side report semantics:

```text
TASK: HERMES-INTEGRATION-H3-E2E-READONLY-CANARY
EXECUTOR: hermes
BRANCH: aither-v2
HEAD: <launch head>
WORKTREE: clean
SOURCE_WRITE: NO
RUNTIME_WRITE: NO
SECRETS_EXPOSED: NO
RESULT: PASS
STOP
```

## Invocation requirements

This canary MUST be initiated by the existing supervisor path, not by directly calling Hermes.

Allowed invocation:

- one manual start/run of the existing `aither-codex-runner.service` / `systemd_runner.py` path, OR equivalent single `host_task_runner.py --run-once` invocation through the installed supervisor mechanism if that is how the unit is wired.

Preferred: start the existing service once while the timer remains disabled.

The invocation must result in:

- task sync from GitHub;
- task loaded as executor=hermes;
- `hermes_observer.py` launched;
- fixed `RUN\n` sent to `/run/aither-hermes/execute.sock`;
- H2 root executor validates governance;
- root Hermes executes with HOME=/root using the existing owner profile;
- no direct Hermes CLI from user `codex`;
- no second Telegram gateway;
- no Codex process;
- no repository implementation commit.

## Hard prohibitions

- DO NOT enable `aither-codex-runner.timer`.
- DO NOT create recurring execution.
- DO NOT call Codex.
- DO NOT call `/usr/local/lib/hermes-agent/venv/bin/hermes` directly from `codex`.
- DO NOT bypass H2 root bridge.
- DO NOT modify source/application/manifests.
- DO NOT modify CURRENT_TASK files locally.
- DO NOT commit or push implementation changes.
- DO NOT touch Kubernetes/Aither runtime/database.
- DO NOT read secrets.
- DO NOT restart/reconfigure Telegram Gateway.
- DO NOT start a second Telegram process.
- DO NOT modify systemd units.
- DO NOT install packages or modify sudoers.
- Exactly ONE automated Hermes task execution is allowed.

## Preconditions

Before invoking the supervisor:

- local branch `aither-v2`;
- clean worktree;
- fetch/sync fast-forward to current GitHub task-control HEAD;
- task id matches this task;
- executor=hermes;
- timer disabled and inactive;
- service not active/activating;
- no host runner process;
- no hermes_observer process;
- H2 socket exists with expected root:codex permissions;
- Telegram Gateway active; record MainPID.

If any precondition fails: `BLOCKED`, no execution, STOP.

## Required evidence

Record before/after:

- local HEAD;
- remote HEAD;
- worktree clean;
- timer enabled/active;
- service state/MainPID;
- host runner process;
- hermes_observer process;
- Telegram Gateway active/MainPID;
- H2 socket owner/group/mode;
- root executor process presence during invocation if observable;
- final host-runner JSON summary;
- final live status sanitized fields;
- repository HEAD/worktree after.

Do not paste raw Hermes reasoning/output beyond the required safe canary report.

## PASS criteria

PASS only if all are true:

1. Supervisor actually selects `executor=hermes`.
2. `hermes_observer.py` is the client path.
3. H2 bridge is invoked exactly once.
4. Root Hermes executes exactly once through the bridge.
5. No Codex execution occurs.
6. Root Hermes uses the existing `/root/.hermes` identity/profile path; no `/home/codex/.hermes` execution.
7. Telegram Gateway remains active with unchanged MainPID.
8. No second Telegram process appears.
9. Root Hermes returns canary PASS.
10. Host-runner result is PASS and preserves task_id/executor.
11. Final live status shows task_id + executor=hermes and no unsafe fields.
12. No source/runtime changes, no implementation commit/push.
13. Worktree remains clean.
14. Timer remains disabled/inactive after execution.

If execution returns BLOCKED/FAIL, do not retry. Capture safe classification and STOP.

## Required final report

```text
TASK: HERMES-INTEGRATION-H3-E2E-READONLY-CANARY

LOCAL_HEAD_BEFORE:
REMOTE_HEAD_BEFORE:
WORKTREE_CLEAN_BEFORE:
CURRENT_TASK:
CURRENT_EXECUTOR:

TIMER_ENABLED_BEFORE:
TIMER_ACTIVE_BEFORE:
RUNNER_SERVICE_ACTIVE_BEFORE:
HOST_RUNNER_PROCESS_BEFORE:
HERMES_OBSERVER_PROCESS_BEFORE:

H2_SOCKET_EXISTS:
H2_SOCKET_OWNER_GROUP_MODE:
TELEGRAM_GATEWAY_ACTIVE_BEFORE:
TELEGRAM_GATEWAY_MAIN_PID_BEFORE:

SUPERVISOR_INVOCATION:
SUPERVISOR_SELECTED_EXECUTOR:
HERMES_OBSERVER_INVOKED:
H2_RUN_COUNT:
ROOT_HERMES_EXECUTION_COUNT:
CODEX_EXECUTION_COUNT:
ROOT_PROFILE_USED:

EXECUTOR_CANARY_TASK:
EXECUTOR_CANARY_BRANCH:
EXECUTOR_CANARY_HEAD:
EXECUTOR_CANARY_WORKTREE:
EXECUTOR_CANARY_RESULT:

HOST_RUNNER_RESULT:
HOST_RUNNER_TASK_ID:
HOST_RUNNER_EXECUTOR:
HOST_RUNNER_COMMIT_SHA:

LIVE_STATE:
LIVE_PHASE:
LIVE_TASK_ID:
LIVE_EXECUTOR:
LIVE_UNSAFE_FIELDS_PRESENT:

LOCAL_HEAD_AFTER:
REMOTE_HEAD_AFTER:
WORKTREE_CLEAN_AFTER:
REPOSITORY_FILES_MODIFIED:
NEW_IMPLEMENTATION_COMMIT:
IMPLEMENTATION_PUSH:

TIMER_ENABLED_AFTER:
TIMER_ACTIVE_AFTER:
RUNNER_SERVICE_ACTIVE_AFTER:
HOST_RUNNER_PROCESS_AFTER:
HERMES_OBSERVER_PROCESS_AFTER:

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
