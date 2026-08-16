# TASK: HERMES-INTEGRATION-H3-R2-E2E-READONLY-CANARY

## Goal

Retry the complete automated Hermes execution path exactly once after acceptance of `HERMES-INTEGRATION-H3-R1-ROOT-GIT-IDENTITY-CORRECTION`.

Target path:

`systemd runner -> host_task_runner -> executor=hermes -> hermes_observer -> H2 root socket bridge -> Git governance as codex -> root Hermes (/root/.hermes) -> read-only canary -> supervisor summary/live status`.

This retry must prove the full E2E path without source/runtime mutation.

## Confirmed state

- Branch: `aither-v2`
- Baseline: `101269d65e3308ef51425b60cd2739b1db1ec959`
- H1 implementation is Architect accepted at repository level.
- H3 first canary reached H2 and was blocked only by root Git dubious ownership.
- H3-R1 corrected H2 Git governance identity: Git checks now run as `codex`, while Hermes remains root with `HOME=/root` and the existing `/root/.hermes` profile.
- H2 socket remains `/run/aither-hermes/execute.sock`.
- Telegram Hermes Gateway must remain active and unrestarted.
- `aither-codex-runner.timer` must remain disabled/inactive.
- Exactly ONE automated Hermes execution is allowed in this task.

## Root Hermes canary semantics

When H2 invokes root Hermes, Hermes must do only:

1. Read `AGENTS.md`, `.agent/CURRENT_TASK.json`, `.agent/CURRENT_TASK.md`.
2. Verify current task id is `HERMES-INTEGRATION-H3-R2-E2E-READONLY-CANARY`.
3. Verify `executor=hermes`, `agent_exec=true`, `source_write=false`.
4. Read-only inspect repository identity:
   - branch;
   - HEAD;
   - clean/dirty worktree.
5. Do not modify any file.
6. Do not use Kubernetes/runtime/database/deployment/package/secret capabilities.
7. Return only concise safe canary evidence and STOP.

Expected safe executor report:

```text
TASK: HERMES-INTEGRATION-H3-R2-E2E-READONLY-CANARY
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

## Invocation

Use the existing supervisor path exactly once.

Preferred invocation:

```text
systemctl start aither-codex-runner.service
```

Timer must remain disabled and inactive.

Do NOT invoke `host_task_runner.py`, `hermes_observer.py`, H2 socket, or Hermes directly as a second execution path.

## Preconditions

Before invocation record and verify:

- local branch `aither-v2`;
- local/remote HEAD synchronized by fast-forward;
- clean worktree;
- current task id matches this task;
- executor=hermes;
- `agent_exec=true`;
- `source_write=false`;
- timer disabled/inactive;
- runner service not active/activating;
- no host runner process;
- no hermes_observer process;
- H2 socket exists/listens and is `root:codex 0660`;
- root executor exists, remains root-owned executable;
- Telegram Gateway active; record MainPID.

If any precondition fails: `BLOCKED`, no execution, STOP.

## Required proof during/after invocation

Prove where possible:

1. Supervisor selected `executor=hermes`.
2. `hermes_observer.py` was invoked.
3. H2 accepted exactly one RUN.
4. H2 Git governance passed using Linux identity `codex`.
5. Root Hermes was spawned exactly once.
6. Root Hermes identity is root and `HOME=/root`; existing `/root/.hermes` profile is used.
7. Codex was not executed.
8. Telegram Gateway MainPID unchanged; no second Telegram process.
9. Root Hermes canary returned PASS.
10. Host-runner final result PASS with correct task_id/executor.
11. Live status final result PASS with correct task_id/executor and no unsafe fields.
12. Repository HEAD unchanged by executor; worktree clean.
13. No Aither/Kubernetes/runtime mutation.
14. Timer still disabled/inactive.

## Hard prohibitions

- Exactly ONE automated execution. No retry in this task.
- DO NOT enable/start the recurring timer.
- DO NOT invoke Codex.
- DO NOT invoke Hermes directly as user `codex`.
- DO NOT bypass H2 bridge.
- DO NOT manually send RUN to H2 socket.
- DO NOT modify H2 executor in this task.
- DO NOT change safe.directory, sudoers, repository ownership, systemd units, or Telegram configuration.
- DO NOT modify source/application/manifests/task-control locally.
- DO NOT create implementation commits or push executor changes.
- DO NOT touch Kubernetes/Aither runtime/database.
- DO NOT read or expose secrets.
- If BLOCKED/FAIL occurs, capture safe evidence and STOP without retry.

## PASS criteria

PASS only if all are true:

1. One supervisor invocation only.
2. Supervisor selects `executor=hermes`.
3. Hermes observer invoked.
4. H2 invoked once.
5. H2 Git governance passes as `codex`.
6. Root Hermes executes exactly once with root identity and `HOME=/root`.
7. Root Hermes canary returns PASS.
8. Host runner returns PASS with correct task id/executor.
9. Live status returns PASS with correct task id/executor and no unsafe fields.
10. No Codex execution.
11. Telegram Gateway unchanged and no second gateway.
12. Repository/runtime unchanged; worktree clean.
13. Timer remains disabled/inactive.

## Required final report

```text
TASK: HERMES-INTEGRATION-H3-R2-E2E-READONLY-CANARY

LOCAL_HEAD_BEFORE:
REMOTE_HEAD_BEFORE:
WORKTREE_CLEAN_BEFORE:
CURRENT_TASK:
CURRENT_EXECUTOR:
AGENT_EXEC:
SOURCE_WRITE:

TIMER_ENABLED_BEFORE:
TIMER_ACTIVE_BEFORE:
RUNNER_SERVICE_ACTIVE_BEFORE:
HOST_RUNNER_PROCESS_BEFORE:
HERMES_OBSERVER_PROCESS_BEFORE:

H2_SOCKET_EXISTS:
H2_SOCKET_OWNER_GROUP_MODE:
ROOT_EXECUTOR_OWNER_GROUP_MODE:
TELEGRAM_GATEWAY_ACTIVE_BEFORE:
TELEGRAM_GATEWAY_MAIN_PID_BEFORE:

SUPERVISOR_INVOCATION_COUNT:
SUPERVISOR_SELECTED_EXECUTOR:
HERMES_OBSERVER_INVOKED:
H2_RUN_COUNT:
H2_GIT_GOVERNANCE_IDENTITY:
H2_GOVERNANCE_RESULT:
ROOT_HERMES_EXECUTION_COUNT:
ROOT_HERMES_USER:
ROOT_HERMES_HOME:
ROOT_PROFILE_USED:
CODEX_EXECUTION_COUNT:

EXECUTOR_CANARY_TASK:
EXECUTOR_CANARY_BRANCH:
EXECUTOR_CANARY_HEAD:
EXECUTOR_CANARY_WORKTREE:
EXECUTOR_CANARY_SOURCE_WRITE:
EXECUTOR_CANARY_RUNTIME_WRITE:
EXECUTOR_CANARY_SECRETS_EXPOSED:
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
