# TASK: CODEX-HARNESS-S2-A-R1 — FIX HOST RUNNER SELF-LOCK AND UNTRACKED PATH ENUMERATION

## MODE
SOURCE GOVERNANCE LAUNCHER CORRECTION ONLY

## Why this correction exists
Independent Connector audit of S2-A found two defects before real execution was enabled:

1. The default lock path is `.agent/host_task_runner.lock`. `simulate()` acquires that lock before `require_clean_worktree()`. Because the lock is inside the worktree and is not ignored, the runner can make its own worktree dirty and block itself.
2. Worktree enumeration uses `git status --porcelain=v1 -z` without `--untracked-files=all`, so a newly created untracked directory may be reported as one directory path instead of the exact files inside it.

No real Codex execution, network Git, commit, push, deployment, Kubernetes, secret access, or runtime mutation is authorized in this correction.

## Baseline
`5c6cec14197298957c373281045c06c7875b1855`

Branch: `aither-v2`

The launch HEAD may be a descendant of baseline because Architect publishes this task after baseline. `HEAD != baseline` is not a blocker. Require baseline ancestor success. Committed paths `baseline..START_HEAD` may contain only `.agent/CURRENT_TASK.json` and `.agent/CURRENT_TASK.md`.

## Files Codex may modify
- `.agent/host_task_runner.py`
- `.agent/tests/test_host_task_runner.py`

Do not modify Architect-managed task files.

## Required corrections

### 1. Lock must not dirty the Git worktree
Move the default inter-process lock out of normal worktree status. Prefer a deterministic path in Git metadata resolved with Git, e.g. using `git rev-parse --git-path <runner-lock-name>` and resolving it relative to the repository when needed.

Requirements:
- lock remains host-side and standard-library only;
- lock creation must not appear in normal `git status --porcelain` output;
- explicit `--lock-path` must remain supported for tests;
- lock contention must still fail closed;
- do not add the lock to `.gitignore` as a workaround.

### 2. Exact untracked file enumeration
`changed_worktree_paths()` must request all untracked files explicitly:

`git status --porcelain=v1 -z --untracked-files=all`

The returned paths must remain exact file paths and continue to reject any path outside task `allowed_paths`.

### 3. Keep S2-A safety boundary
- runner remains dry-run/simulation only;
- do not perform real `codex exec`;
- do not implement or perform real fetch/pull/commit/push in this correction;
- keep fixed Codex argv builder unchanged except where a test-only refactor is strictly necessary;
- no shell interpolation / no `shell=True`.

## Tests required
Retain all existing tests and add tests proving at minimum:

1. default lock path is resolved outside normal worktree status / into Git metadata;
2. simulation clean-worktree check is not poisoned by the runner's own default lock;
3. changed-worktree enumeration invokes Git with `--untracked-files=all`;
4. exact untracked file paths are parsed and checked against `allowed_paths`;
5. existing lock contention fail-closed behavior still passes;
6. all previous S2-A tests still pass.

Use `unittest` and Python standard library only. No network calls.

## Required validation

```bash
python3 -m json.tool .agent/CURRENT_TASK.json >/dev/null
python3 -m py_compile .agent/host_task_runner.py .agent/tests/test_host_task_runner.py
python3 .agent/tests/test_host_task_runner.py
python3 .agent/validate_task_scope.py
git diff --check
```

Also execute the runner's dry-run locally only if it performs no network or mutating Git action:

```bash
python3 .agent/host_task_runner.py --dry-run
```

Expected: PASS when repository is otherwise clean. If running it after editing makes the worktree dirty because of the authorized source changes, use a temporary clean Git fixture in the unit tests instead and report the real-tree dry-run as NOT RUN due to expected dirty implementation worktree. Do not bypass the clean-worktree guard.

## Prohibited
- real `codex exec`
- git fetch/pull/commit/push from inside Codex
- staging/commit/push
- network calls
- root/sudo
- Kubernetes/kubectl
- Docker
- deployment
- DB/runtime mutation
- secret access
- package installation
- application code changes
- systemd/timers/cron
- autonomous next task

## Final report
TASK: CODEX-HARNESS-S2-A-R1
MODE: SOURCE GOVERNANCE LAUNCHER CORRECTION ONLY
START HEAD: <full SHA>
BASELINE: 5c6cec14197298957c373281045c06c7875b1855
BASELINE ANCESTOR CHECK: PASS/FAIL
COMMITTED PATHS BASELINE..START: <paths>
FILES CHANGED BY CODEX: <count>
FILES: <paths>
JSON VALIDATION: PASS/FAIL
PY_COMPILE: PASS/FAIL
UNIT TESTS: PASS/FAIL + test count
SCOPE VALIDATOR: PASS/FAIL
GIT DIFF CHECK: PASS/FAIL
DRY-RUN SELF-LOCK TEST: PASS/FAIL/NOT RUN WITH REASON
UNTRACKED-FILES-ALL TEST: PASS/FAIL
REAL CODEX EXEC: NOT ATTEMPTED
GIT FETCH/PULL: NOT ATTEMPTED
NEW COMMIT: NO
PUSH: NOT ATTEMPTED
KUBERNETES ACCESSED: NO
DEPLOYMENT: NONE
DB CHANGES: NONE
RUNTIME CHANGES: NONE
SECRET ACCESS: NONE
WORKTREE AFTER: clean/dirty
RESULT: PASS/FAIL/BLOCKED
STOP

Do not declare PASSED or CONNECTOR VERIFIED.
