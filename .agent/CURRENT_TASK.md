# TASK: HERMES-INTEGRATION-H3-R1-ROOT-GIT-IDENTITY-CORRECTION

## Goal

Correct the H2 root bridge governance failure discovered by the first H3 E2E canary.

The canary proved the chain through:

`systemd runner -> host_task_runner -> executor=hermes -> hermes_observer -> H2 socket`

but H2 returned `BLOCKED_GOVERNANCE` before spawning root Hermes because the root executor runs Git governance against `/home/codex/aither-project` as Linux user `root`, while the repository is owned by `codex`. Git therefore rejects the repository as dubious ownership.

This task must correct only that identity mismatch.

## Confirmed facts

- Repository checkout: `/home/codex/aither-project`
- Repository owner: `codex`
- H2 service/root executor runs as root.
- Existing H2 socket remains `/run/aither-hermes/execute.sock`.
- Existing Telegram Hermes Gateway must remain active and unrestarted.
- Root Hermes must continue to execute as root with `HOME=/root` and existing `/root/.hermes` profile.
- H3 canary was invoked exactly once and must NOT be repeated in this correction task.
- `aither-codex-runner.timer` remains disabled/inactive.

## Required design

Separate governance identity from Hermes execution identity:

```text
H2 root service
   |
   +-- Git governance checks -> run as Linux user codex
   |      repository=/home/codex/aither-project
   |
   +-- only after governance PASS -> spawn Hermes as root
          HOME=/root
          exact Hermes executable
          existing /root/.hermes profile
```

Git governance must execute as the repository owner, not as root trusting a foreign-owned working tree.

## Preferred implementation

Modify only the installed root executor:

`/usr/local/sbin/aither-hermes-root-exec`

Use an argv-safe privilege drop for Git-only commands, e.g. a fixed helper based on `runuser -u codex -- git ...` or equivalent local mechanism already available on the host.

Requirements:

- only Git governance commands change identity to `codex`;
- Hermes process remains root;
- no shell interpolation;
- no arbitrary command supplied by caller;
- repository path remains fixed `/home/codex/aither-project`;
- branch/task/capability/baseline/clean-worktree governance semantics remain unchanged;
- H2 protocol remains fixed `RUN` with existing framing normalization;
- existing lock remains unchanged;
- existing timeout remains unchanged;
- fail closed if privilege drop or Git command fails.

## Explicitly forbidden

DO NOT:

- run H3 canary in this task;
- send `RUN` to the H2 socket;
- spawn real Hermes;
- launch Codex;
- enable/start the recurring runner timer;
- change `/root/.gitconfig`;
- change `/etc/gitconfig`;
- run `git config --global --add safe.directory ...`;
- run `git config --system --add safe.directory ...`;
- use `safe.directory=*`;
- change ownership of `/home/codex/aither-project`;
- chmod/chown the repository to root;
- move/copy the repository;
- modify sudoers;
- modify `.agent` source/task-control locally;
- modify Aither application/runtime/Kubernetes/database;
- restart/reconfigure Telegram Gateway;
- start a second Telegram process;
- install packages.

## Precheck

Before any mutation record:

- root executor owner/group/mode and SHA256;
- H2 socket owner/group/mode;
- timer enabled/active;
- Telegram Gateway active/MainPID;
- repository owner/group;
- local branch/HEAD/worktree using Linux user `codex`;
- confirm root Git currently fails with `dubious ownership`;
- confirm `runuser -u codex -- git -C /home/codex/aither-project rev-parse --abbrev-ref HEAD` succeeds and returns `aither-v2`.

If the codex-user Git check does not succeed, return `BLOCKED` and STOP without modifying the executor.

## Mutation

Make one minimal backup of the executor outside the repository, mode 0600, timestamped under `/root` or `/var/tmp`.

Then modify only `/usr/local/sbin/aither-hermes-root-exec` so its Git governance helper executes fixed Git argv as Linux user `codex`.

Do not alter Hermes spawn identity.

## Static validation

After modification, without invoking H2 RUN:

