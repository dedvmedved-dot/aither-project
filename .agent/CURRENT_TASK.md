# TASK: CODEX-HARNESS-S1-R2 — MAKE PUSH AND PR BRANCH AUTHORIZATION CI-SAFE

## MODE
SOURCE GOVERNANCE CORRECTION ONLY

## Why this task exists
R1 correctly added pull-request base-branch handling, but `Agent Gates` checks out an exact commit SHA on push. GitHub Actions therefore runs in detached HEAD, so `git branch --show-current` is empty and the validator fails on push.

Observed CI failure on R1:
`ERROR=branch mismatch: expected aither-v2, got `

## Baseline
`1babedfb976e2cff939622026cae6ecbb2b0502b`

Branch: `aither-v2`

Before work:
- `git fetch origin`
- fast-forward local `aither-v2` to current remote Architect task commit;
- worktree must be clean.

## Architect-managed files
Do not modify:
- `.agent/CURRENT_TASK.json`
- `.agent/CURRENT_TASK.md`

## Only implementation file allowed
- `.agent/validate_task_scope.py`

No other implementation path may change.

## Required behavior
Branch authorization must not depend on attached HEAD inside GitHub Actions.

Implement exactly this precedence:

1. If `GITHUB_ACTIONS=true` and `GITHUB_EVENT_NAME=pull_request`:
   - authorized branch source = `GITHUB_BASE_REF`;
   - require it equals `task.branch`.

2. Else if `GITHUB_ACTIONS=true` (for push and other supported branch-triggered CI runs):
   - authorized branch source = `GITHUB_REF_NAME`;
   - require it equals `task.branch`.

3. Else (local execution outside GitHub Actions):
   - authorized branch source = `git branch --show-current`;
   - require it equals `task.branch`.

If the required GitHub environment variable is empty/missing, fail closed.

Keep deterministic output. No network/API calls. No writes. No shell=True.

Do NOT change `.github/workflows/agent-gates.yml` in this task. The exact-SHA checkout is acceptable once validator branch authorization is CI-aware.

## Required local validation
Run:

```bash
python3 -m json.tool .agent/CURRENT_TASK.json >/dev/null
python3 -m py_compile .agent/validate_task_scope.py
python3 .agent/validate_task_scope.py
GITHUB_ACTIONS=true GITHUB_EVENT_NAME=push GITHUB_REF_NAME=aither-v2 python3 .agent/validate_task_scope.py
GITHUB_ACTIONS=true GITHUB_EVENT_NAME=pull_request GITHUB_BASE_REF=aither-v2 python3 .agent/validate_task_scope.py
git diff --check
```

Required:
- normal local validator PASS;
- simulated push PASS;
- simulated PR PASS;
- unauthorized paths 0.

Also prove fail-closed behavior with one negative simulation, for example:

```bash
GITHUB_ACTIONS=true GITHUB_EVENT_NAME=push GITHUB_REF_NAME=main python3 .agent/validate_task_scope.py
```

This negative test MUST fail non-zero with branch mismatch. Do not treat that expected failure as task failure.

## Commit and push
Create exactly one implementation commit.
Recommended message:
`fix: make agent gate CI branch-aware`

Push normally to `aither-v2`.
No amend/rebase/merge/force push.

## Prohibited
- kubectl / Kubernetes
- Docker
- deployment
- DB/runtime changes
- secrets
- package installation
- application code changes
- autonomous next task

## Final report

TASK: CODEX-HARNESS-S1-R2
MODE: SOURCE GOVERNANCE CORRECTION ONLY
START HEAD: <full SHA after pulling Architect task commit>
NEW SHA: <full SHA>
PARENT SHA: <full SHA>
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
NEW COMMIT: YES/NO
PUSH: PASS/FAIL
WORKTREE AFTER: clean/dirty
RESULT: PASS/FAIL/BLOCKED
STOP

Do not declare PASSED or CONNECTOR VERIFIED.
