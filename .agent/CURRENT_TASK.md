# TASK: CODEX-HARNESS-S1-R4 — COMPLETE CI BRANCH-AWARE VALIDATOR

## MODE
SOURCE GOVERNANCE CORRECTION ONLY

## Critical baseline semantics
`baseline_sha` is the immutable comparison base for scope/diff validation. It is NOT required to equal the launch HEAD.

For this task:
- baseline: `cd0d842b6e34e1d8d612b1a43640fffaca0c162a`
- launch HEAD will be a later Architect task-handoff commit.

Codex MUST NOT stop merely because `HEAD != baseline_sha`.
Instead verify all of the following:
1. current branch is `aither-v2`;
2. worktree is clean at launch;
3. baseline commit exists;
4. baseline is an ancestor of launch HEAD (`git merge-base --is-ancestor <baseline> HEAD` succeeds);
5. committed differences from baseline to launch HEAD are only Architect-managed task paths allowed by `CURRENT_TASK.json`.

This instruction explicitly resolves the ambiguity in `AGENTS.md` phrase "verify ... baseline SHA". It means verify existence/ancestry/scope, not HEAD equality.

## Execution model
Git metadata is read-only inside Codex `workspace-write` sandbox. Do not run network Git or mutate `.git`.
The host/operator updates the checkout before launching Codex. Codex edits only the implementation file and runs tests. Commit/push happen outside Codex after STOP.

## Only implementation file Codex may modify
- `.agent/validate_task_scope.py`

Do not modify:
- `.agent/CURRENT_TASK.json`
- `.agent/CURRENT_TASK.md`
- `.github/workflows/agent-gates.yml`
- any application/runtime file

## Required correction
Branch authorization must work when GitHub Actions checks out an exact SHA and therefore has detached HEAD.

Implement this precedence in `.agent/validate_task_scope.py`:

1. If `GITHUB_ACTIONS=true` and `GITHUB_EVENT_NAME=pull_request`:
   - branch source = `GITHUB_BASE_REF`;
   - require non-empty and equal to `task.branch`.

2. Else if `GITHUB_ACTIONS=true`:
   - branch source = `GITHUB_REF_NAME`;
   - require non-empty and equal to `task.branch`.

3. Else (local execution outside GitHub Actions):
   - branch source = `git branch --show-current`;
   - require equal to `task.branch`.

Fail closed if the required GitHub Actions branch variable is missing/empty.
Keep deterministic output. No network/API calls. No writes from validator. No `shell=True`.

## Required validation
Run:

```bash
python3 -m json.tool .agent/CURRENT_TASK.json >/dev/null
python3 -m py_compile .agent/validate_task_scope.py
python3 .agent/validate_task_scope.py
GITHUB_ACTIONS=true GITHUB_EVENT_NAME=push GITHUB_REF_NAME=aither-v2 python3 .agent/validate_task_scope.py
GITHUB_ACTIONS=true GITHUB_EVENT_NAME=pull_request GITHUB_BASE_REF=aither-v2 python3 .agent/validate_task_scope.py
git diff --check
```

Negative test:

```bash
GITHUB_ACTIONS=true GITHUB_EVENT_NAME=push GITHUB_REF_NAME=main python3 .agent/validate_task_scope.py
```

Negative test MUST fail non-zero with branch mismatch; that expected rejection counts as PASS for the negative test.

Before final report verify that the only uncommitted file changed by Codex is:
`.agent/validate_task_scope.py`

## Prohibited
- git fetch / pull / commit / push inside Codex
- Kubernetes / kubectl
- Docker
- deployment
- DB/runtime mutation
- secrets
- package installation
- application code changes
- autonomous next task

## Final report

TASK: CODEX-HARNESS-S1-R4
MODE: SOURCE GOVERNANCE CORRECTION ONLY
START HEAD: <full SHA visible at launch>
BASELINE: cd0d842b6e34e1d8d612b1a43640fffaca0c162a
BASELINE ANCESTOR CHECK: PASS/FAIL
COMMITTED PATHS BASELINE..START: <paths>
FILES CHANGED BY CODEX: 1
FILES:
.agent/validate_task_scope.py
LOCAL VALIDATOR: PASS/FAIL
SIMULATED PUSH: PASS/FAIL
SIMULATED PR: PASS/FAIL
NEGATIVE WRONG-BRANCH TEST: PASS/FAIL
JSON VALIDATION: PASS/FAIL
PY_COMPILE: PASS/FAIL
GIT DIFF CHECK: PASS/FAIL
KUBERNETES ACCESSED: NO
DEPLOYMENT: NONE
DB CHANGES: NONE
RUNTIME CHANGES: NONE
SECRET ACCESS: NONE
GIT FETCH: NOT ATTEMPTED
NEW COMMIT: NO
PUSH: NOT ATTEMPTED
WORKTREE AFTER: dirty (expected: validator only)
RESULT: PASS/FAIL/BLOCKED
STOP

Codex must not declare PASSED or CONNECTOR VERIFIED.