1. Syntax/compile check as appropriate.
2. Static inspection proves:
   - Git commands are executed as `codex`;
   - repository path fixed;
   - root Hermes executable unchanged;
   - `HOME=/root` preserved for Hermes;
   - no direct/user-controlled command forwarding;
   - no `shell=True`, `os.system`, `eval`, `exec` added;
   - no safe.directory configuration added.
3. Execute the exact read-only governance Git commands used by the executor through the new Git helper/identity, but do NOT spawn Hermes and do NOT connect to the socket.
4. Confirm they return:
   - branch `aither-v2`;
   - current HEAD;
   - clean worktree;
   - baseline ancestor checks as required by current task state.

## Service handling

If the root executor is an ordinary executable invoked by the existing templated service and no unit file changes are needed, do NOT daemon-reload or restart persistent services.

Do not restart Telegram Gateway.

The socket must remain active/listening.

## Required final report

```text
TASK: HERMES-INTEGRATION-H3-R1-ROOT-GIT-IDENTITY-CORRECTION

ROOT_EXECUTOR_SHA_BEFORE:
ROOT_EXECUTOR_OWNER_GROUP_MODE_BEFORE:
H2_SOCKET_OWNER_GROUP_MODE_BEFORE:
REPO_OWNER_GROUP:
TIMER_ENABLED_BEFORE:
TIMER_ACTIVE_BEFORE:
TELEGRAM_GATEWAY_MAIN_PID_BEFORE:

ROOT_GIT_DUBIOUS_OWNERSHIP_REPRODUCED:
CODEX_GIT_BRANCH_PRECHECK:
CODEX_GIT_HEAD_PRECHECK:
CODEX_GIT_WORKTREE_PRECHECK:

BACKUP_CREATED:
ROOT_EXECUTOR_MODIFIED: YES|NO
GIT_GOVERNANCE_IDENTITY_AFTER: codex
GIT_GOVERNANCE_REPO_FIXED: YES|NO
ROOT_HERMES_IDENTITY_PRESERVED: YES|NO
ROOT_HERMES_HOME_PRESERVED: YES|NO
ROOT_HERMES_EXECUTABLE_PRESERVED: YES|NO
SAFE_DIRECTORY_CONFIG_CHANGED: NO
SUDOERS_CHANGED: NO

STATIC_SYNTAX_CHECK:
STATIC_NO_SHELL_EVAL_EXEC:
STATIC_FIXED_PROTOCOL_PRESERVED:
STATIC_LOCK_PRESERVED:
STATIC_TIMEOUT_PRESERVED:
GOVERNANCE_BRANCH_CHECK:
GOVERNANCE_HEAD_CHECK:
GOVERNANCE_CLEAN_WORKTREE_CHECK:
GOVERNANCE_BASELINE_CHECK:

REAL_H2_RUN_INVOKED: NO
REAL_HERMES_EXECUTED: NO
CODEX_EXECUTED: NO
AITHER_RUNTIME_TOUCHED: NO
KUBERNETES_TOUCHED: NO
REPOSITORY_FILES_MODIFIED: NO

ROOT_EXECUTOR_SHA_AFTER:
ROOT_EXECUTOR_OWNER_GROUP_MODE_AFTER:
H2_SOCKET_EXISTS_AFTER:
H2_SOCKET_OWNER_GROUP_MODE_AFTER:
TIMER_ENABLED_AFTER:
TIMER_ACTIVE_AFTER:
TELEGRAM_GATEWAY_ACTIVE_AFTER:
TELEGRAM_GATEWAY_MAIN_PID_AFTER:
TELEGRAM_GATEWAY_RESTARTED: NO
SECOND_TELEGRAM_PROCESS: NO
SECRETS_EXPOSED: NO

RESULT: PASS|FAIL|BLOCKED
STOP
```

## PASS criteria

PASS only if:

1. `codex` identity can perform every required Git governance check on the fixed repository.
2. Root executor was minimally changed so Git governance uses `codex`.
3. Root Hermes identity/HOME/executable are unchanged.
4. No safe.directory configuration was added.
5. No H2 RUN or Hermes execution occurred.
6. Socket remains healthy.
7. Telegram Gateway PID unchanged.
8. Timer remains disabled/inactive.
9. Repository and Aither runtime remain untouched.

After PASS, STOP. Do not repeat H3 canary; Architect will authorize the retry separately.
